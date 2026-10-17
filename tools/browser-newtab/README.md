# Hyprbar · Nova aba

Companion MV3 local para Chrome e Brave. Substitui **apenas a nova aba** por
uma página em português, com relógio/data locais, pesquisa e fundo plano
ocupando toda a janela. Não altera sites, barra de ferramentas, perfis,
favoritos, buscador padrão ou o tema principal do navegador.

Tudo é empacotado: HTML, JavaScript, CSS e fonte do sistema. Sem CDNs,
telemetria, imagens remotas, content scripts, service worker ou permissões
de host. A única permissão é `search`, para `chrome.search.query()` usar o
buscador já escolhido pelo usuário na mesma aba. A pesquisa só sai para a
rede depois de uma submissão explícita; URLs digitadas aqui também são
pesquisadas. A barra de endereço continua sendo o lugar para navegar.

## Arquivos e caminhos

| Arquivo de origem | Destino de instalação |
| --- | --- |
| `manifest.json`, `newtab.html`, `newtab.css`, `newtab.js`, `palette.css` | `~/.local/share/hyprbar/extensions/newtab/` |
| `palette.css.in` | `~/.config/hyprbar/templates/browser-newtab/palette.css.in` |
| `browser-newtab.toml` | `~/.config/hyprbar/browser-newtab.toml` |

O caminho da extensão é fixo: **`~/.local/share/hyprbar/extensions/newtab`**.
Não carregue a pasta temporária dos testes como extensão de uso diário.
`palette.css` é um fallback gerado e verificado com os tokens escuros de
`assets/palettes/hyprbar moderno.json`; **não representa necessariamente a
paleta ativa**. A integração escreve a paleta ativa por cima desse arquivo.
Os sete tokens do template usam `.default`, respeitando o modo resolvido
pelo Hyprbar, inclusive mudanças entre claro e escuro.

## Instalação manual (não executada por estes testes)

Primeiro confira colisões e preserve cópias de quaisquer arquivos já
existentes nos destinos. Não sobrescreva uma integração existente sem
revisá-la. A partir desta pasta, com os diretórios de configuração padrão:

```sh
install -d "$HOME/.local/share/hyprbar/extensions/newtab"
install -m 644 manifest.json newtab.html newtab.css newtab.js palette.css \
  "$HOME/.local/share/hyprbar/extensions/newtab/"
install -d "$HOME/.config/hyprbar/templates/browser-newtab"
install -m 644 palette.css.in \
  "$HOME/.config/hyprbar/templates/browser-newtab/palette.css.in"
install -m 644 browser-newtab.toml "$HOME/.config/hyprbar/browser-newtab.toml"
```

Se `HYPRBAR_CONFIG_HOME` ou `XDG_CONFIG_HOME` estiver definido, use o
config-dir efetivo em vez de `~/.config/hyprbar`. O `input_path` do TOML é
relativo a esse diretório. O `output_path` continua sendo o caminho fixo da
extensão acima. O Hyprbar mescla os arquivos `.toml` do config-dir; este
fragmento adiciona somente `[theme.templates.user.browser_newtab]`.

Em `chrome://extensions` ou `brave://extensions`, ative o modo do
desenvolvedor, escolha **Carregar sem compactação** e selecione o caminho
absoluto da extensão (expanda `~` para sua pasta pessoal). Aceite a troca
de nova aba quando o navegador solicitar. Se outra extensão já controla a
nova aba, resolva esse conflito na interface; não edite `Preferences`.

O template será aplicado pelo fluxo normal de cores do Hyprbar. Espere a
renderização terminar antes de abrir uma nova aba. Mantenha **inalterados**
os hooks existentes de `colors_changed` para Chrome/Brave: a sincronização
continua baseada no reinício já adotado. Esta extensão não adiciona hooks,
não reinicia navegadores e não mexe em `Cached Theme.pak`.
Abas já abertas podem reter o CSS antigo até recarregar; fechar/reabrir o
navegador pelo fluxo existente elimina esse cache. O fallback permite usar
a página mesmo antes da primeira renderização.

A substituição vale para janelas normais, não para a nova aba anônima.
Relógio e data usam o fuso local e `pt-BR`. O foco inicial do navegador na
barra de endereço não é roubado; use Tab para chegar à pesquisa. Há rótulos
acessíveis, foco visível, botão de 44 px e layout responsivo sem animações.
O contraste final depende das cores fornecidas pela paleta ativa.

## Desinstalação

1. Remova **Hyprbar · Nova aba** em `chrome://extensions` e
   `brave://extensions`, em cada perfil onde foi carregada. A nova aba
   nativa volta a ser controlada pelo navegador (ou por outra extensão).
2. Remova apenas `browser-newtab.toml` e o template
   `templates/browser-newtab/palette.css.in` do config-dir efetivo. Não
   remova outros templates nem os hooks Chrome/Brave existentes.
3. Depois de remover a extensão dos perfis, apague somente
   `~/.local/share/hyprbar/extensions/newtab/` se não precisar mais dela.

Nada disso exige apagar perfis, cookies, cache de navegação ou o tema
principal. Para desativar temporariamente, use a chave da extensão na UI.

## Testes reais isolados

Dependências já instaladas: Python 3.11+, `hyprbar`, `google-chrome-stable`
e `brave-browser`. Sem pacotes Python externos. Execute na raiz do repo:

```sh
python3 -m unittest discover -s tools/browser-newtab/tests -v
python3 tools/browser-newtab/tests/probe.py
```

`probe.py` usa a pasta de extensão do repo por padrão, gera duas variantes
com o CLI real do Hyprbar, troca temporariamente **somente** `palette.css`
e restaura seus bytes em `finally`. Não execute em paralelo com um segundo
probe na mesma pasta. Aceita `--extension`, `--palette-json` e `--artifacts`.
Um encerramento forçado com SIGKILL não pode executar a restauração: nesse
caso restaure o fallback antes de continuar.

Os testes criam HOME, XDG e perfis novos no diretório temporário do Python
(respeitando `TMPDIR`), usam apenas `--remote-debugging-pipe`
e `--enable-unsafe-extension-debugging` nesses processos de teste e os
encerram ao final. Não há porta TCP de depuração nem acesso ao perfil diário.
A API CDP experimental `Extensions.loadUnpacked` precisa estar disponível
na versão instalada; falhas de API são reportadas, não substituídas por
navegação direta ao HTML. Flags de depuração **não são instruções de
instalação em produção**.

Cada Chrome/Brave recebe uma navegação real a `chrome://newtab/`. O teste
confirma a identidade da extensão, fundo computado de `html` e `body`,
altura da janela, relógio/data, CSS local, ausência de requisições remotas
da página e erros CSP/runtime, layout de 360 px, foco visível, alvo de
44 px e submissão vazia ignorada. A pesquisa real chega ao provedor padrão
(Google no Chrome e Brave Search no Brave dos perfis isolados testados),
mas é interceptada e abortada **antes** de enviar a requisição à rede.
A navegação de pesquisa intencional é separada da medição da nova aba.

A saída informa a pasta de evidências com `results.json`, eventos CDP,
CSS renderizado, logs de renderização/navegador e screenshots desktop
(1440×1000) e mobile (360×740), para os dois modos nos dois navegadores.
Teste não equivale a instalação: nenhuma instalação de produção é feita.

### Referências oficiais verificadas

- Chrome Search API: <https://developer.chrome.com/docs/extensions/reference/api/search>
  — permissão `search`, provedor padrão, `CURRENT_TAB` e retorno Promise.
- Override Chrome pages: <https://developer.chrome.com/docs/extensions/develop/ui/override-chrome-pages>
  — `chrome_url_overrides.newtab`, HTML empacotado e limitação de nova aba
  anônima. Não é necessária permissão de conteúdo para esse override.
