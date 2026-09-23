#!/usr/bin/env python3
"""Desktop controls. Subprocess arguments never pass through a shell."""
import fcntl
import html
import json
import os
from pathlib import Path
import re
import signal
import subprocess as sp
import sys
import time

HOME = Path.home()
STATE = HOME / '.local/state/rice'
STATE.mkdir(parents=True, exist_ok=True)
BOOST = STATE / 'audio-boost'
SINK = '@DEFAULT_AUDIO_SINK@'

def run(*args, check=False, **kwargs):
    p = sp.run([str(a) for a in args], capture_output=True, text=True, timeout=kwargs.pop('timeout', 35), **kwargs)
    if check and p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or f'{args[0]} failed')
    return p.stdout.strip()

def notify(message):
    run('notify-send', 'Desktop', message)

def menu(title, labels, search=False, message=None):
    args = ['rofi', '-dmenu', '-i', '-no-custom', '-format', 'i', '-p', title, '-mesg', html.escape(message or title.upper())]
    if not search:
        args += ['-theme-str', 'mainbox { children: [message,listview]; }']
    p = sp.run(args, input='\n'.join(str(x).replace('\n', ' ') for x in labels), text=True, capture_output=True)
    if p.returncode or not p.stdout.strip().isdigit():
        return None
    i = int(p.stdout)
    return i if i < len(labels) else None

def ask(title):
    p = sp.run(['rofi', '-dmenu', '-password', '-p', title], text=True, input='', capture_output=True)
    return p.stdout.rstrip('\n') if p.returncode == 0 else None

def audio(action):
    if action in ('up', 'down', 'mute', 'boost'):
        with (STATE / 'audio.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if action == 'mute':
                run('wpctl', 'set-mute', SINK, 'toggle', check=True)
            elif action == 'boost':
                if BOOST.exists():
                    value = float(run('wpctl', 'get-volume', SINK).split()[1])
                    if value > 1:
                        run('wpctl', 'set-volume', SINK, '1.0', check=True)
                    BOOST.unlink()
                else:
                    BOOST.touch(mode=0o600)
                notify('Volume ceiling: ' + ('150% (boost)' if BOOST.exists() else '100%'))
                try:
                    pid=int((STATE/'audio-watch.pid').read_text())
                    if b'audio_watch.py' in Path(f'/proc/{pid}/cmdline').read_bytes():os.kill(pid,signal.SIGUSR1)
                except (OSError,ValueError):pass
            else:
                run('wpctl', 'set-volume', '-l', '1.5' if BOOST.exists() else '1.0', SINK, '3%+' if action == 'up' else '3%-', check=True)
        return
    if action == 'status':
        value = run('wpctl', 'get-volume', SINK)
        if not value:
            print(json.dumps({'text': '󰝟 —', 'tooltip': 'No audio output'})); return
        percent = round(float(value.split()[1]) * 100)
        muted = 'MUTED' in value
        boosted = BOOST.exists()
        print(json.dumps({'text': ('󰝟' if muted else '') + f'\u2002\u2002{percent}%' + (' +' if boosted else ''),
            'tooltip': ('Middle click or F4: lock to 100%' if boosted else 'Middle click or F4: unlock 150%') + '\nWheel up/down: volume · Left click: mute\nRight click: output and application volume',
            'class': 'boosted' if boosted else ('muted' if muted else 'normal')}))
        return
    while True:
        sinks = json.loads(run('pactl', '-f', 'json', 'list', 'sinks', check=True))
        default = run('pactl', 'get-default-sink')
        labels = ['Mute / unmute', 'Volume…', 'Ceiling: ' + ('150% — lock to 100%' if BOOST.exists() else '100% — enable 150%'), 'Application volumes…']
        labels += [('● ' if s['name'] == default else '○ ') + s.get('description', s['name']) for s in sinks]
        order = list(range(4, len(labels))) + list(range(4))
        selected = menu('Sound', [labels[n] for n in order], message='SOUND  /  Output and volume')
        i = order[selected] if selected is not None else None
        if i is None: return
        if i == 0: audio('mute')
        elif i == 1:
            values = [0, 10, 25, 50, 75, 100] + ([125, 150] if BOOST.exists() else [])
            v = menu('Volume', [f'{v}%' for v in values])
            if v is not None: run('wpctl', 'set-volume', SINK, f'{values[v]}%', check=True)
        elif i == 2: audio('boost')
        elif i == 3:
            streams = json.loads(run('pactl', '-f', 'json', 'list', 'sink-inputs', check=True))
            if not streams: notify('No applications are playing audio.'); continue
            a = menu('Applications', [s.get('properties', {}).get('application.name', 'Application') + ' · ' + next(iter(s['volume'].values()))['value_percent'] for s in streams])
            if a is not None:
                values = [0, 25, 50, 75, 100]
                v = menu('Application volume', [f'{v}%' for v in values])
                if v is not None: run('pactl', 'set-sink-input-volume', streams[a]['index'], f'{values[v]}%', check=True)
        else:
            sink = sinks[i-4]['name']
            run('pactl', 'set-default-sink', sink, check=True)
            streams = json.loads(run('pactl', '-f', 'json', 'list', 'sink-inputs', check=True))
            for stream in streams:
                run('pactl', 'move-sink-input', stream['index'], sink, check=True)
            if not BOOST.exists():
                value = run('wpctl', 'get-volume', SINK)
                if value and float(value.split()[1]) > 1: run('wpctl', 'set-volume', SINK, '1.0')

def nm(*args, **kwargs):
    return run('nmcli', *args, **kwargs)

def fields(line):
    # nmcli escapes literal colons and backslashes in terse output.
    return [re.sub(r'\\(.)', r'\1', x) for x in re.split(r'(?<!\\):', line)]

def profiles():
    return [fields(l) for l in nm('-t', '-f', 'UUID,TYPE,NAME', 'connection', 'show').splitlines() if '802-11-wireless' in l]

def network():
    while True:
        saved = profiles()
        active = nm('-g', 'GENERAL.CON-UUID', 'device', 'show').splitlines()
        labels = ['Nearby networks…', 'Rescan', 'Wi-Fi: ' + nm('radio', 'wifi') + ' — toggle', 'Diagnostics', 'Hotspot auto-switch: ' + ('paused — resume' if (STATE/'hotspot-paused').exists() else 'enabled — pause')]
        labels += [('● ' if p[0] in active else '○ ') + p[2] for p in saved]
        order = list(range(5, len(labels))) + list(range(5))
        selected = menu('Network', [labels[n] for n in order], message='NETWORK  /  Remembered networks')
        i = order[selected] if selected is not None else None
        if i is None: return
        if i == 0:
            rows = [fields(l) for l in nm('-t', '-f', 'SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list', '--rescan', 'no').splitlines()]
            rows = list({r[0]: r for r in rows if len(r) == 3 and r[0]}.values())
            rows.sort(key=lambda r: int(r[1]), reverse=True)
            n = menu('Nearby networks', [f'{r[0]}  ·  {r[1]}%  ·  {r[2] or "Open"}' for r in rows], search=True)
            if n is None: continue
            ssid = rows[n][0]
            known = next((p for p in saved if nm('-g', '802-11-wireless.ssid', 'connection', 'show', 'uuid', p[0]) == ssid), None)
            if known: nm('connection', 'up', 'uuid', known[0], check=True)
            elif rows[n][2] in ('', '--'): nm('device', 'wifi', 'connect', ssid, check=True)
            else:
                password = ask('Wi-Fi password')
                if password is None: continue
                # Let nmcli request secrets via stdin; never put them in argv.
                p = sp.run(['nmcli', '--ask', 'device', 'wifi', 'connect', ssid], input=password+'\n', capture_output=True, text=True, timeout=60)
                if p.returncode: notify('Connection failed. Check password and signal.')
        elif i == 1: nm('device', 'wifi', 'rescan', check=True)
        elif i == 2: nm('radio', 'wifi', 'off' if nm('radio', 'wifi') == 'enabled' else 'on', check=True)
        elif i == 3:
            devices = [fields(line) for line in nm('-t', '-f', 'DEVICE,TYPE,STATE', 'device').splitlines()]
            detail = '\n'.join(nm('-f', 'GENERAL.DEVICE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS', 'device', 'show', d[0]) for d in devices if len(d) == 3 and d[1] in ('wifi', 'ethernet') and d[2] == 'connected')
            detail = detail or 'No active Wi-Fi or Ethernet connection.'
            menu('Diagnostics', ['Back'], message='Internet: ' + nm('networking', 'connectivity', 'check') + '\n' + detail)
        elif i == 4:
            path = STATE/'hotspot-paused'
            if path.exists(): path.unlink()
            else: path.touch()
        else:
            p = saved[i-5]
            a = menu(p[2], ['Connect', 'Disconnect', 'Forget saved network…'])
            if a == 0: nm('connection', 'up', 'uuid', p[0], check=True)
            elif a == 1: nm('connection', 'down', 'uuid', p[0], check=True)
            elif a == 2 and menu('Forget network?', ['Cancel', 'Forget ' + p[2]]) == 1:
                nm('connection', 'delete', 'uuid', p[0], check=True)

def network_status():
    import rice_status
    print(json.dumps(rice_status.network(), ensure_ascii=False))

def bluetooth():
    while True:
        controller = run('bluetoothctl', 'show')
        if not controller: notify('No Bluetooth controller detected.'); return
        powered = 'Powered: yes' in controller
        devices = []
        for line in run('bluetoothctl', 'devices').splitlines():
            parts = line.split(' ', 2)
            if len(parts) == 3:
                info = run('bluetoothctl', 'info', parts[1])
                devices.append((parts[1], parts[2], 'Connected: yes' in info, 'Paired: yes' in info))
        labels = ['Turn Bluetooth ' + ('off' if powered else 'on'), 'Scan for devices (8 seconds)', 'Select audio output…']
        labels += [('● ' if d[2] else '○ ') + d[1] + (' · paired' if d[3] else ' · new') for d in devices]
        order = list(range(3, len(labels))) + list(range(3))
        selected = menu('Bluetooth', [labels[n] for n in order])
        i = order[selected] if selected is not None else None
        if i is None: return
        if i == 0: run('bluetoothctl', 'power', 'off' if powered else 'on', check=True)
        elif i == 1:
            run('bluetoothctl', 'power', 'on', check=True)
            notify('Scanning for Bluetooth devices…')
            run('bluetoothctl', '--timeout', '8', 'scan', 'on', timeout=12)
        elif i == 2: audio('menu')
        else:
            addr, name, connected, paired = devices[i-3]
            a = menu(name, ['Disconnect' if connected else 'Connect', 'Pair / trust', 'Forget device…'])
            if a == 0:
                if not paired and not connected:
                    sp.run(['python3', str(HOME/'.local/lib/rice/bluetooth_pair.py'), addr], check=True)
                else:
                    run('bluetoothctl', 'disconnect' if connected else 'connect', addr, check=True)
            elif a == 1:
                sp.run(['python3', str(HOME/'.local/lib/rice/bluetooth_pair.py'), addr], check=True)
            elif a == 2 and menu('Forget device?', ['Cancel', 'Forget ' + name]) == 1:
                run('bluetoothctl', 'remove', addr, check=True)

def power():
    actions = ['Lock', 'Suspend', 'Log out', 'Restart', 'Shut down']
    i = menu('Session', ['󰌾  Lock', '󰤄  Suspend', '󰍃  Log out', '󰜉  Restart', '  Shut down'], message='SESSION  /  Esc to cancel')
    if i is None: return
    if i >= 2 and menu(actions[i], ['Cancel', actions[i]], message=actions[i] + '? Unsaved work may be lost.') != 1: return
    if i == 0: sp.Popen([str(HOME/'.local/bin/lock-screen')], start_new_session=True)
    elif i == 1:
        # hypridle's before_sleep_cmd locks before suspend.
        run('systemctl', 'suspend', check=True)
    elif i == 2: run('hyprctl', 'dispatch', 'hl.dsp.exit()', check=True)
    elif i == 3: run('systemctl', 'reboot', check=True)
    else: run('systemctl', 'poweroff', check=True)

def settings():
    while True:
        i = menu('Settings', ['Brightness…', 'Sound…', 'Wi-Fi / Ethernet…', 'Bluetooth…', 'System monitor', 'Edit desktop configuration'])
        if i is None: return
        if i == 0:
            current = run('brightnessctl', '-m').split(',')
            levels = [5, 10, 20, 35, 50, 65, 80, 100]
            n = menu('Brightness', [f'{v}%' for v in levels], message='BRIGHTNESS  /  Current ' + (current[3] if len(current)>3 else 'unknown'))
            if n is not None: run('brightnessctl', 'set', f'{levels[n]}%', check=True)
        elif i == 1: audio('menu')
        elif i == 2: network()
        elif i == 3: bluetooth()
        elif i == 4: sp.Popen(['kitty', 'btop']); return
        else: sp.Popen(['code', str(HOME/'config')]); return

if __name__ == '__main__':
    try:
        action = sys.argv[1]
        if action == 'audio': audio(sys.argv[2] if len(sys.argv)>2 else 'menu')
        elif action == 'network': network()
        elif action == 'network-status': network_status()
        elif action == 'bluetooth': bluetooth()
        elif action == 'power': power()
        elif action == 'settings': settings()
    except (OSError, ValueError, RuntimeError, sp.SubprocessError) as exc:
        notify(str(exc))
        sys.exit(1)
