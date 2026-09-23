#!/usr/bin/env python3
"""Sample a wallpaper and publish one high-contrast palette for every bar."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

HOME = Path.home()
STATE = HOME / '.local/state/rice'
CACHE = HOME / '.cache/rice/wallpaper-palettes'
VERSION = 1
DEFAULT = {'background': '#161616', 'foreground': '#e4e4e4',
           'border': '#3b3b3b', 'muted': '#a3a3a3', 'accent': '#dedede',
           'accent_foreground': '#181818', 'hover': '#303030', 'scheme': 'dark'}


def luminance(rgb):
    values = [v / 255 for v in rgb]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))


def color(rgb):
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v))) for v in rgb)


def sample(path):
    # RGB bytes avoid dependencies on Pillow and work for PNG, JPEG and WebP.
    data = subprocess.run(['magick', str(path), '-auto-orient', '-resize', '48x48!',
                           '-alpha', 'remove', '-depth', '8', 'rgb:-'],
                          capture_output=True, check=True, timeout=15).stdout
    pixels = [tuple(data[i:i + 3]) for i in range(0, len(data) - 2, 3)]
    if not pixels:
        return dict(DEFAULT)
    avg = sum(luminance(p) for p in pixels) / len(pixels)
    # Count broad hue buckets. Weight saturation so a small vibrant object
    # does not beat the dominant colors, but flat gray walls remain neutral.
    bins = {}
    for p in pixels:
        lo, hi = min(p), max(p)
        if hi - lo < 20:
            continue
        key = tuple(v // 32 for v in p)
        count, sums = bins.get(key, (0, [0, 0, 0]))
        bins[key] = (count + 1, [sums[i] + p[i] for i in range(3)])
    if bins:
        _, (count, sums) = max(bins.items(), key=lambda item: item[1][0] *
                              (1 + (max(item[1][1]) - min(item[1][1])) /
                               (item[1][0] * 255)))
        base = [v / count for v in sums]
    else:
        base = [190, 190, 190]
    # A dark panel remains legible over almost any wallpaper. The sampled
    # lightness picks its brightness and the sampled hue colors the accent.
    light = avg > .63
    bg = (239, 239, 239) if light else (22, 22, 22)
    fg = (24, 24, 24) if light else (228, 228, 228)
    target = 75 if light else 185
    spread = [v - sum(base) / 3 for v in base]
    accent = [target + v * .55 for v in spread]
    accent = [max(45 if light else 120, min(125 if light else 225, v)) for v in accent]
    # Ensure the accent itself has readable label text.
    accent_text = (255, 255, 255) if luminance(accent) < .18 else (18, 18, 18)
    return dict(background=color(bg), foreground=color(fg),
                border='#b8b8b8' if light else '#3b3b3b',
                muted='#646464' if light else '#a3a3a3', accent=color(accent),
                accent_foreground=color(accent_text),
                hover='#dedede' if light else '#303030',
                scheme='light' if light else 'dark')


def palette(path):
    if not path or not Path(path).is_file():
        return dict(DEFAULT)
    image = Path(path).resolve()
    stat = image.stat()
    key = hashlib.sha256(f'{VERSION}:{image}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()
    saved = CACHE / (key + '.json')
    try:
        values = json.loads(saved.read_text())
        if all(isinstance(values.get(name), str) for name in DEFAULT):
            return values
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    values = sample(image)
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        temp = CACHE / (key + f'.{os.getpid()}.tmp')
        temp.write_text(json.dumps(values, sort_keys=True) + '\n')
        os.replace(temp, saved)
    except OSError:
        pass  # A full or read-only cache must not prevent wallpaper changes.
    return values


def replace_changed(dest, data):
    try:
        if dest.read_text() == data:
            return
    except OSError:
        pass
    temp = dest.with_name(dest.name + f'.{os.getpid()}.tmp')
    temp.write_text(data)
    os.replace(temp, dest)


def publish(values):
    STATE.mkdir(parents=True, exist_ok=True)
    replace_changed(STATE / 'palette.json', json.dumps(values, sort_keys=True) + '\n')
    css = HOME / '.config/waybar/palette.css'
    css.parent.mkdir(parents=True, exist_ok=True)
    lines = ['@define-color rice_%s %s;' % (k, v) for k, v in values.items() if k != 'scheme']
    replace_changed(css, '\n'.join(lines) + '\n')
    return values


def write(path):
    return publish(palette(path))


if __name__ == '__main__':
    try:
        print(json.dumps(write(sys.argv[1] if len(sys.argv) > 1 else None)))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f'Wallpaper palette: {exc}', file=sys.stderr)
        sys.exit(1)
