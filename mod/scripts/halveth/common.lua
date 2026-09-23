-- HALVETH Morrowind Genesis: plain-data protocol helpers, no executable input.
local M = {}
local escaped = { ['"']='\\"', ['\\']='\\\\', ['\b']='\\b', ['\f']='\\f', ['\n']='\\n', ['\r']='\\r', ['\t']='\\t' }
local function quote(s)
    return '"' .. s:gsub('[%z\1-\31\\"]', function(c)
        return escaped[c] or string.format('\\u%04x', string.byte(c))
    end) .. '"'
end
function M.json(value, depth)
    depth = depth or 0
    assert(depth < 15, 'JSON nesting limit')
    local t = type(value)
    if t == 'nil' then return 'null' end
    if t == 'boolean' then return value and 'true' or 'false' end
    if t == 'number' then
        assert(value == value and value ~= math.huge and value ~= -math.huge, 'Non-finite number')
        return tostring(value)
    end
    if t == 'string' then return quote(value) end
    assert(t == 'table', 'Only plain data may enter the bridge')
    local parts, n, count, isArray = {}, #value, 0, true
    for k in pairs(value) do
        count = count + 1
        if type(k) ~= 'number' or k < 1 or k > n or k % 1 ~= 0 then isArray = false end
    end
    local meta=getmetatable(value)
    isArray = isArray and count == n and (n > 0 or (meta and meta.jsonArray))
    if isArray then
        for i = 1,n do parts[#parts+1] = M.json(value[i], depth+1) end
        return '[' .. table.concat(parts, ',') .. ']'
    end
    local keys = {}
    for k in pairs(value) do assert(type(k)=='string', 'Object keys must be strings'); keys[#keys+1]=k end
    table.sort(keys)
    for _,k in ipairs(keys) do parts[#parts+1] = quote(k) .. ':' .. M.json(value[k], depth+1) end
    return '{' .. table.concat(parts, ',') .. '}'
end
local frameCounter=0
local framePrefix=string.format('%d-%d',os.time(),math.random(100000,999999))
function M.emit(data)
    -- OpenMW's logging stream can decorate long lines in the middle. Keep
    -- every transport line short and ASCII, then reassemble before JSON decode.
    local raw=M.json(data)
    assert(#raw<=65536,'Bridge event exceeds 64 KiB')
    frameCounter=frameCounter+1
    local eventId=framePrefix..'-'..frameCounter
    local chunkSize=384
    local count=math.ceil(#raw/chunkSize)
    for part=1,count do
        local chunk=raw:sub((part-1)*chunkSize+1,part*chunkSize)
        local hex=chunk:gsub('.',function(c) return string.format('%02x',string.byte(c)) end)
        print('HALVETH_FRAME:'..eventId..':'..part..':'..count..':'..hex)
    end
end
function M.array() return setmetatable({}, {jsonArray=true}) end
function M.head(s,limit)
    if #s<=limit then return s end
    local n=limit
    while n>0 and s:byte(n+1)>=128 and s:byte(n+1)<=191 do n=n-1 end
    return s:sub(1,n)
end
function M.tail(s,limit)
    if #s<=limit then return s end
    local n=#s-limit+1
    while n<=#s and s:byte(n)>=128 and s:byte(n)<=191 do n=n+1 end
    return s:sub(n)
end
function M.position(v) return {x=v.x, y=v.y, z=v.z} end
function M.finite(n) return type(n)=='number' and n==n and n~=math.huge and n~=-math.huge end
function M.validId(s) return type(s)=='string' and #s>0 and #s<=160 and s:match('^[%w_:%-%.]+$')~=nil end
return M
