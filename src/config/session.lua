-- Start the dashboard once per login, as normal tiled windows.
-- Only the dedicated terminal classes get a workspace rule. Spotify has no
-- permanent floating, sizing, workspace, or fullscreen-suppression rule.
local apps = {
    { name='fastfetch', class='^session-fastfetch$', command='kitty --class session-fastfetch --title Fastfetch --hold fastfetch' },
    { name='btop', class='^session-btop$', command='kitty --class session-btop --title btop btop' },
    { name='pipes', class='^session-pipes$', command='kitty --class session-pipes --title pipes.sh ~/.local/bin/pipes.sh -p 4 -f 15 -c 7' },
}
for _, app in ipairs(apps) do
    hl.window_rule({name='session-'..app.name, match={class=app.class}, workspace='1 silent'})
end
hl.on('hyprland.start', function()
    hl.dispatch(hl.dsp.focus({workspace=1}))
    for _,app in ipairs(apps) do hl.exec_cmd(app.command) end
    hl.exec_cmd('spotify-launcher')
end)
