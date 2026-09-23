-- Personal monochrome configuration.
return {
    ["logo"] = {
        ["type"] = "small",
        ["color"] = {
            ["1"] = "white",
            ["2"] = "white",
            ["3"] = "white"
        },
        ["padding"] = {
            ["right"] = 4,
            ["top"] = 1
        }
    },
    ["display"] = {
        ["separator"] = "  ",
        ["color"] = {
            ["keys"] = "90",
            ["title"] = "white",
            ["output"] = "white",
            ["separator"] = "90"
        },
        ["key"] = {
            ["width"] = 10
        }
    },
    ["modules"] = {
        {
            ["type"] = "title",
            ["format"] = "{user-name}  /  {host-name}"
        },
        "break",
        {
            ["type"] = "os",
            ["key"] = "System"
        },
        {
            ["type"] = "host",
            ["key"] = "Machine"
        },
        {
            ["type"] = "kernel",
            ["key"] = "Kernel"
        },
        {
            ["type"] = "wm",
            ["key"] = "Desktop"
        },
        {
            ["type"] = "uptime",
            ["key"] = "Uptime"
        },
        "break",
        {
            ["type"] = "cpu",
            ["key"] = "CPU"
        },
        {
            ["type"] = "memory",
            ["key"] = "Memory"
        },
        {
            ["type"] = "disk",
            ["key"] = "Storage",
            ["folders"] = "/"
        },
        {
            ["type"] = "battery",
            ["key"] = "Battery"
        },
        "break"
    }
}
