"""Output choices include ports hidden by the currently active ALSA profile."""
import json
import time


def _port_name(port):
    value = port.get('active_port', '')
    return value.get('name', '') if isinstance(value, dict) else value


def _card_name(sink):
    return sink.get('properties', {}).get('device.name', '')


def _label(port):
    kind = (port.get('type', '') + ' ' + port.get('description', '')).lower()
    if 'headphone' in kind or 'headset' in kind:
        return 'Wired headset', 'Headphone jack', 'audio-headphones-symbolic'
    if 'speaker' in kind:
        return 'Laptop speakers', 'Built-in audio', 'audio-speakers-symbolic'
    return port.get('description', 'Audio output'), 'Built-in audio', 'audio-speakers-symbolic'


def choices(sinks, cards, default):
    """Return active sinks plus available local output routes in other profiles."""
    result = []
    covered = set()
    for card in cards:
        card_name = card.get('name', '')
        if not card_name.startswith('alsa_card.'):
            continue
        profiles = card.get('profiles') or {}
        for port_name, port in (card.get('ports') or {}).items():
            if not port_name.startswith('[Out]') or port.get('availability') == 'not available':
                continue
            candidates = [name for name in port.get('profiles', [])
                          if profiles.get(name, {}).get('available') is not False
                          and profiles.get(name, {}).get('sinks', 0) > 0]
            if not candidates:
                continue
            active = card.get('active_profile', '')
            profile = active if active in candidates else max(
                candidates, key=lambda name: profiles[name].get('priority', 0))
            sink = next((item for item in sinks if _card_name(item) == card_name
                         and _port_name(item) == port_name), None)
            title, detail, icon = _label(port)
            result.append(dict(title=title, detail=detail, icon=icon,
                               card=card_name, profile=profile, port=port_name,
                               sink=sink['name'] if sink else '',
                               selected=bool(sink and sink['name'] == default)))
            if sink:
                covered.add(sink['name'])
    for sink in sinks:
        if sink['name'] in covered:
            continue
        port = _port_name(sink).lower()
        name = sink.get('description', sink['name'])
        if sink['name'].startswith('bluez_output.'):
            title, detail, icon = name, 'Bluetooth audio', 'audio-headphones-symbolic'
        elif 'hdmi' in sink['name'].lower():
            title, detail, icon = 'Display audio', name, 'video-display-symbolic'
        elif 'headphone' in port:
            title, detail, icon = 'Wired headset', 'Headphone jack', 'audio-headphones-symbolic'
        else:
            title, detail, icon = name, 'Audio output', 'audio-speakers-symbolic'
        result.append(dict(title=title, detail=detail, icon=icon, sink=sink['name'],
                           card='', profile='', port='', selected=sink['name'] == default))
    return result


def input_choices(sources, default):
    result = []
    for source in sources:
        name = source.get('name', '')
        if not name or name.endswith('.monitor'):
            continue
        port = _port_name(source).lower()
        description = source.get('description', name)
        if 'digital microphone' in description.lower() or 'digital' in port:
            title, detail = 'Laptop microphone', 'Built-in microphone'
        elif ('mic' in port and source.get('properties', {}).get('device.api') == 'alsa'
              and any(item.get('availability_group') for item in source.get('ports', []))):
            title, detail = 'Wired headset mic', 'Headphone jack'
        else:
            title, detail = description, 'Microphone input'
        result.append(dict(title=title, detail=detail,
                           icon='audio-input-microphone-symbolic', source=name,
                           selected=name == default, muted=source.get('mute', False)))
    return result


def select(route, run, boost_enabled=False):
    """Activate a card profile if necessary, then route the default and live streams."""
    sink_name = route['sink']
    if route['card'] and not sink_name:
        old_default = run('pactl', 'get-default-source')
        old_sources = json.loads(run('pactl', '-f', 'json', 'list', 'sources', check=True))
        old_input = next((source for source in old_sources if source.get('name') == old_default
                          and _card_name(source) == route['card']), None)
        run('pactl', 'set-card-profile', route['card'], route['profile'], check=True)
        for _ in range(20):
            sinks = json.loads(run('pactl', '-f', 'json', 'list', 'sinks', check=True))
            sink = next((item for item in sinks if _card_name(item) == route['card']
                         and _port_name(item) == route['port']), None)
            if sink:
                sink_name = sink['name']
                break
            time.sleep(0.1)
        if not sink_name:
            raise RuntimeError('The selected audio output did not become available')
        if old_input:
            for _ in range(20):
                sources = json.loads(run('pactl', '-f', 'json', 'list', 'sources', check=True))
                replacement = next((source for source in sources if _card_name(source) == route['card']
                                    and _port_name(source) == _port_name(old_input)), None)
                if replacement:
                    run('pactl', 'set-default-source', replacement['name'], check=True)
                    captures = json.loads(run('pactl', '-f', 'json', 'list', 'source-outputs', check=True))
                    for capture in captures:
                        run('pactl', 'move-source-output', capture['index'], replacement['name'], check=True)
                    run('pactl', 'set-source-mute', replacement['name'],
                        '1' if old_input.get('mute') else '0', check=True)
                    break
                time.sleep(0.1)
    run('pactl', 'set-default-sink', sink_name, check=True)
    streams = json.loads(run('pactl', '-f', 'json', 'list', 'sink-inputs', check=True))
    for stream in streams:
        run('pactl', 'move-sink-input', stream['index'], sink_name, check=True)
    if not boost_enabled:
        volume = run('wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@')
        if volume and float(volume.split()[1]) > 1:
            run('wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '1.0', check=True)


def select_input(route, run):
    source = route['source']
    run('pactl', 'set-default-source', source, check=True)
    streams = json.loads(run('pactl', '-f', 'json', 'list', 'source-outputs', check=True))
    for stream in streams:
        run('pactl', 'move-source-output', stream['index'], source, check=True)
    run('pactl', 'set-source-mute', source, '0', check=True)
