#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
dry=${1:-}
[[ -z $dry || $dry == --dry-run || $dry == --monitors ]] || { echo 'usage: install.sh [--dry-run|--monitors]' >&2; exit 2; }
source "$repo/src/installer/monitors.sh"
source "$repo/src/installer/paths.sh"
source "$repo/src/installer/state.sh"
if [[ $dry == --monitors ]]; then rice_monitors_generate; exit 0; fi
first_install=false
if [[ ! -f $HOME/.local/state/rice/installed-revision ]] && {
    [[ ! -f $HOME/.local/state/rice/pre-install/manifest ]] ||
    grep -Eq '^absent[[:space:]]+\.local/share/rice/source$' "$HOME/.local/state/rice/pre-install/manifest"
}; then
    first_install=true
fi

step() {
    if [[ ${RICE_UPDATE_PROGRESS:-} == 1 ]]; then
        printf 'RICE_PROGRESS_STEP=%s\t%s\n' "$1" "$2" >&2
    fi
    printf '\n\033[1m[%s]\033[0m %s\n' "$1" "$2"
}
plan() { if [[ $dry == --dry-run ]]; then printf '  would %s\n' "$*"; return 0; fi; }

step 0 'Checking and compiling native programs'
plan 'verify runtime and compile both C++ programs before changing any user files'
build_dir=''
if [[ $dry != --dry-run ]]; then
    if [[ $repo == "$HOME/.local/share/rice/source" ]]; then
        echo 'Move the checkout outside ~/.local/share/rice/source before installing.' >&2
        exit 1
    fi
    command -v g++ >/dev/null && command -v pkg-config >/dev/null && \
        pkg-config --exists Qt6Core Qt6DBus Qt6Concurrent || {
        echo 'Missing C++/Qt 6 build dependencies. Run ./Installer --deps.' >&2; exit 1;
    }
    command -v quickshell >/dev/null && command -v lua >/dev/null && \
        python3 -c 'import gi; gi.require_version("Gtk", "3.0"); gi.require_version("GtkLayerShell", "0.1"); from gi.repository import Gtk, GtkLayerShell' || {
        echo 'Missing QuickShell, Lua, or GTK panel dependencies. Run ./Installer --deps.' >&2; exit 1;
    }
    build_dir=$(mktemp -d "${TMPDIR:-/tmp}/rice-build.XXXXXXXX")
    trap '[[ -z $build_dir ]] || rm -rf -- "$build_dir"' EXIT
    cxx_flags=$(pkg-config --cflags Qt6Core Qt6DBus Qt6Concurrent)
    cxx_libs=$(pkg-config --libs Qt6Core Qt6DBus Qt6Concurrent)
    read -r -a cxx_include <<< "$cxx_flags"
    read -r -a cxx_link <<< "$cxx_libs"
    for name in rice-actions rice-status; do
        printf 'Compiling %s\n' "$name"
        g++ -std=c++17 -O2 -fPIC "${cxx_include[@]}" "$repo/src/native/$name.cpp" \
            -o "$build_dir/$name" "${cxx_link[@]}"
    done
    if [[ -x /usr/lib/qt6/bin/qmlformat ]]; then
        /usr/lib/qt6/bin/qmlformat "$repo/src/quickshell/shell.qml" >/dev/null
        /usr/lib/qt6/bin/qmlformat "$repo/src/quickshell/SettingsPanel.qml" >/dev/null
    fi
    rice_backup_originals
    mapfile -t managed_paths < <(rice_managed_paths | sort -u)
    rice_backup_added_paths "${managed_paths[@]}"
fi

step 1 'Source and private settings'
plan 'link this repository as ~/.local/share/rice/source'
if [[ $dry != --dry-run ]]; then
    mkdir -p "$HOME/.local/share/rice" "$HOME/.config/rice" "$HOME/.local/state/rice"
    source_target="$HOME/.local/share/rice/source"
    if [[ -d $source_target && ! -L $source_target ]]; then
        if [[ $repo == "$source_target" ]]; then
            echo 'Move the checkout outside ~/.local/share/rice/source before installing.' >&2
            exit 1
        fi
        mv -- "$source_target" "$HOME/.local/state/rice/pre-install/source-directory"
    fi
    ln -sfnT "$repo" "$source_target"
    for name in WiFi Bluetooth Media; do
        if [[ ! -e $HOME/.config/rice/${name}-Options.json ]]; then
            install -m 600 "$repo/${name}-Options.example.json" "$HOME/.config/rice/${name}-Options.json"
        fi
    done
    if [[ ! -e $HOME/.config/rice/settings.json ]]; then
        "$repo/src/bin/rice-clock" set 24h >/dev/null
    fi
    if [[ -n ${RICE_CLOCK:-} ]]; then "$repo/src/bin/rice-clock" set "$RICE_CLOCK" >/dev/null; fi
    if [[ -n ${RICE_DESKTOP_SPOTIFY:-} ]]; then
        "$repo/src/bin/rice-media" set desktop_spotify "$([[ $RICE_DESKTOP_SPOTIFY == yes ]] && printf on || printf off)"
    fi
    if [[ -n ${RICE_BROWSER_MEDIA:-} ]]; then
        "$repo/src/bin/rice-media" set browser_media "$([[ $RICE_BROWSER_MEDIA == yes ]] && printf on || printf off)"
    fi
    printf '{"enabled": true}\n' > "$HOME/.config/rice/telemetry.json"
    chmod 600 "$HOME/.config/rice/telemetry.json"
    for file in private.json.enc display-layout.tsv; do
        if [[ -f $repo/data/$file && ! -e $HOME/.config/rice/$file ]]; then
            install -m 600 "$repo/data/$file" "$HOME/.config/rice/$file"
        fi
    done
    rice_monitors_generate
    if [[ ${RICE_SCALE:-keep} != keep ]]; then
        primary=$(cut -f1 "$HOME/.config/rice/display-device.tsv" 2>/dev/null || true)
        if [[ $primary =~ ^[a-zA-Z0-9_.-]+$ ]]; then
            printf '%s\t%s\n' "$primary" "$RICE_SCALE" > "$HOME/.config/rice/display-device.tsv"
            rice_monitors_generate
            [[ -z ${WAYLAND_DISPLAY:-} ]] || hyprctl reload >/dev/null
        else echo 'No active monitor found; display scale was not changed.' >&2; fi
    fi
fi

step 2 'Programs and config generation'
plan 'copy curated helpers to ~/.local/bin and ~/.local/lib/rice'
plan 'compile C++ status and action handlers and link direct action commands'
plan 'generate Kitty, Rofi, Hyprland companions and other configs from Lua'
if [[ $dry != --dry-run ]]; then
    mkdir -p "$HOME/.local/bin" "$HOME/.local/lib/rice" \
             "$HOME/.config/systemd/user" "$HOME/.config/hypr" \
             "$HOME/.config/fastfetch" "$HOME/.config/kitty" "$HOME/.config/mako" \
             "$HOME/.config/cava" "$HOME/.config/rofi"
    find "$repo/src/bin" -maxdepth 1 -type f -exec cp -a -t "$HOME/.local/bin" {} +
    find "$repo/src/lib/rice" -maxdepth 1 -type f -exec cp -a -t "$HOME/.local/lib/rice" {} +
    mkdir -p "$HOME/.local/lib/rice/actions"
    find "$repo/src/actions" -maxdepth 1 -type f -name '*.exec' -exec cp -a -t "$HOME/.local/lib/rice/actions" {} +
    for name in rice-actions rice-status; do
        cp -- "$build_dir/$name" "$HOME/.local/bin/$name.new"
        chmod 755 "$HOME/.local/bin/$name.new"
        mv "$HOME/.local/bin/$name.new" "$HOME/.local/bin/$name"
    done
    for name in "${RICE_ACTIONS[@]}"; do ln -sfn rice-actions "$HOME/.local/bin/$name"; done
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
    if [[ -n ${WAYLAND_DISPLAY:-} ]]; then
        systemctl --user restart rice-controls.service
        sleep 0.3
        if ! systemctl --user is-active --quiet rice-controls.service; then
            echo 'GTK controls failed to start; check journalctl --user -u rice-controls -b.' >&2
            exit 1
        fi
    fi
    systemctl --user restart rice-hotspot.service
    if [[ -n ${WAYLAND_DISPLAY:-} ]]; then
        # Handoff only after the new bar has been built and its source deployed.
        rice_stop_old_waybar
        systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP HYPRLAND_INSTANCE_SIGNATURE DISPLAY
        systemctl --user restart rice-bar.service
        sleep 0.5
        if ! systemctl --user is-active --quiet rice-bar.service || \
           ! quickshell ipc --path "$HOME/.local/share/rice/source/src/quickshell/shell.qml" show >/dev/null 2>&1; then
            systemctl --user stop rice-bar.service || true
            rice_restore_old_waybar handoff
            echo 'New QuickShell bar failed to load; restored the previous Waybar.' >&2
            exit 1
        fi
    fi
    if revision=$(git -C "$repo" rev-parse --verify HEAD 2>/dev/null); then
        printf '%s\n' "$revision" > "$HOME/.local/state/rice/installed-revision.tmp"
        mv "$HOME/.local/state/rice/installed-revision.tmp" "$HOME/.local/state/rice/installed-revision"
    fi
    if [[ $first_install == true ]]; then
        : > "$HOME/.local/state/rice/tutorial-pending"
        printf 'RICE_TUTORIAL_READY=1\n'
    fi
fi
step 5 'Done · Hyprland Lua and QuickShell bar ready'
if [[ $dry != --dry-run && $first_install == true && -n ${WAYLAND_DISPLAY:-} &&
      ${RICE_UPDATE_PROGRESS:-0} != 1 ]]; then
    "$HOME/.local/bin/rice-tutorial" --first-run >/dev/null 2>&1 &
fi
