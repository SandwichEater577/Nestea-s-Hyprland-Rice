# Personal Hyprland rice

A dark, monochrome Hyprland desktop built around Waybar, Rofi, Kitty, Hyprpaper,
and small Python controls. This repository contains the source files for the
running setup; local profiles, credentials, caches, screenshots, and wallpapers
are outside Git.

The Lua files at the repository root generate native config with:

```sh
lua ~/config/apply.lua
```

`~/.config/hypr/hyprland.lua` currently points to `~/config/hyprland.lua`. A text
Hyprland version is kept in `native/hyprland.conf`. Check your Hyprland version
before selecting either parser. This laptop's monitor, battery, and scaling
settings are examples to adapt on another machine.
This laptop's `HDMI-A-1` projector is configured to mirror `eDP-1` at
1920×1200; the generic monitor rule still handles other outputs.

The `local/bin` and `local/lib` trees mirror the scripts installed under
`~/.local`. To install on another machine, copy those curated trees to the same
locations, regenerate the native config, and start Waybar using
`~/.local/bin/start-waybar`. The optional hotspot user service is in `systemd`.
The Waybar tooltip helper source is included; its compiled `.so` is local only.

## Private data

Wi-Fi display labels, an optional preferred hotspot SSID, and Bluetooth display
labels live in `data/private.json.enc` on this machine. Edit them with
`python3 ~/config/data/edit.py`. The ciphertext is ignored by Git, and its key
lives outside the repository at `~/.local/share/rice/data.key`. Python's
`cryptography` package is required for this feature. On a fresh install, the
controls work without this file; the hotspot preference stays disabled until
configured.

Wi-Fi passwords are stored by NetworkManager and Bluetooth pairing keys by
BlueZ. Neither store is included here. Never add connection exports, browser
profiles, `.env` files, keys, or the encrypted local data file to Git. Keep a
private backup of both the encrypted file and its key.

## Controls

Sound: left click mutes, pressing the mouse wheel over the sound widget toggles
the 100% or 150% ceiling, right click opens outputs and app volume, and each
wheel step adjusts volume. Wi-Fi: right click
opens the network panel; the bar shows signal and download rate. Bluetooth
opens pairing and connection controls. Spotify controls appear only while its
player is available. Super+T changes wallpaper; Super+R opens Rofi.

The source tree is intentionally allowlisted in `.gitignore`: `git add -A` can
only stage the curated files. Review `git status` and `git diff --cached` before
any push.
