-- Edit this Lua source, then run: lua ~/config/apply.lua
return {{
        ["section"] = "general",
        ["entries"] = {{
                ["key"] = "lock_cmd",
                ["value"] = "~/.local/bin/lock-screen",
            }, {
                ["key"] = "before_sleep_cmd",
                ["value"] = "loginctl lock-session",
            }, {
                ["key"] = "after_sleep_cmd",
                ["value"] = "hyprctl dispatch dpms on",
            }},
    }, {
        ["section"] = "listener",
        ["entries"] = {{
                ["key"] = "timeout",
                ["value"] = "600",
            }, {
                ["key"] = "on-timeout",
                ["value"] = "loginctl lock-session",
            }},
    }, {
        ["section"] = "listener",
        ["entries"] = {{
                ["key"] = "timeout",
                ["value"] = "900",
            }, {
                ["key"] = "on-timeout",
                ["value"] = "hyprctl dispatch dpms off",
            }, {
                ["key"] = "on-resume",
                ["value"] = "hyprctl dispatch dpms on",
            }},
    }}
