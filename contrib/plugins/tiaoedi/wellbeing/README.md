# Bem-estar — tiaoedi/wellbeing

Plugin nativo Luau para Hyprbar, API mínima **22**. Sem dependências,
subprocessos, serviços do sistema, rede ou bloqueio de tela. A entrada `service`
é apenas uma entrada interna singleton do Hyprbar, não um daemon externo.

## Recursos

- Hidratação a cada 45 minutos, olhos a cada 20, alongamento a cada 60.
- Seis configurações globais: `water_enabled`, `water_minutes`, `eyes_enabled`,
  `eyes_minutes`, `stretch_enabled`, `stretch_minutes`.
- Intervalos inteiros entre 1 e 1440 minutos. Valores numéricos finitos são
  arredondados para baixo e limitados; tipos inválidos usam o padrão.
- Coração na barra abre/fecha painel nativo em português; botão Configurações
  abre a página nativa do plugin. Rótulos das configurações: traduções pt/en.
- Registro manual de água (não representa volume), pausas concluídas, pausa/
  retomada e adiamento global de cinco minutos.
- Tempo acompanhado hoje e nesta sessão, exibido em horas, minutos e segundos.

## Tempo de uso (v1.1)

A contagem começa com esta versão; não recupera uso anterior. Mede o tempo em
que o plugin está executando e não pausado, não atividade de teclado/mouse,
tempo por aplicativo ou presença efetiva diante da tela. Pausar os lembretes
também pausa a contagem. Lacunas maiores que 120 segundos e relógio voltando
não são somados; suspensões curtas podem ser contadas pela mesma heurística.

O total de hoje é salvo localmente e zerado na mudança de data. A sessão é a
execução atual da entrada interna do plugin, reiniciando ao recarregá-la, não
necessariamente a sessão do sistema. Não guarda histórico de dias anteriores.
Na virada da data, o intervalo que cruza meia-noite não é somado ao total diário
(no tick normal isso perde até cerca de um segundo); a sessão segue acumulando.

## Instalação/ativação (não executadas por estes testes)

Diretório: `~/.local/share/hyprbar/plugins/wellbeing`.

```sh
hyprbar plugins lint ~/.local/share/hyprbar/plugins/wellbeing
hyprbar msg plugins enable tiaoedi/wellbeing
```

Adicione um widget à configuração existente, preservando os demais e incluindo
`bemestar` na lista desejada da barra:

```toml
[widget.bemestar]
type = "tiaoedi/wellbeing:wellbeing"
```

Não altera atalhos do Centro de Controle. Não exige rebuild/restart do Hyprbar.

## Arquitetura e comportamento exato

`scheduler.luau` é puro Lua/Luau; `service.luau` é a única proprietária dos
relógios, notificações e persistência. Widget e painel só consomem `state.view`;
o painel envia `{event, nonce}` por `state.request`. Não há timer por monitor.
A atualização singleton é de 1 segundo. Lembretes simultâneos geram uma única
notificação agrupada; cada lembrete fica pendente, sem repetição, até conclusão
ou adiamento. Concluir reinicia apenas seu intervalo; água também soma +1.

Pausar congela os tempos e preserva pendências. Retomar restaura os tempos
congelados; comandos pause/resume são idempotentes. Adiar limpa pendências e
rearma tudo para cinco minutos, inclusive quando pausado (contagem só avança ao
retomar). Lembretes desativados não notificam. Mudança de intervalo/ativação
reinicia somente o lembrete alterado.

Salto do relógio para trás ou lacuna **maior que 120 segundos** entre atualizações
reinicia todos os intervalos e limpa pendências, sem notificações de recuperação.
É uma heurística de suspensão, não uma assinatura do sistema: suspensão curta
pode gerar o lembrete normalmente, e atraso longo do próprio host também reinicia.

## Persistência e limites

`hyprbar.pluginDataDir()/daily.json` contém somente `{day,count,paused,usageMs}`.
Caminho observado e verificado nesta instalação:
`~/.local/state/hyprbar/plugins/data/tiaoedi/wellbeing/daily.json`.
Em outros ambientes, use o diretório retornado por `hyprbar.pluginDataDir()`;
não derive o caminho a partir da localização dos scripts. Troca diária usa a
data local, zera ao mudar de dia (sem histórico),
e limita o contador a 999. Leitura limitada a 1024 bytes. Escrita por arquivo
`.tmp` + rename, na inicialização, mudanças de data/contador/pausa, checkpoint
de cada minuto de uso e saída ordenada da entrada — não a cada segundo. Falha
é registrada no log; nova tentativa no próximo checkpoint/mudança/saída.
Uma queda abrupta pode perder até aproximadamente um minuto de contagem.
Sem fsync/garantia contra perda por queda de energia.

Timers, adiamentos e pendências não sobrevivem ao reload/restart: reiniciam com
intervalo completo; contador diário e estado pausado sobrevivem. Notificações
respeitam as regras do host (por exemplo, Não Perturbe); não há confirmação de
entrega. Não mede atividade, volume de água, duração de exercícios ou objetivos
médicos. Painel/notificações são intencionalmente em português.

## IPC para verificação real posterior

```sh
hyprbar msg panel-toggle tiaoedi/wellbeing:panel
hyprbar msg plugin tiaoedi/wellbeing:reminders all diagnostics
hyprbar msg plugin tiaoedi/wellbeing:reminders all pause
hyprbar msg plugin tiaoedi/wellbeing:reminders all resume
hyprbar msg plugin tiaoedi/wellbeing:reminders all snooze
# Registram ações reais; water altera o contador, não usar como teste reversível:
hyprbar msg plugin tiaoedi/wellbeing:reminders all water
hyprbar msg plugin tiaoedi/wellbeing:reminders all eyes
hyprbar msg plugin tiaoedi/wellbeing:reminders all stretch
```

`diagnostics` grava sob demanda `pluginDataDir()/diagnostics.json`, com o mesmo
view-model seguro publicado em `view`: data, contador, usageMs, sessionMs, paused, updatedAtMs e
`reminders.{water,eyes,stretch}.{enabled,intervalMs,pending,remainingMs}`.
Não altera o contador. Para verificar, ler esse JSON após cada comando; verificar
`paused` e os tempos, além da UI real. Diagnostics avança normalmente o relógio,
portanto pode emitir lembrete que venceu; não é um modo acelerado de teste.

## Testes offline (não integração real)

```sh
P="$HOME/.local/share/hyprbar/plugins/wellbeing"
/usr/sbin/lua "$P/tests/scheduler.lua" "$P"
/usr/sbin/lua "$P/tests/usage.lua" "$P"
/usr/sbin/lua "$P/tests/host_mock.lua" "$P"
/usr/sbin/lua "$P/tests/package.lua" "$P"
hyprbar plugins lint "$P"
```

Testes escritos em ciclos RED/GREEN, um comportamento por vez. Scheduler cobre
limites, supressão, conclusão, pausa, adiamento, saltos, virada diária e configurações
inválidas. `host_mock.lua` é **mock explícito do host** usando Lua, com armazenamento
em memória e serializador de teste (não JSON real): cobre entradas, notificações
agrupadas, dois widgets, callbacks, IPC, diagnósticos e frequência de escrita.
Não valida execução no sandbox Luau, entrega assíncrona entre VMs, aparência,
cliques nativos, entrega de notificações ou ativação na sessão real. Lint verifica
manifesto/configurações, não substitui esse teste real.
