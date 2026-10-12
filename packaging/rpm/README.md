# Fedora RPM

Ainda não há RPM pré-compilado nem checksum publicados na [página de Releases](https://github.com/tiaoedi/hyprbar/releases). O spec destina-se ao Fedora 44 x86_64; não há repositório DNF configurado.

## Verificação e instalação

Depois de uma release ser publicada, baixe o RPM e o arquivo SHA-256 correspondente da mesma versão. No momento, esses arquivos ainda não existem. Para compilar localmente, use os comandos abaixo.

```sh
sha256sum -c hyprbar-5.2.1-1.fc44.x86_64.rpm.sha256
sudo dnf install ./hyprbar-5.2.1-1.fc44.x86_64.rpm
```

Os comandos de verificação/instalação acima só se aplicam depois de os artefatos existirem. Releases não serão assinadas por GPG nesta etapa; um SHA-256 pode detectar corrupção acidental, não comprova autoria. O pacote não é instalado no host durante a compilação.

## Reproduzir a compilação

A partir da raiz do repositório, crie o arquivo de origem e expanda o spec antes do build:

```sh
version=$(tr -d '\n' < VERSION)
mkdir -p "$HOME/rpmbuild/SOURCES"
git archive --format=tar.gz --prefix="hyprbar-${version}/" HEAD \
  -o "$HOME/rpmbuild/SOURCES/hyprbar-${version}.tar.gz"
rpmspec -P packaging/rpm/hyprbar.spec
RPM_BUILD_NCPUS=4 rpmbuild -ba packaging/rpm/hyprbar.spec
```

O spec usa as macros Meson do Fedora, executa os testes com diretórios HOME/XDG isolados, inclui assets e licenças de dependências vendorizadas e gera completions Bash/Zsh/Fish do executável recém-compilado. Requisitos de bibliotecas compartilhadas são gerados pelo RPM a partir dos binários.

Fedora 44 x86_64 é o único alvo de pacote planejado para esta primeira versão. Os nomes de dependências usados para outras distribuições em `BUILDING.md` são notas herdadas do upstream, não uma declaração de compatibilidade testada.
