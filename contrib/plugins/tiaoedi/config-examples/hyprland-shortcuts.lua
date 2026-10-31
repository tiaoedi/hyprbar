-- Snippet for the user's Hyprland Lua config; requires `hl`, `mainMod`, and `hyprbar`.
hl.bind(mainMod .. " + F7", hl.dsp.exec_cmd(hyprbar .. " msg panel-toggle tiaoedi/calculator:panel"), { description = "Abrir/fechar hyprcalculadora" })
hl.bind(mainMod .. " + F9", hl.dsp.exec_cmd(hyprbar .. " msg panel-toggle tiaoedi/wellbeing:panel"), { description = "Abrir/fechar painel Bem-estar" })
