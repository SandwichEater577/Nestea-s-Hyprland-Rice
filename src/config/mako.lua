-- Edit this Lua source, then run: lua ~/config/src/config/apply.lua
return {{
        ["key"] = "font",
        ["value"] = "JetBrainsMono Nerd Font 10",
    }, {
        ["key"] = "background-color",
        ["value"] = "#202020f5",
    }, {
        ["key"] = "text-color",
        ["value"] = "#e6e6e6ff",
    }, {
        ["key"] = "border-color",
        ["value"] = "#494949ff",
    }, {
        ["key"] = "border-size",
        ["value"] = "1",
    }, {
        ["key"] = "border-radius",
        ["value"] = "8",
    }, {
        ["key"] = "padding",
        ["value"] = "12",
    }, {
        ["key"] = "width",
        ["value"] = "310",
    }, {
        ["key"] = "height",
        ["value"] = "140",
    }, {
        ["key"] = "margin",
        ["value"] = "10",
    }, {
        ["key"] = "default-timeout",
        ["value"] = "5000",
    }, {
        ["key"] = "max-visible",
        ["value"] = "3",
    }, {
        ["key"] = "anchor",
        ["value"] = "top-right",
    }, {
        ["key"] = "text-alignment",
        ["value"] = "right",
    }, {
        -- Summary line right-aligned so the ✕ sits next to the border, inside
        -- the notification. mako 1.11 cannot draw a real close widget, so the
        -- ✕ is part of the text and a left click anywhere dismisses.
        ["key"] = "format",
        ["value"] = "<b>%s</b> ✕\\n%b",
    }, {
        ["key"] = "on-button-left",
        ["value"] = "dismiss",
    }, {
        ["section"] = "urgency=critical",
    }, {
        ["key"] = "default-timeout",
        ["value"] = "0",
    }, {
        ["key"] = "border-color",
        ["value"] = "#b0b0b0ff",
    }}
