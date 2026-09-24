-- Monitor names and scale come from per-machine settings created by Installer.
local rice_settings = assert(os.getenv("HOME")) .. "/.config/rice/"
local primary
local primary_file = io.open(rice_settings .. "display-device.tsv", "r")
if primary_file then
    local line = primary_file:read('*l') or ''
    local output, scale = line:match("^([%w_.%-]+)\t([%d%.]+)$")
    scale = tonumber(scale)
    if output and scale and scale >= 0.5 and scale <= 4 then
        primary = output
        hl.monitor({ output=primary, mode="preferred", position="auto", scale=scale })
    end
    primary_file:close()
end
local display_rules = {}
local display_file = io.open(rice_settings .. "display-layout.tsv", "r")
if display_file then
    for line in display_file:lines() do
        local output, layout, mode, scale = line:match("^([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)$")
        scale = tonumber(scale)
        if output and output:match("^[%w_.%-]+$") and (layout == "mirror" or layout == "extend")
            and (mode == "preferred" or mode:match("^%d+x%d+@%d+%.?%d*$"))
            and scale and scale >= 0.5 and scale <= 4 then
            display_rules[output] = { layout=layout, mode=mode, scale=scale }
        end
    end
    display_file:close()
end
for output, rule in pairs(display_rules) do
    local monitor = { output=output, mode=rule.mode, position="auto", scale=rule.scale }
    if rule.layout == "mirror" and primary then monitor.mirror = primary end
    hl.monitor(monitor)
end
hl.monitor({ output="", mode="preferred", position="auto", scale="auto" })
if primary then hl.workspace_rule({ workspace="1", monitor=primary, default=true }) end
hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")
hl.on("hyprland.start", function()
    hl.exec_cmd("~/.local/bin/start-bar")
    hl.exec_cmd("hyprpaper")
    hl.exec_cmd("~/.local/bin/change-wallpaper --restore")
    hl.exec_cmd("mako")
    hl.exec_cmd("systemctl --user start hyprpolkitagent.service")
    hl.exec_cmd("wl-paste --type text --watch cliphist store")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP HYPRLAND_INSTANCE_SIGNATURE")
end)
hl.config({
    general = {
        gaps_in = 6,
        gaps_out = 12,
        border_size = 1,
        layout = "dwindle",
        ["col.active_border"] = "rgba(999999cc)",
        ["col.inactive_border"] = "rgba(44444499)",
    },
    decoration = {
        rounding = 8,
        blur = {
            enabled = true,
            size = 3,
            passes = 2,
        },
        shadow = {
            enabled = true,
            range = 8,
            render_power = 3,
            color = "rgba(00000030)",
        },
    },
    animations = {
        enabled = true,
    },
    dwindle = {
        preserve_split = true,
    },
    input = {
        kb_layout = "us",
        sensitivity = 0,
        touchpad = {
            tap_to_click = true,
            disable_while_typing = true,
            natural_scroll = true,
        },
    },
    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo = true,
    },
})
hl.curve("restrained", { type="bezier", points={ {0.2,0.8}, {0.2,1.0} } })
hl.animation({ leaf="windows", enabled=true, speed=3, bezier="restrained" })
hl.animation({ leaf="fade", enabled=true, speed=2, bezier="default" })
hl.animation({ leaf="workspaces", enabled=true, speed=3, bezier="restrained", style="fade" })
hl.bind("SUPER + Q", hl.dsp.exec_cmd("kitty"))
hl.bind("SUPER + R", hl.dsp.exec_cmd("rofi -show drun"))
hl.bind("SUPER + SPACE", hl.dsp.exec_cmd("~/.local/bin/rice-command-palette"))
hl.bind("SUPER + C", hl.dsp.window.close())
hl.bind("SUPER + V", hl.dsp.window.float({ action="toggle" }))
hl.bind("SUPER + F", hl.dsp.window.fullscreen({ mode="fullscreen" }))
hl.bind("SUPER + TAB", hl.dsp.window.cycle_next())
hl.bind("SUPER + TAB", hl.dsp.window.bring_to_top())
hl.bind("SUPER + T", hl.dsp.exec_cmd("~/.local/bin/change-wallpaper"))
hl.bind("SUPER + E", hl.dsp.exec_cmd("thunar"))
hl.bind("SUPER + SHIFT + V", hl.dsp.exec_cmd("~/.local/bin/clipboard-menu"))
hl.bind("SUPER + L", hl.dsp.exec_cmd("~/.local/bin/lock-screen"))
hl.bind("SUPER + left", hl.dsp.focus({ direction="left" }))
hl.bind("SUPER + right", hl.dsp.focus({ direction="right" }))
hl.bind("SUPER + up", hl.dsp.focus({ direction="up" }))
hl.bind("SUPER + down", hl.dsp.focus({ direction="down" }))
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse=true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse=true })
hl.bind("Print", hl.dsp.exec_cmd("~/.local/bin/screenshot full"))
hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd("~/.local/bin/screenshot region"))
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("~/.local/bin/desktop-menu audio up"), { locked=true, repeating=true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("~/.local/bin/desktop-menu audio down"), { locked=true, repeating=true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked=true })
-- On this ThinkPad the physical F4 key can report either F4 or MicMute,
-- depending on Fn Lock. Both routes must reach the same ceiling toggle.
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("~/.local/bin/desktop-menu audio boost"), { locked=true })
hl.bind("SUPER + SHIFT + XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked=true })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("~/.local/bin/rice-media next"), { locked=true, repeating=true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("~/.local/bin/rice-media previous"), { locked=true, repeating=true })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("~/.local/bin/rice-media toggle"), { locked=true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("~/.local/bin/rice-media toggle"), { locked=true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("~/.local/bin/rice-media next"), { locked=true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("~/.local/bin/rice-media previous"), { locked=true })
hl.bind("SUPER + 1", hl.dsp.focus({ workspace=1 }))
hl.bind("SUPER + SHIFT + 1", hl.dsp.window.move({ workspace=1 }))
hl.bind("SUPER + 2", hl.dsp.focus({ workspace=2 }))
hl.bind("SUPER + SHIFT + 2", hl.dsp.window.move({ workspace=2 }))
hl.bind("SUPER + 3", hl.dsp.focus({ workspace=3 }))
hl.bind("SUPER + SHIFT + 3", hl.dsp.window.move({ workspace=3 }))
hl.bind("SUPER + 4", hl.dsp.focus({ workspace=4 }))
hl.bind("SUPER + SHIFT + 4", hl.dsp.window.move({ workspace=4 }))
hl.bind("SUPER + 5", hl.dsp.focus({ workspace=5 }))
hl.bind("SUPER + SHIFT + 5", hl.dsp.window.move({ workspace=5 }))
hl.bind("SUPER + 6", hl.dsp.focus({ workspace=6 }))
hl.bind("SUPER + SHIFT + 6", hl.dsp.window.move({ workspace=6 }))
hl.bind("SUPER + 7", hl.dsp.focus({ workspace=7 }))
hl.bind("SUPER + SHIFT + 7", hl.dsp.window.move({ workspace=7 }))
hl.bind("SUPER + 8", hl.dsp.focus({ workspace=8 }))
hl.bind("SUPER + SHIFT + 8", hl.dsp.window.move({ workspace=8 }))
hl.bind("SUPER + 9", hl.dsp.focus({ workspace=9 }))
hl.bind("SUPER + SHIFT + 9", hl.dsp.window.move({ workspace=9 }))

-- Per-session dashboard (never respawns on a config reload).
dofile(os.getenv('HOME') .. '/.local/share/rice/source/src/config/session.lua')

-- F4 toggles the volume ceiling; F5/F6 work with Fn-lock either on or off.
hl.bind("F4", hl.dsp.exec_cmd("~/.local/bin/desktop-menu audio boost"), { locked=true })
hl.bind("SUPER + SHIFT + F4", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked=true })
hl.bind("F5", hl.dsp.exec_cmd("~/.local/bin/rice-media previous"))
hl.bind("F6", hl.dsp.exec_cmd("~/.local/bin/rice-media next"))
