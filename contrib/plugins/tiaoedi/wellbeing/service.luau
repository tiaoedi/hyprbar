-- The only entry allowed to own clocks, notifications or daily persistence.
local scheduler = require("./scheduler.luau")
local function settings()
  return {
    water_enabled = hyprbar.getConfig("water_enabled"), water_minutes = hyprbar.getConfig("water_minutes"),
    eyes_enabled = hyprbar.getConfig("eyes_enabled"), eyes_minutes = hyprbar.getConfig("eyes_minutes"),
    stretch_enabled = hyprbar.getConfig("stretch_enabled"), stretch_minutes = hyprbar.getConfig("stretch_minutes"),
  }
end
local dir = hyprbar.pluginDataDir()
local path = dir and (dir .. "/daily.json")
local saved
if path then
  local raw = hyprbar.readFile(path)
  if raw and #raw <= 1024 then saved = hyprbar.json.decode(raw) end
end
local state = scheduler.new(settings(), hyprbar.nowMs(), hyprbar.formatTime("%Y-%m-%d"), saved)
local lastSaved
local persistenceError = false
local function atomicWrite(target, raw)
  if not raw then return false end
  local ok = hyprbar.writeFile(target .. ".tmp", raw)
  if ok then ok = hyprbar.renameFile(target .. ".tmp", target) end
  return ok == true
end
local function publish(force)
  hyprbar.state.set("view", scheduler.view(state, state.last))
  local persisted = scheduler.persist(state)
  local raw = hyprbar.json.encode(persisted)
  persisted.usageMs = math.floor(persisted.usageMs / 60000) * 60000
  local signature = hyprbar.json.encode(persisted)
  if path and (force or signature ~= lastSaved) then
    -- Checkpoint usage once per minute, or flush on orderly runtime exit.
    lastSaved = signature
    if atomicWrite(path, raw) then persistenceError = false
    elseif not persistenceError then
      persistenceError = true; hyprbar.log("Bem-estar: não foi possível salvar o contador diário.")
    end
  end
end
local messages = {
  water = "Beba água quando for confortável para você.",
  eyes = "Descanse os olhos: olhe para longe da tela por alguns instantes.",
  stretch = "Faça uma pausa e alongue-se com conforto.",
}
local function step()
  local alerts = scheduler.tick(state, hyprbar.nowMs(), hyprbar.formatTime("%Y-%m-%d"))
  local text = {}
  for _, id in ipairs(alerts) do text[#text + 1] = messages[id] end
  if #text > 0 then hyprbar.notify("Bem-estar", table.concat(text, "\n")) end
end
local function command(event)
  step()
  scheduler.command(state, event, state.last)
  publish()
end
hyprbar.state.watch("request", function(request)
  if type(request) == "table" and type(request.event) == "string" then command(request.event) end
end)
hyprbar.setUpdateInterval(1000)
function update() step(); publish() end
function onConfigChanged()
  step(); scheduler.configure(state, settings(), state.last); publish()
end
function onIpc(event, _payload)
  if event == "diagnostics" then
    step(); publish()
    if dir and not atomicWrite(dir .. "/diagnostics.json", hyprbar.json.encode(scheduler.view(state, state.last))) then
      hyprbar.log("Bem-estar: falha ao gravar diagnostics.json.")
    end
  else command(event) end
end
function onExit(_signal, _reason) publish(true) end
publish()
