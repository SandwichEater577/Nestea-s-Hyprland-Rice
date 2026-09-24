#!/usr/bin/env bash
# Shared by the installer and its live display option.
rice_monitors_generate() {
    local dir="$HOME/.config/rice" file="$HOME/.config/rice/display-device.tsv"
    local output='' scale='' name='' layout='' mode='' rule_scale=''
    mkdir -p "$dir"
    if [[ ! -s $file ]] && command -v hyprctl >/dev/null && command -v jq >/dev/null; then
        IFS=$'\t' read -r output scale < <(hyprctl -j monitors 2>/dev/null | jq -r \
            '([.[] | select(.name | test("^(eDP|LVDS|DSI)-"))] + .)[0] | [.name, .scale] | @tsv' 2>/dev/null) || true
        if [[ $output =~ ^[a-zA-Z0-9_.-]+$ && $scale =~ ^[0-9]+([.][0-9]+)?$ ]]; then
            printf '%s\t%s\n' "$output" "$scale" > "$file"
            chmod 600 "$file"
        fi
    fi
    output= scale=
    if [[ -s $file ]]; then IFS=$'\t' read -r output scale < "$file" || true; fi
    {
        if [[ $output =~ ^[a-zA-Z0-9_.-]+$ && $scale =~ ^[0-9]+([.][0-9]+)?$ ]]; then
            printf 'monitor = %s, preferred, auto, %s\n' "$output" "$scale"
            printf 'workspace = 1, monitor:%s, default:true\n' "$output"
        fi
        if [[ -f $dir/display-layout.tsv ]]; then
            while IFS=$'\t' read -r name layout mode rule_scale; do
                [[ $name =~ ^[a-zA-Z0-9_.-]+$ && $mode =~ ^(preferred|[0-9]+x[0-9]+@[0-9.]+)$ && $rule_scale =~ ^[0-9]+([.][0-9]+)?$ ]] || continue
                if [[ $layout == mirror && -n $output ]]; then
                    printf 'monitor = %s, %s, auto, %s, mirror, %s\n' "$name" "$mode" "$rule_scale" "$output"
                elif [[ $layout == extend ]]; then
                    printf 'monitor = %s, %s, auto, %s\n' "$name" "$mode" "$rule_scale"
                fi
            done < "$dir/display-layout.tsv"
        fi
    } > "$dir/monitors.conf"
}
