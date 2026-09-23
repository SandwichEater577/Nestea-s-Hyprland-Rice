Local preferences live in `private.json.enc`. It is encrypted with AES-256-GCM and
ignored by Git. The key is `~/.local/share/rice/data.key`, also outside the repo.
Back up both files privately: neither can be recovered from GitHub.

Run `python3 ~/config/data/edit.py` to edit Wi-Fi display labels, the preferred
hotspot SSID, and optional Bluetooth display labels. The editor opens a temporary
0600 file under `XDG_RUNTIME_DIR` and removes it after encryption. Restart the
hotspot service after changing its SSID; reopen the control panel for new labels.

Wi-Fi passwords stay in NetworkManager's own private connection store. Bluetooth
pairing keys stay with BlueZ. This rice never copies those secrets into its repo.
