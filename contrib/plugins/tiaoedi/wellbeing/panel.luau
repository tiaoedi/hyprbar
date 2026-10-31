local opened = false
local sequence = 0
local names = { water = "Hidratação", eyes = "Descanso dos olhos", stretch = "Alongamento" }
local function remaining(r)
  if not r.enabled then return "Desativado" end
  if r.pending then return "Pausa pendente" end
  local seconds = math.ceil(r.remainingMs / 1000)
  return string.format("%02d:%02d", math.floor(seconds / 60), seconds % 60)
end
local function render()
  if not opened then return end
  local v = hyprbar.state.get("view")
  if not v then
    panel.render(ui.label({ text = "Bem-estar: iniciando lembretes…", color = "on_surface" }))
    return
  end
  local dailySeconds = math.floor((v.usageMs or 0) / 1000)
  local sessionSeconds = math.floor((v.sessionMs or 0) / 1000)
  local rows = {
    ui.row({ gap = 10, align = "center" }, {
      ui.glyph({ name = "heart", size = 24, color = "primary" }),
      ui.label({ text = "Bem-estar", fontSize = 22, fontWeight = "bold" }),
    }),
    ui.label({ text = "Água registrada hoje: " .. tostring(v.count) .. " • " .. v.day }),
    ui.label({ text = string.format("Tempo de uso hoje: %02dh %02dm %02ds", math.floor(dailySeconds / 3600), math.floor(dailySeconds / 60) % 60, dailySeconds % 60), fontWeight = "bold", color = "primary" }),
    ui.label({ text = string.format("Nesta sessão: %02dh %02dm %02ds", math.floor(sessionSeconds / 3600), math.floor(sessionSeconds / 60) % 60, sessionSeconds % 60) }),
    ui.label({ text = v.paused and "Lembretes pausados • tempos congelados" or "Lembretes ativos", color = "primary" }),
  }
  for _, id in ipairs({ "water", "eyes", "stretch" }) do
    rows[#rows + 1] = ui.row({ justify = "space_between", gap = 12 }, {
      ui.label({ text = names[id], flexGrow = 1 }),
      ui.label({ text = remaining(v.reminders[id]), color = "primary" }),
    })
  end
  rows[#rows + 1] = ui.button({ text = "Bebi água (+1)", glyph = "droplet", variant = "primary", onClick = "drinkWater" })
  rows[#rows + 1] = ui.button({ text = "Concluí a pausa dos olhos", glyph = "eye", onClick = "restEyes" })
  rows[#rows + 1] = ui.button({ text = "Concluí o alongamento", glyph = "stretching", onClick = "stretchBody" })
  rows[#rows + 1] = ui.row({ gap = 8 }, {
    ui.button({ text = v.paused and "Retomar" or "Pausar", onClick = "togglePause", flexGrow = 1 }),
    ui.button({ text = "Adiar tudo 5 min", onClick = "snooze", flexGrow = 1 }),
  })
  rows[#rows + 1] = ui.button({ text = "Configurações", glyph = "settings", variant = "ghost", onClick = "configure" })
  rows[#rows + 1] = ui.label({ text = "Uso acompanhado pelo plugin; não detecta inatividade. Pausar congela também a contagem.", maxLines = 3, fontSize = 12 })
  panel.render(ui.column({ padding = 16, gap = 12 }, rows))
end
local function request(event)
  sequence = sequence + 1
  hyprbar.state.set("request", { event = event, nonce = tostring(hyprbar.nowMs()) .. ":" .. tostring(sequence) })
end
function drinkWater() request("water") end
function restEyes() request("eyes") end
function stretchBody() request("stretch") end
function togglePause()
  local v = hyprbar.state.get("view")
  if v then request(v.paused and "resume" or "pause") end
end
function snooze() request("snooze") end
function configure() hyprbar.openSettings() end
function onOpen(_context) opened = true; render() end
function onClose() opened = false end
hyprbar.state.watch("view", function() render() end)
