"""Anonymous active-machine check-in for update checks.

No raw machine ID or network address is written to rice state. A check-in only
runs after installation and a public HTTPS endpoint has been configured.
"""
import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

HOME = Path.home()
SOURCE_CONFIG = HOME / '.local/share/rice/source/src/data/telemetry.json'
PRIVATE_CONFIG = HOME / '.config/rice/telemetry.json'
LAST_REPORT = HOME / '.local/state/rice/telemetry-last-report'
FOUR_HOURS = 4 * 3600


def maybe_check_in(now=None):
    now = time.time() if now is None else now
    try:
        if not json.loads(PRIVATE_CONFIG.read_text()).get('enabled'):
            return False
        endpoint = json.loads(SOURCE_CONFIG.read_text()).get('endpoint', '').rstrip('/')
        if not endpoint.startswith('https://'):
            return False
        if now - float(LAST_REPORT.read_text()) < FOUR_HOURS:
            return False
        machine_id = Path('/etc/machine-id').read_text().strip()
        if len(machine_id) < 16:
            return False
        digest = hashlib.sha256(('nestea-rice-active-v1:' + machine_id).encode()).hexdigest()
        payload = json.dumps({'id': digest}).encode()
        request = Request(endpoint + '/check-in', data=payload,
                          headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=2.5) as response:
            if response.status != 204:
                return False
        LAST_REPORT.parent.mkdir(parents=True, exist_ok=True)
        LAST_REPORT.write_text(str(now) + '\n')
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False
