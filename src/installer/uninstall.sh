#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source "$repo/src/installer/paths.sh"
source "$repo/src/installer/state.sh"

[[ -f $HOME/.local/state/rice/pre-install/manifest ]] || {
    echo 'No pre-install snapshot is available. Uninstall cannot safely restore this desktop.' >&2
    exit 1
}
echo 'Stopping rice services'
for unit in rice-bar rice-controls rice-hotspot rice-update-watch rice-update; do
    systemctl --user disable --now "$unit.service" >/dev/null 2>&1 || true
done
echo 'Restoring files from before the first rice installation'
rice_restore_originals
systemctl --user daemon-reload
rice_restore_services
if [[ -n ${WAYLAND_DISPLAY:-} ]]; then
    hyprctl reload >/dev/null 2>&1 || true
    rice_restore_old_waybar
fi
echo 'Uninstalled the rice and restored the saved desktop files.'
