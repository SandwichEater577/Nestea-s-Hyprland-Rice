# Optional encrypted preferences

Current setup uses local JSON preference files at `~/.config/rice/WiFi-Options.json`, `Bluetooth-Options.json`, and `Media-Options.json`. Wi-Fi passwords remain with NetworkManager and Bluetooth pairing keys with BlueZ.

The legacy encrypted `~/.config/rice/private.json.enc` is still read for Wi-Fi hotspot and display labels. Edit it with `python3 src/data/edit.py`; its key lives at `~/.local/share/rice/data.key`. Both are private and absent from Git. Back up both if you use this legacy format. The editor needs Python's `cryptography` package.
