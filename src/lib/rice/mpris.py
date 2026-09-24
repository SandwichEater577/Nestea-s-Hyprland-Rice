"""Choose one enabled MPRIS source and read it through playerctl."""
import json
import os
from pathlib import Path
import subprocess
import time

OPTIONS = Path.home() / '.config/rice/Media-Options.json'
BROWSERS = ('chromium', 'brave', 'chrome', 'firefox', 'vivaldi', 'edge', 'opera')


def options():
    try:
        value = json.loads(OPTIONS.read_text())
        if isinstance(value, dict):
            return value
    except (OSError, ValueError):
        pass
    return {'desktop_spotify': True, 'browser_media': False}


def player(name, *args):
    try:
        result = subprocess.run(['playerctl', f'--player={name}', *args],
                                capture_output=True, text=True, timeout=1)
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def selected_player():
    try:
        result = subprocess.run(['playerctl', '-l'], capture_output=True, text=True, timeout=1)
        names = result.stdout.splitlines() if result.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        return ''
    enabled = options()
    names = [name for name in names if
             (name == 'spotify' and enabled.get('desktop_spotify', True)) or
             (name.lower().startswith(BROWSERS) and enabled.get('browser_media', False))]
    if not names:
        return ''
    ordered = sorted(names, key=lambda name: (name != 'spotify', name))
    return next((name for name in ordered if player(name, 'status') == 'Playing'), ordered[0])


def get_state(fields=()):
    name = selected_player()
    status = player(name, 'status') if name else ''
    if not status:
        return None
    state = {'PlaybackStatus': status, '_name': name}
    if 'loop' in fields:
        state['LoopStatus'] = player(name, 'loop')
    if 'shuffle' in fields:
        state['Shuffle'] = player(name, 'shuffle')
    if 'metadata' in fields:
        parts = player(name, 'metadata', '--format', '{{mpris:artUrl}}\t{{artist}}\t{{title}}').split('\t', 2)
        if len(parts) == 3:
            state['Metadata'] = {'mpris:artUrl': parts[0], 'xesam:artist': parts[1], 'xesam:title': parts[2]}
    return state


def set_property(name, key, value):
    if key == 'LoopStatus':
        args = ('loop', value)
    elif key == 'Shuffle':
        args = ('shuffle', 'On' if value else 'Off')
    else:
        return False
    try:
        result = subprocess.run(['playerctl', f'--player={name}', *args],
                                capture_output=True, timeout=1)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def status_widget(state):
    if not state:
        return {'text': '', 'tooltip': ''}
    status = state.get('PlaybackStatus', 'Stopped')
    return {'text': '' if status == 'Playing' else '',
            'class': status.lower(), 'tooltip': 'Play / pause'}


def shuffle_widget(state):
    if not state:
        return {'text': '', 'tooltip': ''}
    if state.get('Shuffle') not in ('On', 'Off'):
        return {'text': '', 'tooltip': ''}
    enabled = state['Shuffle'] == 'On'
    return {'text': '', 'class': 'enabled' if enabled else 'disabled',
            'tooltip': ('Shuffle on (regular / Smart not exposed)' if enabled else 'Shuffle off')
                       + '\nClick: toggle shuffle\nRight-click: choose Smart Shuffle in Spotify'}


def repeat_widget(state):
    if not state:
        return {'text': '', 'tooltip': ''}
    mode = state.get('LoopStatus', 'None')
    if mode not in ('None', 'Playlist', 'Track'):
        return {'text': '', 'tooltip': ''}
    label = {'None': 'Repeat off', 'Playlist': 'Repeat all', 'Track': 'Repeat one'}.get(mode, 'Repeat unavailable')
    return {'text': '󰑘' if mode == 'Track' else '',
            'class': 'enabled' if mode in ('Playlist', 'Track') else 'disabled',
            'tooltip': label + '\nClick: off → all → one'}


def cover(state):
    if not state:
        return '', ''
    import hashlib
    from urllib.parse import unquote, urlparse
    from urllib.request import urlopen
    metadata = state.get('Metadata') or {}
    url = metadata.get('mpris:artUrl', '')
    parsed = urlparse(url)
    if parsed.scheme == 'file':
        path = Path(unquote(parsed.path))
        image = str(path) if path.is_file() else ''
    elif parsed.scheme in ('http', 'https'):
        cache = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'rice-media-covers'
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / (hashlib.sha256(url.encode()).hexdigest() + '.art')
        if not path.is_file():
            failed = path.with_suffix('.failed')
            if failed.exists() and time.time() - failed.stat().st_mtime < 60:
                return '', ''
            try:
                with urlopen(url, timeout=3) as response:
                    data = response.read(5 * 1024 * 1024 + 1)
            except (OSError, ValueError):
                failed.touch()
                return '', ''
            if not data or len(data) > 5 * 1024 * 1024:
                failed.touch()
                return '', ''
            tmp = cache / (path.name + '.tmp-' + str(os.getpid()))
            tmp.write_bytes(data)
            tmp.replace(path)
            failed.unlink(missing_ok=True)
            for old in sorted(cache.glob('*.art'), key=lambda p: p.stat().st_mtime, reverse=True)[100:]:
                old.unlink(missing_ok=True)
        image = str(path)
    else:
        image = ''
    artists = metadata.get('xesam:artist') or []
    artist = ', '.join(artists) if isinstance(artists, (list, tuple)) else str(artists)
    title = str(metadata.get('xesam:title') or '')
    tooltip = ' '.join(f'{artist} — {title}'.split()) or 'Spotify'
    return image, tooltip if image else ''
