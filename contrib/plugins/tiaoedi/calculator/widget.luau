local function refresh(value)
  barWidget.setGlyph("calculator")
  barWidget.setText("")
  barWidget.setTooltip("hyprcalculadora" .. (value and (" • "..value) or "") .. "\nClique para abrir")
end
hyprbar.state.watch("latest",refresh)
refresh(hyprbar.state.get("latest"))
function onClick() hyprbar.togglePanel("tiaoedi/calculator:panel") end
function onIpc(event,_payload) if event=="toggle" then onClick() end end
