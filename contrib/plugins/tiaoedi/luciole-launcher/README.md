# Luciole Launcher para Hyprbar

Plugin de launcher que responde ao prefixo `/luciole` e inicia o executável `luciole` diretamente, sem shell intermediário. Requer uma instalação funcional do Luciole; não instala o aplicativo nem suas dependências.

O arquivo `luciole-theme.toml` registra o template de cores que acompanha o Luciole no Hyprbar. O Hyprbar renderiza a paleta ativa em `~/.config/luciole/colors.toml` quando as cores ou o modo mudam; o Luciole observa esse arquivo e atualiza suas janelas sem reiniciar. A sincronização usa apenas o motor nativo de templates do Hyprbar e não altera hooks existentes.

## Staging local

Copie `plugin.toml` e `launcher.luau` para `~/.local/share/hyprbar/plugins/luciole-launcher/`. Copie `luciole-theme.toml` para `~/.config/hyprbar/` e recarregue com `hyprbar msg config-reload`. O template inicializa `colors.toml` e acompanha as próximas mudanças de paleta/modo; os hooks já configurados não precisam ser alterados. Habilite o plugin explicitamente:

```sh
hyprbar msg plugins enable tiaoedi/luciole-launcher
```

Depois abra o launcher do Hyprbar, digite `/luciole` e selecione **Abrir Luciole**.

O conteúdo em `contrib/` é o snapshot de desenvolvimento; copiá-lo e habilitá-lo são etapas separadas.
