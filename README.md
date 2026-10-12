# Hyprbar

![Ícone do Hyprbar](assets/hyprbar.svg)

Fork independente de **Noctalia v5.2.1**: um shell de desktop nativo para Wayland, com barra, widgets, dock, launcher, notificações, controles de sessão e seletor de papéis de parede. Esta é a distribuição mantida por `tiaoedi`; não é o projeto oficial Noctalia e não é endossada pelos mantenedores originais.

- Desenvolvedor: `sebastao .o santana` (GitHub: [@tiaoedi](https://github.com/tiaoedi))
- YouTube: [Linux Livre](https://www.youtube.com/@linuxlivre9008)

## Baixar e instalar

O GitHub oferece arquivos ZIP/TAR do código-fonte; consulte [Releases](https://github.com/tiaoedi/hyprbar/releases) para pacotes binários quando houver uma versão publicada. Não há RPM nem checksum de release publicados ainda. Para compilar no Fedora, siga [`INSTALACAO-PT-BR.md`](INSTALACAO-PT-BR.md) e [`BUILDING.md`](BUILDING.md).

Para iniciar automaticamente no Hyprland, adicione `exec-once = hyprbar --daemon` à configuração do compositor. No Niri, consulte [`docs/user/compositor-settings/niri.mdx`](docs/user/compositor-settings/niri.mdx). A documentação complementar está em [`docs/user/getting-started/installation.mdx`](docs/user/getting-started/installation.mdx).

## Compatibilidade verificada

| Ambiente | Verificação deste fork |
|---|---|
| Fedora 44 x86_64 | Compilação do código-fonte e suíte de testes verificados; RPM ainda não publicado |
| Hyprland 0.56.2 | Execução e painéis principais verificados |
| Niri | Configuração de inicialização validada; execução não verificada |
| Outros compositores/distribuições | O código contém integrações herdadas, mas não foram validadas para este fork |

É necessário iniciar em uma sessão Wayland com suporte EGL/GLES. Áudio depende de PipeWire/WirePlumber; recursos opcionais podem depender de serviços disponíveis na sessão. A compatibilidade efetiva varia conforme os protocolos e recursos oferecidos pelo compositor.

## Serviços remotos herdados

Este fork ainda usa endpoints herdados de `api.noctalia.dev` para recursos opcionais como catálogos de paletas/templates, geolocalização/geocodificação, consulta de IP público e OAuth do Google Calendar. A telemetria é opt-in (`telemetry_enabled = false` por padrão). Este repositório não estabelece quem opera atualmente esses endpoints, nem a retenção ou o uso dos dados; a política publicada pelo Noctalia é apenas uma referência upstream, não uma política do Hyprbar, e não verificamos se ela cobre essas requisições. `offline_mode = true` bloqueia novos pedidos pelo cliente HTTP compartilhado do Hyprbar, mas não cancela transferências já em andamento e não é firewall: navegador, outros processos e caminhos arbitrários de plugins podem continuar usando a rede. Caches locais ainda podem ser lidos. Veja `NETWORK-PRIVACY.md` e a documentação de [localização](docs/user/services/location.mdx), [calendário](docs/user/services/calendar.mdx) e [configuração](docs/user/configuration/shell.mdx).

## Compilar do código-fonte

Consulte [`BUILDING.md`](BUILDING.md) para dependências e instruções por distribuição. Exemplo:

```sh
git clone --depth 1 https://github.com/tiaoedi/hyprbar.git
cd hyprbar
just configure release
just build release
sudo just install release
```

Se estiver migrando uma configuração antiga, use `hyprbar config import-noctalia --help` para revisar a importação antes de aplicá-la. Hyprbar mantém nomes internos `noctalia.*` em algumas interfaces por compatibilidade; isso não altera a identidade independente do fork.

## Créditos e licença

O código-fonte deriva do [Noctalia v5.2.1](https://github.com/noctalia-dev/noctalia). Os créditos upstream foram preservados em [`CREDITS.md`](CREDITS.md). A licença principal é MIT; componentes incluídos em `third_party/` e a fonte Tabler mantêm suas próprias licenças. Consulte [`LICENSE`](LICENSE) e os avisos de cada componente antes de redistribuir.
