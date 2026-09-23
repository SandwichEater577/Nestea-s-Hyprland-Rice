#!/usr/bin/env python3
"""Switch once on hotspot appearance; respect manual changes until it disappears."""
import json
import subprocess
import time
from pathlib import Path
from desktop import nm, profiles, fields, STATE
from private_data import load_private_data

HOTSPOT_SSID = load_private_data().get('hotspot_ssid', '')

seen = False
failures = 0
while True:
    try:
        if not HOTSPOT_SSID or (STATE/'hotspot-paused').exists() or nm('radio', 'wifi') != 'enabled':
            time.sleep(15)
            continue
        rows = [fields(l) for l in nm('-t', '-f', 'DEVICE,TYPE,STATE', 'device').splitlines()]
        wifi = next((r[0] for r in rows if len(r)>2 and r[1]=='wifi'), None)
        wired = any(len(r)>2 and r[1]=='ethernet' and r[2]=='connected' for r in rows)
        if wifi and not wired:
            nm('device', 'wifi', 'rescan', 'ifname', wifi)
            time.sleep(3)
            available = nm('-t', '-f', 'SSID', 'device', 'wifi', 'list', '--rescan', 'no', 'ifname', wifi).splitlines()
            target = next((p for p in profiles() if p[2] == HOTSPOT_SSID), None)
            present = target is not None and HOTSPOT_SSID in available
            if present and not seen:
                active = nm('-g', 'GENERAL.CON-UUID', 'device', 'show', wifi)
                if active != target[0]:
                    nm('--wait', '20', 'connection', 'up', 'uuid', target[0], 'ifname', wifi, check=True)
                seen = True
                failures = 0
            elif not present:
                seen = False
                failures = 0
    except (OSError, RuntimeError, subprocess.SubprocessError):
        failures += 1
    time.sleep(min(120, 20 * (1 + failures)))
