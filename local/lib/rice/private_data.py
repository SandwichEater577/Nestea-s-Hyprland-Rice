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


DATA_FILE = Path.home() / 'config/data/private.json.enc'
KEY_FILE = Path.home() / '.local/share/rice/data.key'


@lru_cache(maxsize=1)
def load_private_data():
    if AESGCM is None or not DATA_FILE.is_file() or not KEY_FILE.is_file():
        return {}
    try:
        payload = DATA_FILE.read_bytes()
        key = hashlib.sha256(KEY_FILE.read_bytes()).digest()
        data = json.loads(AESGCM(key).decrypt(payload[:12], payload[12:], None))
    except (OSError, ValueError, InvalidTag):
        return {}
    return data if isinstance(data, dict) else {}
