-- Native monochrome theme. Regenerate with lua ~/config/src/config/apply.lua.
return {
    { selector = "*", entries = {
        { key = "font-family", value = "\"Adwaita Sans\", \"JetBrainsMono Nerd Font\"" },
        { key = "font-size", value = "12px" },
        { key = "min-height", value = "0" },
        { key = "border", value = "none" },
        { key = "border-radius", value = "0" },
        { key = "text-shadow", value = "none" },
        { key = "box-shadow", value = "none" },
    } },
    { selector = "window#waybar", entries = {
        { key = "background", value = "transparent" },
        { key = "color", value = "@rice_foreground" },
        { key = "transition", value = "color 200ms ease-out" },
    } },
    { selector = ".modules-left, .modules-center, .modules-right", entries = {
        { key = "background", value = "@rice_background" },
        { key = "border", value = "1px solid @rice_border" },
        { key = "border-radius", value = "10px" },
        { key = "padding", value = "0 5px" },
        { key = "transition", value = "background-color 200ms ease-out, border-color 200ms ease-out" },
    } },
    { selector = "#custom-clock, #custom-audio, #bluetooth, #custom-network, #battery, #custom-terminal, #custom-control, #custom-files, #custom-display, #custom-power, #custom-vscode", entries = {
        { key = "padding", value = "0 7px" },
        { key = "margin", value = "0" },
        { key = "background", value = "transparent" },
    } },
    { selector = "#custom-spotify, #custom-spotify-prev, #custom-spotify-next, #custom-spotify-shuffle, #custom-spotify-repeat", entries = {
        { key = "font-size", value = "28px" },
        { key = "min-width", value = "15px" },
        { key = "padding", value = "0 5px" },
        { key = "background", value = "transparent" },
        { key = "color", value = "@rice_foreground" },
    } },
    { selector = "#custom-spotify-shuffle.enabled, #custom-spotify-repeat.enabled", entries = {
        { key = "border-bottom", value = "1px solid @rice_accent" },
    } },
    { selector = "#custom-audio.boosted", entries = {
        { key = "border-bottom", value = "2px solid @rice_accent" },
    } },
    { selector = "#custom-workspace-1, #custom-workspace-2, #custom-workspace-3, #custom-workspace-4, #custom-workspace-5", entries = {
        { key = "color", value = "@rice_muted" },
        { key = "background", value = "transparent" },
        { key = "min-width", value = "39px" },
        { key = "min-height", value = "22px" },
        { key = "padding", value = "0" },
        { key = "margin", value = "3px 1px" },
        { key = "border-radius", value = "5px" },
        { key = "transition", value = "background-color 200ms ease-out, color 200ms ease-out" },
    } },
    { selector = "#custom-workspace-1.active, #custom-workspace-2.active, #custom-workspace-3.active, #custom-workspace-4.active, #custom-workspace-5.active, #custom-workspace-1:hover, #custom-workspace-2:hover, #custom-workspace-3:hover, #custom-workspace-4:hover, #custom-workspace-5:hover", entries = {
        { key = "background", value = "@rice_accent" },
        { key = "color", value = "@rice_accent_foreground" },
    } },
    { selector = "#custom-audio:hover, #custom-control:hover, #custom-power:hover, #custom-files:hover, #custom-terminal:hover, #custom-display:hover, #custom-vscode:hover, #bluetooth:hover, #custom-network:hover", entries = {
        { key = "background", value = "@rice_hover" },
        { key = "color", value = "@rice_foreground" },
        { key = "border-radius", value = "6px" },
    } },
    { selector = "#battery.warning, #battery.critical", entries = {
        { key = "border-bottom", value = "2px solid @rice_accent" },
    } },
    { selector = "tooltip", entries = {
        { key = "background", value = "@rice_background" },
        { key = "color", value = "@rice_foreground" },
        { key = "border", value = "1px solid @rice_border" },
        { key = "border-radius", value = "10px" },
    } },
    { selector = "tooltip label", entries = {
        { key = "color", value = "@rice_foreground" },
        { key = "padding", value = "9px" },
    } },
    { selector = "#custom-spotify-shuffle.disabled, #custom-spotify-repeat.disabled", entries = {
        { key = "color", value = "@rice_muted" },
    } },
}
