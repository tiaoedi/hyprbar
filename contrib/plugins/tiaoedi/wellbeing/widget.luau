local function render(v)
  barWidget.setGlyph("heart")
  if not v then
    barWidget.setText("")
    barWidget.setTooltip("Bem-estar: iniciando lembretes…")
    return
  end
  local pending = 0
  for _, r in pairs(v.reminders) do if r.enabled and r.pending then pending = pending + 1 end end
  barWidget.setText(v.paused and "Ⅱ" or (pending > 0 and tostring(pending) or ""))
  barWidget.setGlyphColor(pending > 0 and "primary" or "on_surface")
  barWidget.setTooltip("Bem-estar • Água hoje: " .. tostring(v.count) .. (v.paused and " • Pausado" or "") .. "\nClique para abrir o painel")
end
hyprbar.state.watch("view", render)
render(hyprbar.state.get("view"))
function onClick() hyprbar.togglePanel("tiaoedi/wellbeing:panel") end
function onIpc(event, _payload) if event == "toggle" then onClick() end end
