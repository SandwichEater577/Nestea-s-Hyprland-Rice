-- Native monochrome theme. Regenerate with lua ~/config/src/config/apply.lua.
return {
    { selector = "configuration", entries = {
        { key = "modi", value = "\"drun,run,window\"" },
        { key = "show-icons", value = "false" },
        { key = "font", value = "\"Adwaita Sans 11\"" },
        { key = "display-drun", value = "\"Apps\"" },
        { key = "display-run", value = "\"Run\"" },
        { key = "display-window", value = "\"Windows\"" },
        { key = "drun-display-format", value = "\"{name}\"" },
        { key = "matching", value = "\"fuzzy\"" },
        { key = "sort", value = "true" },
        { key = "cycle", value = "true" },
        { key = "scroll-method", value = "0" },
    } },
    { selector = "*", entries = {
        { key = "background-color", value = "transparent" },
        { key = "border-color", value = "#3c3c3c" },
        { key = "text-color", value = "#ededed" },
    } },
    { selector = "window", entries = {
        { key = "width", value = "520px" },
        { key = "location", value = "center" },
        { key = "anchor", value = "center" },
        { key = "border", value = "1px" },
        { key = "border-color", value = "#3c3c3c" },
        { key = "border-radius", value = "16px" },
        { key = "background-color", value = "#191919" },
    } },
    { selector = "mainbox", entries = {
        { key = "padding", value = "16px" },
        { key = "spacing", value = "12px" },
        { key = "children", value = "[inputbar,message,listview]" },
    } },
    { selector = "inputbar", entries = {
        { key = "children", value = "[prompt,entry]" },
        { key = "spacing", value = "12px" },
        { key = "padding", value = "13px" },
        { key = "border", value = "0px" },
        { key = "border-color", value = "#ffffff" },
        { key = "background-color", value = "#272727" },
        { key = "border-radius", value = "10px" },
    } },
    { selector = "prompt", entries = {
        { key = "text-color", value = "#bdbdbd" },
    } },
    { selector = "entry", entries = {
        { key = "placeholder", value = "\"Search…\"" },
        { key = "placeholder-color", value = "#858585" },
    } },
    { selector = "message", entries = {
        { key = "padding", value = "8px 10px" },
        { key = "border", value = "0px" },
        { key = "border-color", value = "#ffffff" },
    } },
    { selector = "textbox", entries = {
        { key = "text-color", value = "#b0b0b0" },
    } },
    { selector = "listview", entries = {
        { key = "border", value = "0px" },
        { key = "lines", value = "7" },
        { key = "columns", value = "1" },
        { key = "fixed-height", value = "false" },
        { key = "spacing", value = "4px" },
        { key = "scrollbar", value = "false" },
    } },
    { selector = "element", entries = {
        { key = "padding", value = "12px" },
        { key = "spacing", value = "10px" },
        { key = "border-radius", value = "9px" },
        { key = "text-color", value = "#ffffff" },
    } },
    { selector = "element normal.normal, element alternate.normal, element normal.active, element alternate.active", entries = {
        { key = "background-color", value = "transparent" },
        { key = "text-color", value = "#c5c5c5" },
    } },
    { selector = "element selected.normal, element selected.active, element selected.urgent", entries = {
        { key = "background-color", value = "#333333" },
        { key = "text-color", value = "#ffffff" },
    } },
    { selector = "element-text", entries = {
        { key = "vertical-align", value = "0.5" },
        { key = "background-color", value = "inherit" },
        { key = "text-color", value = "inherit" },
    } },
    { selector = "element-icon", entries = {
        { key = "size", value = "18px" },
        { key = "background-color", value = "inherit" },
        { key = "text-color", value = "inherit" },
    } },
}
