return {{
        ["source"] = "waybar.lua",
        ["target"] = "waybar/config.jsonc",
        ["format"] = "json",
    }, {
        ["source"] = "fastfetch.lua",
        ["target"] = "fastfetch/config.jsonc",
        ["format"] = "json",
    }, {
        ["source"] = "kitty.lua",
        ["target"] = "kitty/kitty.conf",
        ["format"] = "space",
    }, {
        ["source"] = "mako.lua",
        ["target"] = "mako/config",
        ["format"] = "compact-equals",
    }, {
        ["source"] = "cava.lua",
        ["target"] = "cava/config",
        ["format"] = "equals",
    }, {
        ["source"] = "hypridle.lua",
        ["target"] = "hypr/hypridle.conf",
        ["format"] = "hypr",
    }, {
        ["source"] = "hyprlock.lua",
        ["target"] = "hypr/hyprlock.conf",
        ["format"] = "hypr",
    }, {
        ["source"] = "hyprpaper.lua",
        ["target"] = "hypr/hyprpaper.conf",
        ["format"] = "hypr",
    }, {
        ["source"] = "rofi.lua",
        ["target"] = "rofi/config.rasi",
        ["format"] = "css",
    }, {
        ["source"] = "waybar-style.lua",
        ["target"] = "waybar/style.css",
        ["format"] = "css",
    }}
