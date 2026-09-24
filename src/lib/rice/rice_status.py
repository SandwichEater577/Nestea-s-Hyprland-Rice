"""Fast, bounded status reads for the QuickShell bar."""
import html
import json
import os
from pathlib import Path
import re
import subprocess
import time

HOME = Path.home()
STATE = HOME / '.local/state/rice'


def run(*args, timeout=1):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def audio():
    value = run('wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@')
    boosted = (STATE / 'audio-boost').exists()
    try:
        percent = round(float(value.split()[1]) * 100)
    except (ValueError, IndexError):
        return {'text': '󰝟 —', 'tooltip': 'No audio output'}
    muted = 'MUTED' in value
    return {'text': ('󰝟' if muted else '') + f'\u2002\u2002{percent}%' + (' +' if boosted else ''),
            'tooltip': ('Middle click or F4: lock to 100%' if boosted else 'Middle click or F4: unlock 150%')
                       + '\nWheel up/down: volume · Left click: mute\nRight click: output and application volume',
            'class': 'boosted' if boosted else ('muted' if muted else 'normal')}


def network():
    try:
        # One nmcli response contains the device, connection and addresses.
        # This avoids importing the large GI stack on every bar refresh.
        details = run('nmcli', '-t', '-f',
                      'GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS',
                      'device', 'show')
        devices = []
        for block in details.split('\n\n'):
            item = {}
            addresses = []
            for line in block.splitlines():
                key, sep, value = line.partition(':')
                if not sep:
                    continue
                value = re.sub(r'\\(.)', r'\1', value)
                if key.startswith('IP4.ADDRESS['):
                    addresses.append(value)
                else:
                    item[key] = value
            if item.get('GENERAL.TYPE') in ('wifi', 'ethernet') and item.get('GENERAL.STATE', '').startswith('100'):
                item['addresses'] = addresses
                devices.append(item)
        devices.sort(key=lambda d: d['GENERAL.TYPE'] != 'ethernet')
        if not devices:
            return {'text': '󰖪', 'tooltip': 'No internet\nRight-click: networks'}
        device = devices[0]
        iface = device['GENERAL.DEVICE']
        kind = device['GENERAL.TYPE']
        name = device.get('GENERAL.CONNECTION') or iface
        counter = int((Path('/sys/class/net') / iface / 'statistics/rx_bytes').read_text())
        now = time.monotonic()
        cache = STATE / 'network-rate.json'
        try:
            old = json.loads(cache.read_text())
            elapsed = now - old['time']
            rate = max(0, (counter - old['bytes']) / elapsed / 1_000_000) if old['dev'] == iface and elapsed > .1 else 0
        except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
            rate = 0
        try:
            STATE.mkdir(parents=True, exist_ok=True)
            tmp = cache.with_name(cache.name + f'.tmp-{os.getpid()}')
            tmp.write_text(json.dumps({'dev': iface, 'bytes': counter, 'time': now}))
            tmp.replace(cache)
        except OSError:
            pass
        connectivity = run('nmcli', 'networking', 'connectivity') or 'unknown'
        signal = ''
        if kind == 'wifi':
            for line in run('nmcli', '-t', '-f', 'IN-USE,SIGNAL', 'device', 'wifi',
                            'list', '--rescan', 'no', 'ifname', iface).splitlines():
                if line.startswith('*:'):
                    signal = line.split(':', 2)[1] + '% '
                    break
        icon = '󰖪' if connectivity in ('none', 'limited', 'portal') else ('󰈀' if kind == 'ethernet' else '')
        return {'text': f'{icon}\u2002\u2002{signal} ↓  {rate:.2f} MB/s',
                'tooltip': html.escape(f'{name} · {iface}\n' + '\n'.join(device['addresses']) + f'\nInternet: {connectivity}\nRight-click: networks and diagnostics')}
    except Exception:
        # A status widget should remain usable during NetworkManager restarts.
        return {'text': '󰖪', 'tooltip': 'Network status unavailable\nRight-click: networks'}


def display():
    try:
        monitors = json.loads(run('hyprctl', '-j', 'monitors', 'all'))
        external = [m for m in monitors if not m.get('name', '').startswith(('eDP-', 'LVDS-', 'DSI-'))]
        if external:
            names = ', '.join(m.get('model') or m['name'] for m in external)
            return {'text': '󰍹', 'tooltip': f'Displays · {names}\nClick to change layout'}
    except (ValueError, KeyError, TypeError):
        pass
    return {'text': ''}


def bluetooth():
    value = run('bluetoothctl', 'show')
    return '' if 'Powered: yes' in value else ('󰂲' if value else '')
