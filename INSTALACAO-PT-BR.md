# Instalação do Hyprbar no Fedora 44

Hyprbar é um shell de desktop Wayland mantido de forma independente. A compilação e a suíte de testes foram verificadas em Fedora 44 x86_64; não há RPM pré-compilado publicado ainda.

## Compilar e instalar

Instale as dependências listadas em [`BUILDING.md`](BUILDING.md), baixe o código-fonte e compile:

```sh
git clone --depth 1 https://github.com/tiaoedi/hyprbar.git
cd hyprbar
just configure release
just build release
sudo just install release
```

Essa instalação manual não altera a configuração do Hyprland nem ativa a inicialização automática.

## Iniciar

Para testar na sessão Wayland atual:

```sh
hyprbar --daemon
```

Para iniciar no login do Hyprland, adicione à configuração do compositor:

```ini
exec-once = hyprbar --daemon
```

A entrada de desktop `dev.hyprbar.Hyprbar` também pode iniciar o serviço.

## Compilar do código-fonte

As dependências e opções de compilação estão em [`BUILDING.md`](BUILDING.md).

## Migrar uma configuração existente

A configuração do Hyprbar fica em diretórios XDG próprios e não é copiada automaticamente. Primeiro veja as opções e o modo de prévia:

```sh
hyprbar config import-noctalia --help
```

A prévia é o comportamento padrão. Use `--apply` somente depois de revisar o que será importado.

## Compatibilidade

- Fedora 44 x86_64: compilação do código-fonte e suíte de testes verificadas; RPM ainda não publicado.
- Hyprland 0.56.2: execução e painéis principais verificados.
- Niri: sintaxe de inicialização conferida; execução não verificada.
- Outros compositores e distribuições: o código contém integrações herdadas, mas não foram testados como parte deste fork.

É necessária uma sessão Wayland com suporte EGL/GLES. Recursos de áudio dependem de PipeWire/WirePlumber. Veja [`docs/user/getting-started/installation.mdx`](docs/user/getting-started/installation.mdx) para a documentação complementar.
