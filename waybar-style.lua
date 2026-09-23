-- Native monochrome theme. Regenerate with lua ~/config/apply.lua.
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
        { key = "color", value = "#e4e4e4" },
    } },
    { selector = ".modules-left, .modules-center, .modules-right", entries = {
        { key = "background", value = "rgba(22,22,22,0.97)" },
        { key = "border", value = "1px solid #3b3b3b" },
        { key = "border-radius", value = "10px" },
        { key = "padding", value = "0 5px" },
    } },
    { selector = "#clock, #custom-audio, #bluetooth, #custom-network, #battery, #custom-terminal, #custom-control, #custom-files, #custom-power, #custom-vscode", entries = {
        { key = "padding", value = "0 7px" },
        { key = "margin", value = "0" },
        { key = "background", value = "transparent" },
    } },
    { selector = "#custom-spotify, #custom-spotify-prev, #custom-spotify-next, #custom-spotify-shuffle, #custom-spotify-repeat", entries = {
        { key = "font-size", value = "14px" },
        { key = "min-width", value = "15px" },
        { key = "padding", value = "0 5px" },
        { key = "background", value = "transparent" },
        { key = "color", value = "#d8d8d8" },
    } },
    { selector = "#custom-spotify-shuffle.enabled, #custom-spotify-repeat.enabled", entries = {
        { key = "border-bottom", value = "1px solid #a8a8a8" },
    } },
    { selector = "#workspaces button", entries = {
        { key = "color", value = "#a3a3a3" },
        { key = "background", value = "transparent" },
        { key = "padding", value = "0 9px" },
        { key = "margin", value = "3px 2px" },
        { key = "border-radius", value = "6px" },
    } },
    { selector = "#workspaces button.active, #workspaces button:hover, #workspaces button.urgent", entries = {
        { key = "background", value = "#dedede" },
        { key = "color", value = "#181818" },
    } },
    { selector = "#custom-audio:hover, #custom-control:hover, #custom-power:hover, #custom-files:hover, #custom-terminal:hover, #custom-vscode:hover, #bluetooth:hover, #custom-network:hover", entries = {
        { key = "background", value = "#303030" },
        { key = "color", value = "#ffffff" },
        { key = "border-radius", value = "6px" },
    } },
    { selector = "#battery.warning, #battery.critical", entries = {
        { key = "border-bottom", value = "2px solid #ffffff" },
    } },
    { selector = "tooltip", entries = {
        { key = "background", value = "#202020" },
        { key = "color", value = "#ffffff" },
        { key = "border", value = "1px solid #424242" },
        { key = "border-radius", value = "10px" },
    } },
    { selector = "tooltip label", entries = {
        { key = "color", value = "#dedede" },
        { key = "padding", value = "9px" },
    } },
    { selector = "#custom-spotify-shuffle.disabled, #custom-spotify-repeat.disabled", entries = {
        { key = "color", value = "#797979" },
    } },
}
