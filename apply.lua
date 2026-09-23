-- Regenerate native application configs from the Lua sources in this folder.
local home = assert(os.getenv('HOME'))
local root = home .. '/config/'
local function quote(s)
    return '"' .. s:gsub('[%z\1-\31\\"]', function(c)
        return ({['"']='\\"', ['\\']='\\\\', ['\n']='\\n', ['\r']='\\r', ['\t']='\\t'})[c]
            or string.format('\\u%04x', c:byte())
    end) .. '"'
end
local function json(v)
    if type(v) == 'string' then return quote(v) end
    if type(v) ~= 'table' then return tostring(v) end
    local out = {}
    if #v > 0 or next(v) == nil then
        for _, x in ipairs(v) do out[#out+1] = json(x) end
        return '[' .. table.concat(out, ',') .. ']'
    end
    local keys = {}
    for k in pairs(v) do keys[#keys+1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do out[#out+1] = quote(k) .. ':' .. json(v[k]) end
    return '{' .. table.concat(out, ',') .. '}'
end
local function render(data, format)
    if format == 'json' then return json(data) .. '\n' end
    local out = {}
    for _, row in ipairs(data) do
        if row.entries then
            out[#out+1] = (row.selector or row.section) .. ' {'
            for _, entry in ipairs(row.entries) do
                out[#out+1] = '    ' .. entry.key .. (format == 'css' and ': ' or ' = ')
                    .. entry.value .. (format == 'css' and ';' or '')
            end
            out[#out+1] = '}'
        elseif row.section then
            out[#out+1] = '[' .. row.section .. ']'
        else
            out[#out+1] = row.key .. (format == 'space' and ' ' or format == 'compact-equals' and '=' or ' = ') .. row.value
        end
    end
    return table.concat(out, '\n') .. '\n'
end
-- Evaluate every source before updating any generated file.
local pending = {}
for _, item in ipairs(dofile(root .. 'manifest.lua')) do
    pending[#pending+1] = { path=home .. '/.config/' .. item.target,
        content=render(dofile(root .. item.source), item.format) }
end
for _, item in ipairs(pending) do
    local tmp = item.path .. '.lua-tmp'
    local f = assert(io.open(tmp, 'w'))
    assert(f:write(item.content)); assert(f:close())
    assert(os.rename(tmp, item.path))
    print('Generated ' .. item.path)
end
