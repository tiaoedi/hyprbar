-- HOST MOCK ONLY: executes entry code in Lua, not Hyprbar/Luau/native UI.
local root = arg[1] or "."
local now, day = 0, "2026-10-31"
local data, watches, files = {}, {}, {}
local writes, notices = 0, 0
local config = { water_minutes = 1, eyes_minutes = 1, stretch_minutes = 1 }
local function encode(v)
  if type(v) ~= "table" then return tostring(v) end
  local keys, parts = {}, {}
  for k in pairs(v) do keys[#keys+1] = k end
  table.sort(keys)
  for _, k in ipairs(keys) do parts[#parts+1] = tostring(k) .. "=" .. encode(v[k]) end
  return "{" .. table.concat(parts, ";") .. "}"
end
local h = {
  nowMs = function() return now end, formatTime = function() return day end,
  getConfig = function(k) return config[k] end, setUpdateInterval = function(ms) assert(ms >= 1000) end,
  pluginDataDir = function() return "/mock/wellbeing" end,
  readFile = function(p) return files[p] end,
  writeFile = function(p, v) files[p] = v; writes = writes + 1; return true end,
  renameFile = function(a,b) files[b]=files[a]; files[a]=nil; return true end,
  json = { encode = encode, decode = function() return nil end },
  log = function() end, notify = function() notices = notices + 1 end,
  state = {
    get = function(k) return data[k] end,
    set = function(k,v) data[k]=v; for _, f in ipairs(watches[k] or {}) do f(v) end end,
    watch = function(k,f) watches[k]=watches[k] or {}; table.insert(watches[k],f) end,
  },
}
local function entry(name, extra)
  local env = setmetatable({hyprbar=h}, {__index=_G})
  env.require = function(p) return dofile(root .. "/" .. p) end
  for k,v in pairs(extra or {}) do env[k]=v end
  local fn, err = loadfile(root .. "/" .. name .. ".luau", "t", env)
  assert(fn, "missing entry: " .. tostring(err)); fn(); return env
end
local service = entry("service")
assert(data.view and data.view.count == 0 and data.view.reminders.eyes.remainingMs == 60000)
local initialWrites = writes
for i=1,59 do now=i*1000; service.update() end
assert(writes == initialWrites, "usage ticks must not write before minute checkpoint")
now=60000; service.update()
assert(notices == 1, "simultaneous reminders must aggregate")
assert(writes == initialWrites + 1, "usage minute checkpoint must persist once")
now=61000; service.update(); assert(notices == 1)
assert(writes == initialWrites + 1, "must not persist every usage tick")
service.onIpc("pause", ""); assert(data.view.paused)
service.onIpc("snooze", ""); assert(data.view.reminders.eyes.remainingMs == 300000)
service.onIpc("resume", ""); assert(not data.view.paused)
h.state.set("request", { event="water", nonce=1 }); assert(data.view.count == 1)
service.onIpc("diagnostics", "")
assert(files["/mock/wellbeing/diagnostics.json"] == encode(data.view))
assert(files["/mock/wellbeing/daily.json"])
print("PASS HOST MOCK singleton service, aggregate alerts, request/IPC, bounded persistence, diagnostics")
local toggles, glyph, label, tooltip = 0
h.togglePanel = function(id) assert(id == "tiaoedi/wellbeing:panel"); toggles = toggles + 1 end
local bar = {
  setGlyph = function(v) glyph=v end, setText = function(v) label=v end,
  setTooltip = function(v) tooltip=v end, setGlyphColor = function() end,
}
local w1 = entry("widget", {barWidget=bar})
local w2 = entry("widget", {barWidget=bar})
w1.onClick(); w2.onClick()
assert(toggles == 2 and glyph == "heart" and type(tooltip) == "string")
assert(notices == 1, "widget placements must not generate alerts")
print("PASS HOST MOCK two bar placements toggle panel without owning timers")
local tree, settingsOpened
local ui = setmetatable({}, { __index=function(_,kind) return function(props, children) return {kind=kind, props=props, children=children} end end })
h.openSettings = function() settingsOpened=true end
local p = entry("panel", { ui=ui, panel={render=function(v) tree=v end} })
p.onOpen()
local buttons, labels = {}, {}
local function walk(node)
  if node.kind == "button" then buttons[node.props.onClick]=node.props end
  if node.kind == "label" then labels[node.props.text]=true end
  for _, child in ipairs(node.children or {}) do walk(child) end
end
walk(tree)
assert(labels["Tempo de uso hoje: 00h 01m 01s"], "daily usage missing from panel")
assert(labels["Nesta sessão: 00h 01m 01s"], "session usage missing from panel")
for _, cb in ipairs({"drinkWater", "restEyes", "stretchBody", "togglePause", "snooze", "configure"}) do
  assert(buttons[cb] and type(p[cb]) == "function", "missing panel action " .. cb)
end
p.togglePause(); assert(data.view.paused)
p.snooze(); assert(data.view.reminders.eyes.remainingMs==300000)
p.togglePause(); assert(not data.view.paused)
p.restEyes(); assert(not data.view.reminders.eyes.pending)
p.stretchBody(); assert(not data.view.reminders.stretch.pending)
p.drinkWater(); assert(data.view.count == 2)
p.configure(); assert(settingsOpened)
p.onClose()
print("PASS HOST MOCK Portuguese panel actions route through singleton")
local attempts=0
h.writeFile=function() attempts=attempts+1; return false end
service.onIpc("water", "")
local first=attempts
now=now+1000; service.update()
assert(attempts==first, "disk failure must not trigger writes each second")
print("PASS HOST MOCK persistence failure does not retry each tick")
h.writeFile=function(path, raw) files[path]=raw; writes=writes+1; return true end
local beforeExit = writes
assert(type(service.onExit)=="function", "missing orderly exit usage flush")
service.onExit("", "reload")
assert(writes==beforeExit+1 and files["/mock/wellbeing/daily.json"]:find("usageMs=62000",1,true), "exit did not flush exact usage")
print("PASS HOST MOCK exact usage flushes on orderly runtime exit")
