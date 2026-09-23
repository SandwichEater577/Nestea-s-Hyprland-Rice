#!/usr/bin/env python3
"""Connected-monitor status and persistent Hyprland display layouts."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys


PREFERENCES = Path.home() / '.config/rice/display-layout.tsv'
INTERNAL_PREFIXES = ('eDP-', 'LVDS-', 'DSI-')
OUTPUT_NAME = re.compile(r'^[A-Za-z0-9_.-]+$')
MODE = re.compile(r'^(?:preferred|[0-9]+x[0-9]+@[0-9]+(?:\.[0-9]+)?)$')


def hyprctl(*args):
    result = subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Hyprland did not respond')
    return result.stdout.strip()


def monitors():
    return json.loads(hyprctl('-j', 'monitors', 'all'))


def display_data():
    connected = monitors()
    internal = next((m for m in connected if m['name'].startswith(INTERNAL_PREFIXES)), None)
    external = [m for m in connected if not m['name'].startswith(INTERNAL_PREFIXES)]
    return {'internal': internal, 'external': external}


def mirror_mode(internal, external):
    width, height = internal['width'], internal['height']
    matching = [m for m in external.get('availableModes', []) if m.startswith(f'{width}x{height}@')]
    if matching:
        return matching[0].removesuffix('Hz')
    return 'preferred'


def saved_layouts():
    layouts = {}
    if not PREFERENCES.exists():
        return layouts
    for line in PREFERENCES.read_text().splitlines():
        fields = line.split('\t')
        if len(fields) != 4:
            continue
        output, layout, mode, scale = fields
        if OUTPUT_NAME.fullmatch(output) and layout in ('mirror', 'extend') and MODE.fullmatch(mode):
            try:
                if 0.5 <= float(scale) <= 4:
                    layouts[output] = (layout, mode, scale)
            except ValueError:
                pass
    return layouts


def apply_layout(output, layout):
    if layout not in ('mirror', 'extend') or not OUTPUT_NAME.fullmatch(output):
        raise ValueError('Invalid display layout')
    data = display_data()
    external = next((m for m in data['external'] if m['name'] == output), None)
    if external is None:
        raise RuntimeError('That display is no longer connected')
    internal = data['internal']
    if layout == 'mirror' and internal is None:
        raise RuntimeError('Connect the laptop screen before mirroring it')
    mode = mirror_mode(internal, external) if layout == 'mirror' else 'preferred'
    scale = str(internal['scale'] if internal else 1)
    layouts = saved_layouts()
    layouts[output] = (layout, mode, scale)
    PREFERENCES.parent.mkdir(parents=True, exist_ok=True)
    old = PREFERENCES.read_bytes() if PREFERENCES.exists() else None
    tmp = PREFERENCES.with_suffix('.tsv.tmp')
    lines = [f'{name}\t{kind}\t{size}\t{factor}\n' for name, (kind, size, factor) in sorted(layouts.items())]
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as file:
            file.writelines(lines)
        tmp.replace(PREFERENCES)
        hyprctl('reload')
        updated = display_data()
        current = next((m for m in updated['external'] if m['name'] == output), None)
        source = updated['internal']
        mirrored = current and source and str(current['mirrorOf']) in (str(source['id']), source['name'])
        if not current or bool(mirrored) != (layout == 'mirror'):
            raise RuntimeError('Display layout did not apply')
    except Exception:
        if old is None:
            PREFERENCES.unlink(missing_ok=True)
        else:
            PREFERENCES.write_bytes(old)
            PREFERENCES.chmod(0o600)
        try:
            hyprctl('reload')
        except Exception:
            pass
        raise
    finally:
        tmp.unlink(missing_ok=True)


def status():
    import rice_status
    print(json.dumps(rice_status.display(), ensure_ascii=False))


if __name__ == '__main__':
    try:
        if len(sys.argv) == 2 and sys.argv[1] == 'status':
            status()
        else:
            raise ValueError('Usage: display.py status')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        if len(sys.argv) == 2 and sys.argv[1] == 'status':
            print(json.dumps({'text': '', 'tooltip': str(exc)}))
        else:
            raise
