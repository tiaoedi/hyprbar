# hyprcalculadora — tiaoedi/calculator

Plugin nativo Luau, API 22. Motor aritmético próprio: não usa calculadora externa,
comandos, subprocessos, rede ou serviços adicionais, inclusive nas porcentagens.
Nenhum pacote adicional é necessário além do Hyprbar que executa o plugin.

Operações: +, -, *, /, parênteses, sinais, potência (^), porcentagem (%), sqrt(),
pi e ans. Aceita ponto/vírgula decimal, notação científica e operadores × ÷ −.
O campo aceita digitação; Enter calcula. Após calcular, um operador continua pelo
resultado e um dígito inicia outra conta. Ans pertence apenas a esta sessão.

Porcentagens usuais:
  100+10% = 110
  100-10% = 90
  100*10% = 10
  100/10% = 1000
Parênteses, potências e taxas encadeadas preservam a precedência observada em
148 comparações de referência registradas antes da remoção do aplicativo anterior.

Limites: ponto flutuante binário, 12 algarismos significativos na exibição;
não é aritmética financeira/decimal exata. Parser fechado, sem execução de texto
como código, até 512 caracteres, 256 tokens e 32 níveis de parênteses. Divisão
por zero, operações fora dos reais e resultados não finitos retornam erro.

Histórico: últimas 20 contas na memória da entrada do plugin, duas por página,
com Mais recentes/Mais antigas. Fechar o painel não limpa; recarregar/desabilitar
limpa. Clique numa conta para reutilizar seu resultado. Copiar só muda o clipboard
quando solicitado. O painel abre no centro da tela. Super+F7 abre/fecha.

Instalação: ~/.local/share/hyprbar/plugins/calculator.
Configuração: ~/.config/hyprbar/zzzz-calculator.toml.
Menu principal: ~/.local/share/applications/hyprcalculadora.desktop.
Um lançador legado oculto permite que favoritos antigos continuem funcionando;
ele também executa apenas o painel deste plugin, sem aplicativo externo.

  hyprbar msg plugins enable tiaoedi/calculator
  hyprbar msg panel-toggle tiaoedi/calculator:panel

Testes offline (mocks de host são distintos da verificação visual real):
  lua tests/engine.lua .
  lua tests/host_mock.lua .
  lua tests/layout.lua .
  lua tests/percentage.lua .
  lua tests/independent.lua .
  lua tests/branding.lua .
  hyprbar plugins lint .

Verificação real sob demanda:
  hyprbar msg plugin tiaoedi/calculator:panel all evaluate '100+10%'
  hyprbar msg plugin tiaoedi/calculator:panel all diagnostics
O painel precisa ter sido aberto ao menos uma vez para sua entrada estar pronta.
Diagnostics grava expressão, resultado, Ans, erro, histórico e página em
pluginDataDir()/diagnostics.json, normalmente
~/.local/state/hyprbar/plugins/data/tiaoedi/calculator/diagnostics.json.
Não salva contas automaticamente. O evento restore-session aceita um snapshot
JSON validado e limitado para preservar a sessão em uma atualização autorizada.
clear e clear-history limpam entrada e histórico, respectivamente.
