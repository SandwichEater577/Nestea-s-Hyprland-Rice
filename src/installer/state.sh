#!/usr/bin/env bash
# Preserve each pre-rice file once. A later update must not replace the backup.
rice_backup_originals() {
    local backup="$HOME/.local/state/rice/pre-install" relative source
    [[ -e $backup/manifest ]] && return 0
    [[ ! -e $backup ]] || { echo "Incomplete backup at $backup; move it aside before installing." >&2; return 1; }
    mkdir -p "$(dirname "$backup")"
    local staging="$backup.tmp.$$"
    mkdir -p "$staging/files"
    while IFS= read -r relative; do
        source="$HOME/$relative"
        if [[ -e $source || -L $source ]]; then
            mkdir -p "$staging/files/$(dirname "$relative")"
            cp -a -- "$source" "$staging/files/$relative"
            printf 'present\t%s\n' "$relative" >> "$staging/manifest"
        else
            printf 'absent\t%s\n' "$relative" >> "$staging/manifest"
        fi
    done < <(rice_managed_paths | sort -u)
    if systemctl --user is-active --quiet waybar.service; then
        printf 'service\n' > "$staging/old-waybar"
    elif pgrep -u "$(id -u)" -x waybar >/dev/null; then
        printf 'process\n' > "$staging/old-waybar"
    else
        printf 'none\n' > "$staging/old-waybar"
    fi
    systemctl --user is-enabled --quiet waybar.service &&
        printf 'enabled\n' > "$staging/old-waybar-enabled" ||
        printf 'disabled\n' > "$staging/old-waybar-enabled"
    local unit enabled active
    for unit in rice-bar rice-controls rice-hotspot rice-update-watch rice-update; do
        enabled=$(systemctl --user is-enabled "$unit.service" 2>/dev/null || true)
        active=$(systemctl --user is-active "$unit.service" 2>/dev/null || true)
        printf '%s\t%s\t%s\n' "$unit" "$enabled" "$active" >> "$staging/services.tsv"
    done
    mv -- "$staging" "$backup"
}

rice_restore_originals() {
    local backup="$HOME/.local/state/rice/pre-install" kind relative target
    [[ -f $backup/manifest ]] || {
        echo 'No pre-install backup exists; refusing to remove unknown user files.' >&2
        return 1
    }
    while IFS=$'\t' read -r kind relative; do
        target="$HOME/$relative"
        [[ $relative != /* && $relative != *'..'* ]] || return 1
        if [[ -d $target && ! -L $target ]]; then
            rm -r -- "$target"
        else
            rm -f -- "$target"
        fi
        if [[ $kind == present ]]; then
            mkdir -p "$(dirname "$target")"
            cp -a -- "$backup/files/$relative" "$target"
        fi
    done < "$backup/manifest"
    [[ ! -d $backup/source-directory ]] || rm -rf -- "$backup/source-directory"
}

rice_stop_old_waybar() {
    local mode=none
    if systemctl --user is-active --quiet waybar.service; then mode=service
    elif pgrep -u "$(id -u)" -x waybar >/dev/null; then mode=process; fi
    printf '%s\n' "$mode" > "$HOME/.local/state/rice/handoff-waybar"
    systemctl --user disable --now waybar.service >/dev/null 2>&1 || true
    pkill -u "$(id -u)" -x waybar >/dev/null 2>&1 || true
    for _ in 1 2 3 4 5; do
        pgrep -u "$(id -u)" -x waybar >/dev/null || break
        sleep 0.1
    done
}

rice_restore_old_waybar() {
    local backup="$HOME/.local/state/rice/pre-install" mode file="$HOME/.local/state/rice/pre-install/old-waybar"
    [[ ${1:-} != handoff ]] || file="$HOME/.local/state/rice/handoff-waybar"
    mode=$(cat "$file" 2>/dev/null || printf none)
    if [[ $(cat "$backup/old-waybar-enabled" 2>/dev/null) == enabled ]]; then
        systemctl --user enable waybar.service >/dev/null 2>&1 || true
    fi
    case $mode in
        service) systemctl --user start waybar.service ;;
        process) if command -v waybar >/dev/null; then nohup waybar >/dev/null 2>&1 & fi ;;
    esac
}

rice_restore_services() {
    local backup="$HOME/.local/state/rice/pre-install" unit enabled active
    [[ -f $backup/services.tsv ]] || return 0
    [[ $(cat "$backup/old-waybar" 2>/dev/null) == none ]] || return 0
    while IFS=$'\t' read -r unit enabled active; do
        if [[ $enabled == enabled ]]; then
            systemctl --user enable "$unit.service" >/dev/null 2>&1 || true
        fi
        if [[ $active == active && $unit != rice-update ]]; then
            systemctl --user start "$unit.service" >/dev/null 2>&1 || true
        fi
    done < "$backup/services.tsv"
}
