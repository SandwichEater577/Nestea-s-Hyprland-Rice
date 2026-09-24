#!/usr/bin/env bash
# Names deployed by the rice. Keep this list shared by install and uninstall.
RICE_ACTIONS=(rice-audio-up rice-audio-down rice-audio-mute rice-audio-boost
    rice-media-toggle rice-media-next rice-media-previous rice-media-up
    rice-media-down rice-media-shuffle rice-media-repeat
    rice-brightness-up rice-brightness-down rice-brightness-set rice-brightness-current
    rice-profile-saver rice-profile-balanced rice-profile-fast rice-profile-current
    rice-clock-12 rice-clock-24 rice-spotify-on rice-spotify-off
    rice-browser-on rice-browser-off
    rice-show-settings rice-show-audio rice-show-network rice-show-bluetooth
    rice-show-display rice-show-media rice-show-power rice-show-code rice-show-updates
    rice-terminal rice-files rice-wallpaper-next rice-screen-full rice-screen-region
    rice-lock rice-clipboard rice-vscode-menu rice-vscode-folder rice-vscode-focus
    rice-workspace-focus rice-show-update rice-update-ignore rice-update-check
    rice-system-monitor rice-desktop-config rice-share-idea)

rice_managed_paths() {
    local name target
    printf '%s\n' \
        .local/share/rice/source \
        .config/rice/WiFi-Options.json .config/rice/Bluetooth-Options.json \
        .config/rice/Media-Options.json .config/rice/settings.json \
        .config/rice/telemetry.json \
        .config/rice/display-device.tsv .config/rice/display-layout.tsv \
        .config/rice/private.json.enc .config/rice/monitors.conf \
        .config/hypr/hyprland.lua .config/hypr/hyprland.conf \
        .local/state/rice/installed-revision .local/state/rice/palette.json
    for name in rice-bar rice-controls rice-hotspot rice-update-watch rice-update; do
        printf '.config/systemd/user/%s.service\n' "$name"
    done
    for name in rice-actions rice-status "${RICE_ACTIONS[@]}"; do
        printf '.local/bin/%s\n' "$name"
    done
    for name in build-rice-bar start-waybar ui-backend waybar-spotify rice-media-watch; do
        printf '.local/bin/%s\n' "$name"
    done
    while IFS= read -r name; do printf '.local/bin/%s\n' "$name"; done < <(
        find "$repo/src/bin" -maxdepth 1 -type f -printf '%f\n' | sort)
    while IFS= read -r name; do printf '.local/lib/rice/%s\n' "$name"; done < <(
        find "$repo/src/lib/rice" -maxdepth 1 -type f -printf '%f\n' | sort)
    while IFS= read -r target; do printf '.config/%s\n' "$target"; done < <(
        sed -n 's/.*\["target"\] = "\([^"]*\)".*/\1/p' "$repo/src/config/manifest.lua")
}
