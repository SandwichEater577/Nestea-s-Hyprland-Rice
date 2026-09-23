#!/usr/bin/env python3
"""Check a preferred hotspot every three seconds without undoing manual changes."""
import subprocess
import time

from desktop import STATE, fields, nm, profiles
from private_data import load_private_data

CHECK_SECONDS = 3
SCAN_SECONDS = 9  # A scan every tick can make some Wi-Fi drivers drop traffic.


def check(ssid, seen, last_scan):
    if not ssid or (STATE / 'hotspot-paused').exists() or nm('radio', 'wifi') != 'enabled':
        return False, last_scan
    rows = [fields(line) for line in nm('-t', '-f', 'DEVICE,TYPE,STATE', 'device').splitlines()]
    wifi = next((row[0] for row in rows if len(row) > 2 and row[1] == 'wifi'), None)
    wired = any(len(row) > 2 and row[1] == 'ethernet' and row[2] == 'connected' for row in rows)
    if not wifi or wired:
        return False, last_scan
    now = time.monotonic()
    if now - last_scan >= SCAN_SECONDS:
        # NetworkManager keeps the last scan's access points available while
        # this request is in progress. Scan errors are harmless here.
        try:
            subprocess.run(['nmcli', 'device', 'wifi', 'rescan', 'ifname', wifi],
                           capture_output=True, timeout=2, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
        last_scan = now
    available = {fields(line)[0] for line in
                 nm('-t', '-f', 'SSID', 'device', 'wifi', 'list', '--rescan', 'no', 'ifname', wifi).splitlines()}
    target = next((row for row in profiles() if len(row) > 2 and row[2] == ssid), None)
    present = target is not None and ssid in available
    if present and not seen:
        active = nm('-g', 'GENERAL.CON-UUID', 'device', 'show', wifi)
        if active != target[0]:
            nm('--wait', '20', 'connection', 'up', 'uuid', target[0], 'ifname', wifi, check=True)
        return True, last_scan
    return present and seen, last_scan


def main():
    seen = False
    previous_ssid = ''
    last_scan = -SCAN_SECONDS
    while True:
        started = time.monotonic()
        try:
            ssid = load_private_data().get('hotspot_ssid', '')
            if ssid != previous_ssid:
                seen = False
                previous_ssid = ssid
            seen, last_scan = check(ssid, seen, last_scan)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
            # A transient NetworkManager failure must not stop future checks.
            pass
        time.sleep(max(0, CHECK_SECONDS - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
