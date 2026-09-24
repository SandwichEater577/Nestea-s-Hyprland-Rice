#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
dry=${1:-}
[[ -z $dry || $dry == --dry-run || $dry == --monitors ]] || { echo 'usage: install.sh [--dry-run|--monitors]' >&2; exit 2; }
source "$repo/src/installer/monitors.sh"
if [[ $dry == --monitors ]]; then rice_monitors_generate; exit 0; fi

step() {
    if [[ ${RICE_UPDATE_PROGRESS:-} == 1 ]]; then
        printf 'RICE_PROGRESS_STEP=%s\t%s\n' "$1" "$2" >&2
    fi
    printf '\n\033[1m[%s]\033[0m %s\n' "$1" "$2"
}
plan() { if [[ $dry == --dry-run ]]; then printf '  would %s\n' "$*"; return 0; fi; }

step 1 'Source and private settings'
plan 'link this repository as ~/.local/share/rice/source'
if [[ $dry != --dry-run ]]; then
    mkdir -p "$HOME/.local/share/rice" "$HOME/.config/rice" "$HOME/.local/state/rice"
    ln -sfn "$repo" "$HOME/.local/share/rice/source"
    for name in WiFi Bluetooth Media; do
        if [[ ! -e $HOME/.config/rice/${name}-Options.json ]]; then
            install -m 600 "$repo/${name}-Options.example.json" "$HOME/.config/rice/${name}-Options.json"
        fi
    done
    if [[ ! -e $HOME/.config/rice/settings.json ]]; then
        "$repo/src/bin/rice-clock" set 24h >/dev/null
    fi
    for file in private.json.enc display-layout.tsv; do
        if [[ -f $repo/data/$file && ! -e $HOME/.config/rice/$file ]]; then
            install -m 600 "$repo/data/$file" "$HOME/.config/rice/$file"
        fi
    done
    rice_monitors_generate
fi

step 2 'Programs and config generation'
plan 'copy curated helpers to ~/.local/bin and ~/.local/lib/rice'
plan 'generate Kitty, Rofi, Hyprland companions and other configs from Lua'
if [[ $dry != --dry-run ]]; then
    mkdir -p "$HOME/.local/bin" "$HOME/.local/lib/rice" \
             "$HOME/.config/systemd/user" "$HOME/.config/hypr" \
             "$HOME/.config/fastfetch" "$HOME/.config/kitty" "$HOME/.config/mako" \
             "$HOME/.config/cava" "$HOME/.config/rofi"
    find "$repo/src/bin" -maxdepth 1 -type f -exec cp -a -t "$HOME/.local/bin" {} +
    find "$repo/src/lib/rice" -maxdepth 1 -type f -exec cp -a -t "$HOME/.local/lib/rice" {} +
    chmod +x "$HOME/.local/bin/"*
    for name in build-rice-bar start-waybar ui-backend waybar-spotify rice-media-watch; do
        [[ ! -f $HOME/.local/bin/$name ]] || unlink "$HOME/.local/bin/$name"
    done
    lua "$repo/src/config/apply.lua"
    # Apply notification styling (right-aligned dismiss ✕) without waiting for
    # a session restart; makoctl talks to mako over the session bus.
    if command -v makoctl >/dev/null 2>&1; then makoctl reload >/dev/null 2>&1 || true; fi
    ln -sfn "$repo/src/config/hyprland.lua" "$HOME/.config/hypr/hyprland.lua"
    cp -a "$repo/src/native/hyprland.conf" "$HOME/.config/hypr/hyprland.conf"
fi

step 3 'Wallpaper palette'
plan 'restore the current wallpaper and QuickShell palette'
if [[ $dry != --dry-run ]]; then
    if [[ -n ${WAYLAND_DISPLAY:-} ]] && pgrep -x hyprpaper >/dev/null; then
        "$HOME/.local/bin/change-wallpaper" --restore || python3 "$HOME/.local/lib/rice/wallpaper_palette.py"
    else
        python3 "$HOME/.local/lib/rice/wallpaper_palette.py"
    fi
fi

step 4 'User services'
plan 'link and enable the QuickShell bar, control panel, updater and preferred hotspot user services'
plan 'record the deployed revision for future update checks'
if [[ $dry != --dry-run ]]; then
    systemctl --user disable --now rice-media-watch.service >/dev/null 2>&1 || true
    [[ ! -L $HOME/.config/systemd/user/rice-media-watch.service ]] || unlink "$HOME/.config/systemd/user/rice-media-watch.service"
    ln -sfn "$repo/src/systemd/rice-bar.service" "$HOME/.config/systemd/user/rice-bar.service"
    ln -sfn "$repo/src/systemd/rice-controls.service" "$HOME/.config/systemd/user/rice-controls.service"
    ln -sfn "$repo/src/systemd/rice-hotspot.service" "$HOME/.config/systemd/user/rice-hotspot.service"
    ln -sfn "$repo/src/systemd/rice-update-watch.service" "$HOME/.config/systemd/user/rice-update-watch.service"
    # rice-update.service is deliberately not enabled; the settings panel starts
    # it on demand and it has no install section.
    ln -sfn "$repo/src/systemd/rice-update.service" "$HOME/.config/systemd/user/rice-update.service"
    systemctl --user daemon-reload
    systemctl --user enable rice-bar.service rice-controls.service rice-hotspot.service rice-update-watch.service
    systemctl --user restart rice-update-watch.service
    if [[ -n ${WAYLAND_DISPLAY:-} ]]; then systemctl --user restart rice-controls.service; fi
    systemctl --user restart rice-hotspot.service
    if [[ -n ${WAYLAND_DISPLAY:-} ]]; then
        "$HOME/.local/bin/start-bar"
        systemctl --user restart rice-bar.service
    fi
    if revision=$(git -C "$repo" rev-parse --verify HEAD 2>/dev/null); then
        printf '%s\n' "$revision" > "$HOME/.local/state/rice/installed-revision.tmp"
        mv "$HOME/.local/state/rice/installed-revision.tmp" "$HOME/.local/state/rice/installed-revision"
    fi
fi
step 5 'Done · Hyprland Lua and QuickShell bar ready'
