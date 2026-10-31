local root = arg[1] or "."
local function read(path)
  local f = assert(io.open(root .. "/" .. path), "missing package artifact " .. path)
  local s=f:read("*a"); f:close(); return s
end
local manifest=read("plugin.toml")
assert(manifest:find('id = "tiaoedi/wellbeing"',1,true))
assert(manifest:find('plugin_api = 22',1,true))
assert(manifest:find('id = "reminders"',1,true))
for _,id in ipairs({"water","eyes","stretch"}) do
  for _,suffix in ipairs({"enabled","minutes"}) do
    local key=id .. "_" .. suffix
    assert(manifest:find('key = "' .. key .. '"',1,true))
    assert(read("translations/en.json"):find('settings.' .. key,1,true))
    assert(read("translations/pt.json"):find('settings.' .. key,1,true))
  end
end
print("PASS manifest API22, singleton entry and translated settings package")
