-- Edit this source, then run: lua ~/config/apply.lua
return {
    ["battery"] = {
        ["bat"] = "BAT0",
        ["format"] = "{icon}  {capacity}%",
        ["format-charging"] = "  {capacity}%",
        ["format-icons"] = {"", "", "", "", ""},
        ["format-plugged"] = "  {capacity}%",
        ["interval"] = 30,
        ["states"] = {
            ["critical"] = 10,
            ["warning"] = 20
        },
        ["tooltip-format"] = "Battery · {capacity}%\n{time}"
    },
    ["bluetooth"] = {
        ["format"] = "",
        ["format-connected"] = "  {device_alias}",
        ["format-disabled"] = "󰂲",
        ["format-no-controller"] = "",
        ["format-off"] = "󰂲",
        ["max-length"] = 18,
        ["on-click"] = "~/.local/bin/desktop-menu bluetooth",
        ["on-click-right"] = "~/.local/bin/desktop-menu bluetooth",
        ["tooltip-format-connected"] = "{device_enumerate}",
        ["tooltip-format-enumerate-connected"] = "{device_alias}"
    },
    ["clock"] = {
        ["format"] = "  {:%H:%M:%S}",
        ["interval"] = 1,
        ["tooltip-format"] = "{:%A, %d %B %Y}"
    },
    ["custom/audio"] = {
        ["exec"] = "python3 -u ~/.local/lib/rice/audio_watch.py",
        ["exec-on-event"] = false,
        ["on-click"] = "~/.local/bin/desktop-menu audio mute",
        ["on-click-middle"] = "~/.local/bin/desktop-menu audio boost",
        ["on-click-right"] = "~/.local/bin/desktop-menu audio",
        ["on-scroll-down"] = "~/.local/bin/desktop-menu audio down",
        ["on-scroll-up"] = "~/.local/bin/desktop-menu audio up",
        ["return-type"] = "json",
        ["smooth-scrolling-threshold"] = 1
    },
    ["custom/control"] = {
        ["format"] = "",
        ["on-click"] = "~/.local/bin/control-menu",
        ["tooltip-format"] = "Settings · brightness, sound, connectivity"
    },
    ["custom/display"] = {
        ["exec"] = "python3 ~/.local/lib/rice/display.py status",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = 2,
        ["on-click"] = "~/.local/bin/desktop-panel display",
        ["return-type"] = "json"
    },
    ["custom/files"] = {
        ["format"] = "",
        ["on-click"] = "thunar",
        ["tooltip-format"] = "Files"
    },
    ["custom/network"] = {
        ["exec"] = "~/.local/bin/desktop-menu network-status",
        ["interval"] = 2,
        ["on-click-right"] = "~/.local/bin/desktop-menu network",
        ["return-type"] = "json"
    },
    ["custom/power"] = {
        ["format"] = "",
        ["on-click"] = "~/.local/bin/power-menu",
        ["tooltip-format"] = "Power / session"
    },
    ["custom/spotify"] = {
        ["exec"] = "~/.local/bin/waybar-spotify",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = 2,
        ["on-click"] = "playerctl --player=spotify play-pause",
        ["on-click-right"] = "~/.local/bin/desktop-window spotify",
        ["on-scroll-down"] = "playerctl --player=spotify volume 0.05-",
        ["on-scroll-up"] = "playerctl --player=spotify volume 0.05+",
        ["return-type"] = "json"
    },
    ["custom/spotify-next"] = {
        ["exec"] = "printf 'next'",
        ["exec-if"] = "playerctl --player=spotify status >/dev/null 2>&1",
        ["format"] = "󰒭",
        ["interval"] = 2,
        ["on-click"] = "playerctl --player=spotify next",
        ["tooltip-format"] = "Next track"
    },
    ["custom/spotify-prev"] = {
        ["exec"] = "printf 'previous'",
        ["exec-if"] = "playerctl --player=spotify status >/dev/null 2>&1",
        ["format"] = "󰒮",
        ["interval"] = 2,
        ["on-click"] = "playerctl --player=spotify previous",
        ["tooltip-format"] = "Previous track"
    },
    ["custom/spotify-repeat"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --repeat",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = 1,
        ["on-click"] = "~/.local/bin/waybar-spotify --cycle-repeat",
        ["return-type"] = "json"
    },
    ["custom/spotify-shuffle"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --shuffle",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = 1,
        ["on-click"] = "~/.local/bin/waybar-spotify --toggle-shuffle",
        ["on-click-right"] = "~/.local/bin/desktop-window spotify",
        ["return-type"] = "json"
    },
    ["custom/terminal"] = {
        ["format"] = "",
        ["on-click"] = "kitty",
        ["tooltip-format"] = "Kitty"
    },
    ["custom/vscode"] = {
        ["format"] = "󰨞",
        ["on-click"] = "~/.local/bin/vscode-menu",
        ["on-click-middle"] = "~/.local/bin/vscode-menu folder",
        ["on-click-right"] = "~/.local/bin/vscode-menu focus",
        ["tooltip-format"] = "VS Code\nClick: project menu\nRight-click: open / focus\nMiddle-click: open folder"
    },
    ["height"] = 30,
    ["hyprland/workspaces"] = {
        ["format"] = "{id}",
        ["on-click"] = "activate",
        ["persistent-workspaces"] = {
            ["1"] = {},
            ["2"] = {},
            ["3"] = {},
            ["4"] = {},
            ["5"] = {}
        },
        ["sort-by-number"] = true
    },
    ["image#spotify-cover"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --cover",
        ["interval"] = 2,
        ["on-click"] = "~/.local/bin/desktop-window spotify",
        ["size"] = 24,
        ["tooltip"] = true
    },
    ["layer"] = "top",
    ["margin-left"] = 8,
    ["margin-right"] = 8,
    ["margin-top"] = 5,
    ["modules-center"] = {"hyprland/workspaces"},
    ["modules-left"] = {"clock", "custom/audio", "image#spotify-cover", "custom/spotify-shuffle", "custom/spotify-prev", "custom/spotify", "custom/spotify-next", "custom/spotify-repeat"},
    ["modules-right"] = {"custom/vscode", "custom/terminal", "custom/files", "custom/display", "bluetooth", "custom/network", "battery", "custom/control", "custom/power"},
    ["position"] = "top",
    ["spacing"] = 0
}
