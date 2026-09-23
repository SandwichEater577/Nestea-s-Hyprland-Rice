-- Edit this Lua source, then run: lua ~/config/src/config/apply.lua
return {{
        ["section"] = "general",
        ["entries"] = {{
                ["key"] = "hide_cursor",
                ["value"] = "true",
            }},
    }, {
        ["section"] = "background",
        ["entries"] = {{
                ["key"] = "monitor",
                ["value"] = "",
            }, {
                ["key"] = "color",
                ["value"] = "rgba(181818ff)",
            }},
    }, {
        ["section"] = "input-field",
        ["entries"] = {{
                ["key"] = "monitor",
                ["value"] = "",
            }, {
                ["key"] = "size",
                ["value"] = "280, 48",
            }, {
                ["key"] = "outline_thickness",
                ["value"] = "1",
            }, {
                ["key"] = "outer_color",
                ["value"] = "rgba(666666ff)",
            }, {
                ["key"] = "inner_color",
                ["value"] = "rgba(242424ff)",
            }, {
                ["key"] = "font_color",
                ["value"] = "rgba(e6e6e6ff)",
            }, {
                ["key"] = "font_family",
                ["value"] = "JetBrainsMono Nerd Font",
            }, {
                ["key"] = "placeholder_text",
                ["value"] = "Password",
            }, {
                ["key"] = "rounding",
                ["value"] = "8",
            }, {
                ["key"] = "position",
                ["value"] = "0, -60",
            }, {
                ["key"] = "halign",
                ["value"] = "center",
            }, {
                ["key"] = "valign",
                ["value"] = "center",
            }},
    }, {
        ["section"] = "label",
        ["entries"] = {{
                ["key"] = "monitor",
                ["value"] = "",
            }, {
                ["key"] = "text",
                ["value"] = "$TIME",
            }, {
                ["key"] = "font_size",
                ["value"] = "44",
            }, {
                ["key"] = "font_family",
                ["value"] = "JetBrainsMono Nerd Font",
            }, {
                ["key"] = "color",
                ["value"] = "rgba(e6e6e6ff)",
            }, {
                ["key"] = "position",
                ["value"] = "0, 45",
            }, {
                ["key"] = "halign",
                ["value"] = "center",
            }, {
                ["key"] = "valign",
                ["value"] = "center",
            }},
    }}
