-- Edit this source, then run: lua ~/config/src/config/apply.lua
local bar = {
    ["battery"] = {
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
        ["format-connected"] = "",
        ["format-disabled"] = "󰂲",
        ["format-no-controller"] = "",
        ["format-off"] = "󰂲",
        ["max-length"] = 18,
        ["on-click"] = "~/.local/bin/desktop-menu bluetooth",
        ["on-click-right"] = "~/.local/bin/desktop-menu bluetooth",
        ["tooltip-format-connected"] = "{device_enumerate}",
        ["tooltip-format-enumerate-connected"] = "{device_alias}"
    },
    ["custom/clock"] = {
        ["exec"] = "~/.local/bin/rice-clock --watch",
        ["return-type"] = "json",
        ["format"] = "{}"
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
        ["on-click"] = "~/.local/bin/desktop-menu network",
        ["on-click-right"] = "~/.local/bin/desktop-menu network",
        ["return-type"] = "json"
    },
    ["custom/power"] = {
        ["format"] = "",
        ["on-click"] = "~/.local/bin/power-click",
        ["tooltip-format"] = "Power / session\nClick: power menu · Triple-click: shut down"
    },
    ["custom/spotify"] = {
        ["exec"] = "~/.local/bin/waybar-spotify",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = "once",
        ["signal"] = 10,
        ["on-click"] = "~/.local/bin/rice-media toggle",
        ["on-click-right"] = "~/.local/bin/desktop-panel media",
        ["on-scroll-down"] = "~/.local/bin/rice-media down",
        ["on-scroll-up"] = "~/.local/bin/rice-media up",
        ["return-type"] = "json"
    },
    ["custom/spotify-next"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --next",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = "once",
        ["signal"] = 10,
        ["return-type"] = "json",
        ["on-click"] = "~/.local/bin/rice-media next",
        ["tooltip-format"] = "Next track"
    },
    ["custom/spotify-prev"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --prev",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = "once",
        ["signal"] = 10,
        ["return-type"] = "json",
        ["on-click"] = "~/.local/bin/rice-media previous",
        ["tooltip-format"] = "Previous track"
    },
    ["custom/spotify-repeat"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --repeat",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = "once",
        ["signal"] = 10,
        ["on-click"] = "~/.local/bin/waybar-spotify --cycle-repeat",
        ["return-type"] = "json"
    },
    ["custom/spotify-shuffle"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --shuffle",
        ["format"] = "{}",
        ["hide-empty-text"] = true,
        ["interval"] = "once",
        ["signal"] = 10,
        ["on-click"] = "~/.local/bin/waybar-spotify --toggle-shuffle",
        ["on-click-right"] = "~/.local/bin/desktop-panel media",
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
    -- Tall enough for the doubled media glyphs; matches the 40px cpp/quickshell bars.
    ["height"] = 40,
    ["image#spotify-cover"] = {
        ["exec"] = "~/.local/bin/waybar-spotify --cover",
        ["interval"] = 2,
        ["signal"] = 10,
        ["on-click"] = "~/.local/bin/desktop-panel media",
        ["size"] = 24,
        ["tooltip"] = true
    },
    ["layer"] = "top",
    ["margin-left"] = 8,
    ["margin-right"] = 8,
    ["margin-top"] = 5,
    ["on-sigusr2"] = "noop",
    ["modules-center"] = {},
    ["modules-left"] = {"custom/clock", "custom/audio", "image#spotify-cover", "custom/spotify-shuffle", "custom/spotify-prev", "custom/spotify", "custom/spotify-next", "custom/spotify-repeat"},
    ["modules-right"] = {"custom/vscode", "custom/terminal", "custom/files", "custom/display", "bluetooth", "custom/network", "battery", "custom/control", "custom/power"},
    ["position"] = "top",
    ["reload_style_on_change"] = true,
    ["spacing"] = 0
}
for n = 1, 9 do
    table.insert(bar["modules-center"], "custom/workspace-" .. n)
    bar["custom/workspace-" .. n] = {
        ["exec"] = "~/.local/bin/rice-workspace --watch " .. n,
        ["exec-on-event"] = false,
        ["format"] = "{}",
        ["hide-empty-text"] = n > 5,
        ["on-click"] = "~/.local/bin/rice-workspace " .. n,
        ["return-type"] = "json",
        ["tooltip"] = false,
    }
end
return bar
