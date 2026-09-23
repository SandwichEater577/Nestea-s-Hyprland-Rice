"""Read optional, locally encrypted rice preferences.

NetworkManager and BlueZ remain responsible for connection credentials and pairing.
"""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None
    InvalidTag = ValueError


DATA_FILE = Path.home() / '.config/rice/private.json.enc'
KEY_FILE = Path.home() / '.local/share/rice/data.key'
WIFI_FILE = Path.home() / '.config/rice/WiFi-Options.json'
BLUETOOTH_FILE = Path.home() / '.config/rice/Bluetooth-Options.json'


def stamp(path):
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


@lru_cache(maxsize=8)
def _load(stamps):
    data = {}
    try:
        if AESGCM and DATA_FILE.is_file() and KEY_FILE.is_file():
            payload = DATA_FILE.read_bytes()
            key = hashlib.sha256(KEY_FILE.read_bytes()).digest()
            saved = json.loads(AESGCM(key).decrypt(payload[:12], payload[12:], None))
            if isinstance(saved, dict):
                data.update(saved)
    except (OSError, ValueError, InvalidTag):
        pass
    for path in (WIFI_FILE, BLUETOOTH_FILE):
        try:
            saved = json.loads(path.read_text())
            if isinstance(saved, dict):
                data.update(saved)
        except (OSError, ValueError):
            pass
    return data


def load_private_data():
    return _load(tuple(stamp(path) for path in (DATA_FILE, KEY_FILE, WIFI_FILE, BLUETOOTH_FILE)))
