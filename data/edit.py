#!/usr/bin/env python3
"""Edit ignored local preferences and encrypt them before closing."""

import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import tempfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


HOME = Path.home()
KEY = HOME / '.local/share/rice/data.key'
DATA = Path(__file__).with_name('private.json.enc')


def main():
    KEY.parent.mkdir(parents=True, exist_ok=True)
    if not KEY.exists():
        fd = os.open(KEY, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as file:
            file.write(secrets.token_urlsafe(48) + '\n')
    key = hashlib.sha256(KEY.read_bytes()).digest()
    initial = {'hotspot_ssid': '', 'wifi_labels': {}, 'bluetooth_labels': {}}
    if DATA.exists():
        payload = DATA.read_bytes()
        initial = json.loads(AESGCM(key).decrypt(payload[:12], payload[12:], None))
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
    fd, path = tempfile.mkstemp(prefix='rice-data-', suffix='.json', dir=runtime)
    try:
        with os.fdopen(fd, 'w') as file:
            json.dump(initial, file, indent=2, ensure_ascii=False)
            file.write('\n')
        editor = shlex.split(os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'nano')
        subprocess.run([*editor, path], check=True)
        updated = json.loads(Path(path).read_text())
        if not isinstance(updated, dict):
            raise ValueError('Expected a JSON object')
        nonce = os.urandom(12)
        encrypted = nonce + AESGCM(key).encrypt(nonce, json.dumps(updated).encode(), None)
        temp = DATA.with_suffix('.enc.tmp')
        with temp.open('wb') as file:
            file.write(encrypted)
        temp.chmod(0o600)
        temp.replace(DATA)
        print('Saved encrypted local preferences.')
    finally:
        Path(path).unlink(missing_ok=True)


if __name__ == '__main__':
    main()
