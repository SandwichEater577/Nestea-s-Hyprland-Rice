# Nestea's Rice for Hyprland

A monochrome Hyprland desktop with a QuickShell topbar. Hyprland and the other desktop application configs remain Lua based. The bar keeps the existing controls, media selection, clock settings, and wallpaper colors.

## Start from zero

On Arch Linux or EndeavourOS, clone the repository, then run the terminal installer:

```sh
git clone https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice.git ~/config
cd ~/config
./Installer --check
./Installer --deps       # optional; reviews Arch packages before installing
./Installer
```

The installer asks one question at a time: clock format, desktop and browser media, display scale, Wi-Fi, Bluetooth, and optional Arch packages. Review your answers at the end, then choose whether to install. Arrow keys move between answers; Enter selects. The six-dot indicator shows progress during installation. Run `./Installer --install` for a non-interactive refresh. Set `NO_COLOR=1` for plain terminal output. The short `./install.sh` wrapper also works.

The install links this checkout at `~/.local/share/rice/source`. Keep the checkout after installing. Edit sources in `src/`, then run `./Installer --install` to deploy them. QuickShell reads its QML from this checkout. To regenerate the remaining Lua-produced configs, use `lua src/config/apply.lua`.

The initial setup expects Hyprland, NetworkManager, BlueZ, PipeWire, a Wayland session, and the programs reported by `./Installer --check`. QuickShell is required for the topbar. The package step asks before invoking `sudo pacman` and does not install hardware drivers or change the kernel.

If the readiness check reports inactive network or Bluetooth services, choose the service prompt in `./Installer --deps` or run `sudo systemctl enable --now NetworkManager bluetooth`. Log into Hyprland before the first live bar preview; the installer can still generate files from a plain terminal.

## Repository layout

| Path | Purpose |
| --- | --- |
| `Installer` | Terminal setup, preferences and readiness |
| `src/config/` | Lua sources that generate desktop configs |
| `src/bin/`, `src/lib/` | Installed commands and shared readers |
| `src/quickshell/` | Topbar QML and reusable button component |
| `src/native/hyprland.conf` | Text fallback for Hyprland; the Lua config remains primary |
| `src/data/` | Update descriptions (`updates.json`) and private-data editors |
| `src/installer/`, `src/systemd/` | Install logic and user services |
| `AGENTS.md` | Instructions for AI assistants adding and shipping features |
| `wallpaper/` | Add your own PNG, JPEG or WebP images here |
| `*-Options.example.json` | Safe templates copied to private local settings |

## Wi-Fi and Bluetooth

Use `nmtui` (or the bar's Network menu) to connect to Wi-Fi. NetworkManager stores the password and remembered connection. Use the bar's Bluetooth menu or `bluetoothctl` to pair; BlueZ stores pairing keys. The installer offers both setup tools.

The installer creates `~/.config/rice/WiFi-Options.json` and `Bluetooth-Options.json` from the examples. These files only set labels and preferences. `wifi_labels` maps an SSID to a display label; `hotspot_ssid` identifies an optional preferred network for the hotspot helper. `bluetooth_labels` maps device addresses to display labels. The `preferred_connection_uuids` and `preferred_device_addresses` arrays are reserved for future connection policy and currently do not trigger automatic joins. Keep secrets in NetworkManager and BlueZ, never in these JSON files.

An older encrypted preference file is supported at `~/.config/rice/private.json.enc`; edit it with `python3 src/data/edit.py` if you already use it. The installer migrates a local legacy copy when present. See [src/data/README.md](src/data/README.md).

## Media controls

**Desktop Spotify** is enabled by default. **Browser media** is optional in the installer and live Media settings. It can use Spotify Web, SoundCloud, YouTube Music, and other sites when your browser exposes an MPRIS player through the desktop. Supported browser player names include Chromium, Chrome, Brave, Firefox, Vivaldi, Edge, and Opera. The bar shows media controls only while an enabled player is available. Play/pause, next/previous, cover art, and available repeat/shuffle controls use the same actions in the bar and Media page. Album details appear on cover hover after 300 ms.

Use `rice-media get`, `rice-media set desktop_spotify on|off`, or `rice-media set browser_media on|off` from a terminal. The settings live in `~/.config/rice/Media-Options.json`. Browser integration depends on that browser's MPRIS support and the site providing media metadata; the installer does not add browser extensions.

Audio and media changes wake the bar on PipeWire/MPRIS events. Network and Bluetooth discovery use slower background refreshes. Volume wheel steps, play/pause, and track changes are reflected without waiting for a scan cycle.

## Bar, clock and wallpaper

QuickShell runs the topbar through `rice-bar.service` and reads `src/quickshell/shell.qml` directly from the checkout. The installer restarts that service after an update; `systemctl --user restart rice-bar.service` refreshes it manually. Bar engine selection is no longer part of setup or Settings.

The clock can be changed to 12 or 24 hour format in the installer, live Settings menu, or with `rice-clock set 12h|24h`. Its setting is in `~/.config/rice/settings.json`.

Put images in `wallpaper/`. **Super+T** changes wallpaper and generates the QuickShell palette in the same action. QuickShell watches that file and changes colors without restarting. Original images are untouched. The generated palette is in `~/.local/state/rice/palette.json`.

The sampled colors for each image are cached in `~/.cache/rice/wallpaper-palettes/`. Later visits reuse that palette; changing an image's size or modification time recomputes it.

The installer detects the primary output in a running Hyprland session and writes local display rules in `~/.config/rice/display-device.tsv` and `monitors.conf`. Adjust scale in the installer or live Displays menu. Connected secondary displays can be mirrored or extended from Displays; their choices live in `~/.config/rice/display-layout.tsv`. On another machine, review these local files rather than copying this laptop's output names. The Lua source used at login is `src/config/hyprland.lua`; a text fallback is `src/native/hyprland.conf`.

## Updates

`rice-update-watch.service` checks the upstream repository every 30 minutes and sends a desktop notification when new commits are published. The notification stays until dismissed: click it (the ✕ near the right edge marks the spot) and mako closes it. Nothing is ever installed automatically — the user always chooses when to download.

The installer records the last deployed commit separately from the checkout's Git HEAD. A newer commit in the source directory does not count as installed until the installer has successfully refreshed the desktop files and services.

Every commit is tracked on its own in `~/.local/state/rice/update.json` under `updates`, keyed by its twelve character Git hash. New releases also have a five-digit hex ID, starting at `0x00001`, shown in the update UI. Entries contain `new`, `summary`, `detail`, `kind` (`optional` or `recommended`), `applied` and `when` fields:

- **Download update** appears at the very top of the Settings menu only while some update is still new (never seen). An **Ignore** button sits beside it: it flips `new` to false, so the row disappears and the update is reachable only from **Update history** — it is never lost and never forced.
- Clicking **Download update** closes Settings and opens a centered confirmation window with the update description. **Install** opens a persistent progress window, then starts `rice-update.service`. Git reports its actual transfer counts, and the installer reports completed stages; work with no measurable total shows activity without a made-up percentage. The window stays open until installation succeeds or fails.
- **Update history** at the bottom of the Settings menu (below **Share an idea**) opens the same centered window listing every known update with a one line description and an `(optional)` or `(recommended)` tag. Clicking an entry opens its detail overlay; applied updates show when they landed, and ignored ones can still be downloaded from there.

Descriptions and IDs come from `src/data/updates.json`, then `Rice-Update-Summary` / `Rice-Update-Detail` / `Rice-Update-Kind` / `Rice-Update-ID` commit trailers, then the commit subject itself. When nothing is new, the top row shows the last check time and re-checks on click.

Check or apply from a terminal with `rice-update check` and `rice-update apply`. Checking uses the checkout's own remote first and falls back to the public HTTPS mirror, so a default HTTPS clone needs no credentials while an SSH remote needs a registered key. **Share an idea** at the bottom of the Settings menu opens a new issue on this repository.

## Controls and troubleshooting

The bar's audio widget adjusts volume by wheel, mutes on left click, toggles the 100%/150% ceiling on middle click, and opens output/app volume on right click. The network and Bluetooth widgets open their control menus. The clock and battery show information without click actions. The media cover opens the Media page; hover shows track details. Workspace buttons 1–5 stay visible, along with every workspace containing a window and the current workspace even when empty. A thin outline marks a workspace requesting attention (for example, when Brave opens a tab there from another workspace); visiting it clears the outline. Buttons switch via Hyprland's dispatch API.

Check services with `systemctl --user status rice-bar rice-controls rice-hotspot rice-update-watch`. Inspect their logs with `journalctl --user -u rice-bar -u rice-controls -u rice-hotspot -u rice-update-watch -b`. `./Installer --check` reports missing commands.

Local connection data, wallpaper images, caches, keys and screenshots are ignored by Git. Review `git status` before publishing changes.
