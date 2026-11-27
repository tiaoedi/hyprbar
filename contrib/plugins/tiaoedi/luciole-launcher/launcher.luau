function onQuery(text)
  launcher.setResults(text, {
    {
      id = "open",
      title = "Abrir Luciole",
      subtitle = "Gerenciador de arquivos Wayland",
      glyph = "folder",
    },
  })
end

function onActivate(id)
  if id ~= "open" then
    return
  end

  if not hyprbar.commandExists("luciole") then
    hyprbar.notifyError("Luciole não encontrado", "Instale o Luciole e confirme que o executável está no PATH.")
    return
  end

  if not hyprbar.runAsync("luciole") then
    hyprbar.notifyError("Falha ao abrir Luciole", "O Hyprbar não conseguiu iniciar o processo.")
  end
end
