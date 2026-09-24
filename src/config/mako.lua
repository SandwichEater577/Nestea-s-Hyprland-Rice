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
        -- Mako cannot style a separate close widget. This circled X has a
        -- visible round outline; a left click anywhere dismisses.
        ["key"] = "format",
        ["value"] = '<b>%s</b>  <span size="large">ⓧ</span>\\n%b',
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
