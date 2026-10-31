-- Pure Lua/Luau scheduler; all timestamps are wall-clock milliseconds.
local M = {}
M.ids = { "water", "eyes", "stretch" }
local defaults = { water = 45, eyes = 20, stretch = 60 }
local function bounded(value, fallback, low, high)
  if type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then return fallback end
  return math.max(low, math.min(high, math.floor(value)))
end
function M.new(config, now, day, saved)
  saved = type(saved) == "table" and saved or {}
  local s = { last = now, day = day, count = 0, usageMs = 0, sessionMs = 0, paused = saved.paused == true, reminders = {} }
  if saved.day == day then
    s.count = bounded(saved.count, 0, 0, 999)
    s.usageMs = bounded(saved.usageMs, 0, 0, 86400000)
  end
  for _, id in ipairs(M.ids) do
    local interval = defaults[id] * 60000
    s.reminders[id] = { interval = interval, enabled = true, due = now + interval, pending = false }
  end
  M.configure(s, config, now)
  return s
end
function M.configure(s, config, now)
  config = type(config) == "table" and config or {}
  for _, id in ipairs(M.ids) do
    local r = s.reminders[id]
    local interval = bounded(config[id .. "_minutes"], defaults[id], 1, 1440) * 60000
    local enabled = config[id .. "_enabled"] ~= false
    if r.interval ~= interval or r.enabled ~= enabled then
      r.interval = interval; r.enabled = enabled
      r.due = now + interval; r.remaining = interval; r.pending = false
    end
  end
end
function M.view(s, now)
  local v = { day = s.day, count = s.count, usageMs = s.usageMs, sessionMs = s.sessionMs, paused = s.paused, updatedAtMs = now, reminders = {} }
  for _, id in ipairs(M.ids) do
    local r = s.reminders[id]
    v.reminders[id] = { enabled = r.enabled, intervalMs = r.interval, pending = r.pending,
      remainingMs = s.paused and (r.remaining or r.interval) or math.max(0, r.due - now) }
  end
  return v
end
function M.tick(s, now, day)
  local changedDay = s.day ~= day
  if changedDay then s.day = day; s.count = 0; s.usageMs = 0 end
  local jump = now < s.last or now - s.last > 120000
  if not jump and not s.paused then
    if not changedDay then s.usageMs = math.min(86400000, s.usageMs + now - s.last) end
    s.sessionMs = s.sessionMs + now - s.last
  end
  s.last = now
  if jump then
    for _, id in ipairs(M.ids) do
      local r = s.reminders[id]
      r.due = now + r.interval; r.remaining = r.interval; r.pending = false
    end
    return {}
  end
  local alerts = {}
  for _, id in ipairs(M.ids) do
    local r = s.reminders[id]
    if not s.paused and r.enabled and not r.pending and now >= r.due then
      r.pending = true
      alerts[#alerts + 1] = id
    end
  end
  return alerts
end
function M.command(s, event, now)
  if event == "pause" or event == "resume" then
    local pause = event == "pause"
    if pause ~= s.paused then
      for _, id in ipairs(M.ids) do
        local r = s.reminders[id]
        if pause then r.remaining = math.max(0, r.due - now)
        else r.due = now + (r.remaining or r.interval) end
      end
      s.paused = pause
    end
    return true
  end
  if event == "snooze" then
    for _, id in ipairs(M.ids) do
      local r = s.reminders[id]
      r.pending = false; r.due = now + 300000; r.remaining = 300000
    end
    return true
  end
  local r = s.reminders[event]
  if not r then return false end
  r.pending = false
  r.due = now + r.interval
  r.remaining = r.interval
  if event == "water" then s.count = math.min(999, s.count + 1) end
  return true
end
function M.persist(s)
  return { day = s.day, count = s.count, paused = s.paused, usageMs = s.usageMs }
end
return M
