# Plano de Implementação — temp002b

> **Fonte das alterações**: [docs/temp002_alteracoes.txt](temp002_alteracoes.txt)
>
> Este plano cobre apenas os itens **NÃO IMPLEMENTADOS**, **PARCIALMENTE IMPLEMENTADOS** ou marcados como **NÃO SEI SE FOI IMPLEMENTADO** no arquivo fonte. Itens já marcados como “ITEM IMPLEMENTADO COM SUCESSO” não estão nesta lista (mas podem ser validados de forma colateral em cada fase quando relevante).
>
> Cada **fase** trata de **um único tópico funcional** completo (UI + backend + testes). Cada **item dentro de uma fase** é redigido como um **prompt completo e autocontido** que um agente de IA pode receber sem nenhum contexto prévio e ainda assim executar o trabalho corretamente.

---

## Contexto comum (releia antes de cada fase)

> **Antes de executar qualquer prompt deste documento, leia esta seção e o [CLAUDE.md](../CLAUDE.md) na raiz do projeto.** Ela é repetida (resumida) em cada prompt para que agentes que recebam apenas o prompt isolado tenham contexto suficiente, mas a versão completa abaixo é a fonte da verdade.

### Arquitetura geral
- **Backend**: FastAPI + SQLAlchemy 2.x (SQLite em dev, PostgreSQL em produção). Entrypoint: [sistema/app/main.py](../sistema/app/main.py).
- **Modelos**: [sistema/app/models.py](../sistema/app/models.py) (`mapped_column` + `Mapped[T]`). JSON sempre como `Text`.
- **Schemas**: [sistema/app/schemas.py](../sistema/app/schemas.py) (Pydantic v2).
- **Routers principais**: [sistema/app/routers/admin.py](../sistema/app/routers/admin.py), [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py), [sistema/app/routers/twilio_callbacks.py](../sistema/app/routers/twilio_callbacks.py).
- **Services**: [sistema/app/services/accident_lifecycle.py](../sistema/app/services/accident_lifecycle.py), [sistema/app/services/accident_archive_builder.py](../sistema/app/services/accident_archive_builder.py), [sistema/app/services/accident_situation_table.py](../sistema/app/services/accident_situation_table.py), [sistema/app/services/twilio_caller.py](../sistema/app/services/twilio_caller.py), [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py) (SSE), [sistema/app/services/admin_identity.py](../sistema/app/services/admin_identity.py).
- **Front Admin (admin2)**: [sistema/app/static/admin2/app.js](../sistema/app/static/admin2/app.js), [sistema/app/static/admin2/index.html](../sistema/app/static/admin2/index.html), [sistema/app/static/admin2/styles.css](../sistema/app/static/admin2/styles.css). **Espelho de deploy**: [deploy/docker/admin2-web/](../deploy/docker/admin2-web/) — manter byte-idêntico ao `sistema/app/static/admin2/` ao terminar (ver [admin2_mirror_sync](../../.claude/projects/c--dev-projetos-checkcheck/memory/admin2_mirror_sync.md)).
- **Front Checking Web (check / “App”)**: [sistema/app/static/check/index.html](../sistema/app/static/check/index.html), [sistema/app/static/check/app.js](../sistema/app/static/check/app.js), [sistema/app/static/check/accident.js](../sistema/app/static/check/accident.js), [sistema/app/static/check/accident-camera.js](../sistema/app/static/check/accident-camera.js), [sistema/app/static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js), [sistema/app/static/check/styles.css](../sistema/app/static/check/styles.css).
- **SSE — Brokers**: `notify_admin_data_changed(reason, metadata=...)` e `notify_web_check_data_changed(reason, metadata=...)` em [sistema/app/services/admin_updates.py](../sistema/app/services/admin_updates.py). Toda mutação que afeta UI em tempo real deve disparar pelo menos um deles. Razões existentes para acidente: `accident_opened`, `accident_closed`, `accident_user_report`, `accident_acknowledged`, `accident_video_uploaded`, `emergency_call_initiated`, `emergency_call_status_update`.
- **Migrations**: pasta [alembic/versions/](../alembic/versions/). Última conhecida: `0059_add_here_api_key_to_llm_settings.py` (use o próximo número livre, **valide com `Glob alembic/versions/*.py`**).
- **Convenção de eventos**: `CheckEvent.action` é `String(16)` — manter ≤ 16 caracteres. Sempre chamar `log_event(...)` após mutações relevantes.
- **Auditoria admin**: usar `require_admin_identity` e `identity.admin_user.id` para colunas `*_by_admin_id` (FK→`admin_users.id`), nunca `User.id`. Ver bloco "Identidade de admin" no [CLAUDE.md](../CLAUDE.md).

### Convenções de UI

- **Front “check”** é JS vanilla (sem framework). Os módulos expõem objetos globais (`window.AccidentCamera`, `window.AccidentMode`, `window.CheckingWebI18n`, etc.).
- Para textos visíveis ao usuário no front check: **sempre** adicionar a chave em [i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js) seguindo o padrão `seção.subsecao.chave` e localizá-la nas 6 línguas (`pt`, `en`, `zh`, `ms`, `id`, `tl`); na ausência, o `t(key)` cai automaticamente em `pt`. Quando o agente não tiver tradução boa, deixe a chave em PT em todas as 6 línguas e marque com comentário `// TODO i18n`.
- **Front “admin2”** também é JS vanilla; textos podem ficar em português direto no código (sem i18n).
- **Não** quebrar diálogos existentes (`accidentReportConfirmDialog`, `accidentReportProjectDialog`, etc.). Reaproveite IDs/CSS.

### Como rodar e testar

- Backend: `pytest -x` na raiz para a suíte completa, ou `pytest tests/test_accident_*.py` para focar em acidente.
- Front: o backend serve os arquivos estáticos em dev — basta `uvicorn sistema.app.main:app --reload` e abrir `http://localhost:8000/admin2/` e `http://localhost:8000/check/`.
- Para verificar mudanças no XLSX/ZIP de archive, é fácil disparar manualmente: abrir um acidente em dev, registrar ao menos um vídeo, fechar o acidente, e baixar o ZIP gerado.

### Padrão dos prompts

- Cada prompt **deve ser autossuficiente**. Os agentes que executarão estes prompts não veem este documento como um todo — recebem apenas o prompt.
- Cada prompt inclui: **objetivo**, **referência ao item do `temp002_alteracoes.txt`**, **arquivos a estudar**, **arquivos a modificar**, **passos**, **anti-padrões**, **critério de aceitação** e **memória/notas para o agente**.
- Os prompts utilizam blocos `markdown` codeblocks para clareza; o agente que executa **não** deve copiar o codeblock literalmente — deve **executar** as instruções.

---

## Visão geral das fases

| Fase | Tema | Itens cobertos no temp002 |
|---|---|---|
| **1** | Diálogo “Acidente Reportado” + atualização do campo Ciência | 4.3 e 5.4.4 / 3.6 |
| **2** | Estado pós-reportagem do App (“Situação enviada” + botão emergência persistente) | 4.2.1, 4.2.2, 4.2.3 |
| **3** | Auto check-in disparado pelo modo acidente | 4.1 |
| **4** | Suporte a múltiplos acidentes simultâneos (App + Admin) | 5.1, 5.3, 4.5 |
| **5** | Descrição detalhada no wizard do App | 4.6 |
| **6** | Visibilidade do botão “Reportar Acidente” | 4.4 |
| **7** | Descrição do acidente no XLSX gerado | 2.3 |
| **8** | Numeração sequencial vitalícia + notificações padronizadas de ligação | 3.2.5 (e 5.5.1) |
| **9** | Feedback de upload de vídeo + arquivos no ZIP/XLSX | 5.2 |
| **10** | Sincronização do espelho `deploy/docker/admin2-web/` e testes de regressão finais | (transversal) |

> As fases foram ordenadas das mais isoladas para as que dependem de back-and-forth com várias áreas do sistema. **Fases 1–6** são independentes entre si e podem rodar em paralelo. **Fases 7, 8, 9** dependem de modelos e wiring de backend já estabilizados pelas anteriores. **Fase 10** é sempre a última.

---

## Fase 1 — Diálogo “Acidente Reportado” + campo Ciência (itens 4.3 e 5.4.4/3.6)

**Objetivo da fase**: garantir que, ao ativar o modo acidente, o App (Checking Web) exiba uma caixa de diálogo central com `Projeto`, `Local`, `Detalhes`, mensagem de alerta e botão `Ciente`. Ao clicar em `Ciente`, o registro do usuário na tabela `accident_user_reports` muda `awareness_status` de `waiting` para `acknowledged`, refletindo na coluna “Ciência” do admin para aquele acidente.

**Estado atual** (relevante para o agente):
- O diálogo HTML `accidentAckDialog` já existe em [sistema/app/static/check/index.html:651-670](../sistema/app/static/check/index.html#L651-L670).
- A função `showAccidentAckDialog(state)` já existe em [sistema/app/static/check/accident.js:537-564](../sistema/app/static/check/accident.js#L537-L564) e é chamada em [accident.js:62-68](../sistema/app/static/check/accident.js#L62-L68).
- O endpoint `POST /api/web/check/accident/acknowledge` já existe em [web_check.py:1011](../sistema/app/routers/web_check.py#L1011).
- A coluna `Ciência` no admin já lê `r.awareness_status` em [admin2/app.js:7194](../sistema/app/static/admin2/app.js#L7194).
- **Bug reportado pelo usuário (item 5.4.4)**: a caixa de diálogo simplesmente *não está aparecendo*. Provavelmente o gatilho (`state.awareness_status !== "acknowledged"` em [accident.js:63](../sistema/app/static/check/accident.js#L63)) só dispara quando o estado *transiciona* de inativo para ativo (`isNewAccident` check em [accident.js:64](../sistema/app/static/check/accident.js#L64)). Usuários já logados quando o admin abre o acidente recebem o evento SSE de transição, mas o diálogo precisa aparecer em *todos* os usuários do projeto, inclusive os que loguem **depois** do acidente já estar ativo.

### To-do desta fase

#### 1.1 Diagnosticar e corrigir o gatilho do diálogo `accidentAckDialog`

```
Você é um agente de IA implementando uma correção no projeto "Checking" (sistema de check-in/check-out via RFID, FastAPI + SQLite/Postgres + JS vanilla). Trabalhe a partir da raiz `c:/dev/projetos/checkcheck`.

OBJETIVO
Garantir que a caixa de diálogo "Acidente Reportado" (id=accidentAckDialog) apareça em TODOS os usuários autenticados de um projeto sempre que houver um acidente ativo cujo `awareness_status` daquele usuário seja "waiting" — incluindo:
 a) usuários já logados que recebem o SSE de "accident_opened" (transição é detectada hoje);
 b) usuários que fazem login DEPOIS do acidente já estar em curso (caso onde hoje o diálogo não aparece);
 c) reabertura de sessão / refresh da página enquanto o acidente está ativo e o usuário ainda não confirmou.

Este corrige o item 5.4.4 (parcialmente implementado de 3.6) e parte do item 4.3 do arquivo docs/temp002_alteracoes.txt.

ARQUIVOS A ESTUDAR ANTES DE EDITAR
- docs/temp002_alteracoes.txt (itens 3.6, 4.3, 5.4.4)
- CLAUDE.md (raiz) — convenções gerais e seção "Modo Acidente"
- sistema/app/static/check/accident.js — toda a lógica de modo acidente do front App
- sistema/app/static/check/index.html (linhas 651-670) — markup do diálogo accidentAckDialog
- sistema/app/static/check/app.js (procure por "AccidentMode.onLogin", "fetchWebState", "applyHistoryState")
- sistema/app/routers/web_check.py (função get_web_accident_state, ~linha 898) — confirme o payload contém `awareness_status`
- sistema/app/schemas.py (WebAccidentStateResponse) — confirme schema

ARQUIVOS A MODIFICAR
- sistema/app/static/check/accident.js (alterar a lógica em refreshState que decide quando chamar showAccidentAckDialog)
- (Se aplicável) sistema/app/static/check/i18n-dictionaries.js — adicionar/ajustar chaves se você decidir i18n-izar os textos. Reaproveite chaves existentes da seção `accident`.

PASSOS
1. Releia refreshState() em accident.js. A lógica atual exige `isNewAccident` (transição), o que faz com que usuários que carreguem a página com um acidente já ativo não recebam o diálogo.
2. Reescreva a condição para: "mostrar o diálogo SEMPRE que `state.is_active === true && state.awareness_status !== 'acknowledged' && _ackShownForAccidentId !== state.accident_id`". Mantenha o controle por `_ackShownForAccidentId` para não exibir o diálogo repetidamente dentro da mesma sessão para o mesmo acidente, MAS reseta `_ackShownForAccidentId` quando o accident_id muda OU quando o usuário desloga.
3. Após o usuário clicar em "Ciente" no diálogo, atualize `_ackShownForAccidentId = state.accident_id` (já está implícito hoje pela transição de awareness_status). Confirme via SSE que `accident_acknowledged` re-dispara `refreshState`, que vai trazer `awareness_status === 'acknowledged'` e impedir nova exibição.
4. Garanta que ao deslogar (`AccidentMode.onLogout`) o `_ackShownForAccidentId` volta para null.
5. Se o agente perceber que o `awareness_status` não está no payload `WebAccidentStateResponse` retornado pelo endpoint, adicione-o em [sistema/app/schemas.py](../sistema/app/schemas.py) (já está como `awareness_status: str | None = None` na linha 4433 — apenas valide).
6. Adicione um teste em `tests/` (use `tests/test_accident_web_state.py` ou similar) que:
   - Cria um projeto, dois usuários membros, abre um acidente como admin.
   - Faz `GET /api/web/check/accident/state?chave=...` para o usuário A — espera `is_active=true, awareness_status='waiting'`.
   - Faz `POST /api/web/check/accident/acknowledge` — espera 200.
   - Faz `GET` novamente — espera `awareness_status='acknowledged'`.
   - Para usuário B (que nunca interagiu): espera `awareness_status='waiting'`.
7. Rode `pytest -x tests/test_accident_web_state.py` (ou suite equivalente) e cole o sumário na resposta final.

ANTI-PADRÕES
- NÃO substituir a abordagem por polling — o gatilho deve ser baseado em estado, não em transição de eventos.
- NÃO mostrar o diálogo a cada `refreshState` mesmo quando o usuário já clicou "Ciente". Use `_ackShownForAccidentId` para idempotência dentro da sessão.
- NÃO mexer no markup do diálogo. Não criar um diálogo novo.

CRITÉRIO DE ACEITAÇÃO
- Abrir o admin em uma aba, abrir o check (App) em outra aba já logado. Admin abre acidente. O diálogo aparece no App imediatamente após o SSE (ou no próximo polling).
- Fazer logout no App, fazer login novamente enquanto o acidente segue ativo: o diálogo deve aparecer novamente (porque é nova sessão, awareness_status pode ser waiting ou acknowledged dependendo se já clicou antes).
- Recarregar a página do App com sessão ativa e acidente em curso: o diálogo aparece se awareness_status='waiting'.
- Coluna "Ciência" na tabela do acidente no admin reflete "Ciente" após o clique.

MEMÓRIA / NOTAS A REGISTRAR APÓS COMPLETAR
- Atualizar mentalmente: este fix expande a regra de exibição do accidentAckDialog para "any waiting + active accident" em vez de "transition only". Não há novo migration.
```

#### 1.2 Garantir que o `awareness_status` é exposto e atualizado consistentemente para múltiplos acidentes

```
Você é um agente de IA implementando uma melhoria no projeto "Checking". Trabalhe a partir da raiz `c:/dev/projetos/checkcheck`.

OBJETIVO
Ajustar o endpoint /api/web/check/accident/state para que, quando existirem múltiplos acidentes ativos (cenário introduzido pelo modelo: índice único é por projeto, então admin pode ter N acidentes simultâneos em N projetos), o front receba o awareness_status para CADA acidente do projeto do usuário, e o front exiba uma caixa "Acidente Reportado" para cada acidente que o usuário ainda não confirmou.

CONTEXTO IMPORTANTE
- O índice único em accidents é parcial e por projeto (`ix_accidents_single_active_per_project`), conforme [sistema/app/models.py:757-763](../sistema/app/models.py#L757-L763). Logo, são possíveis múltiplos acidentes simultâneos quando em projetos distintos.
- Hoje, get_web_accident_state em [routers/web_check.py:898](../sistema/app/routers/web_check.py#L898) retorna apenas UM acidente (o primeiro `matching`). Para o usuário que pertence a múltiplos projetos com múltiplos acidentes ativos, isso esconde acidentes paralelos.
- O item 4.3 do temp002_alteracoes.txt diz literalmente: "Deve haver uma caixa de diálogo para cada acidente reportado" (texto na seção 5.4.4).

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (itens 3.1, 4.3, 5.4.4)
- sistema/app/routers/web_check.py (linhas 898-940 — get_web_accident_state)
- sistema/app/schemas.py (WebAccidentStateResponse — linha 4426)
- sistema/app/static/check/accident.js (todo o módulo)
- sistema/app/services/accident_lifecycle.py (list_active_accidents)

ARQUIVOS A MODIFICAR
- sistema/app/schemas.py — criar `WebAccidentActiveItem` (id, accident_id, accident_number_label, project_name, location_name, description, awareness_status, current_user_report) e adicionar campo `active_accidents: list[WebAccidentActiveItem] = []` em `WebAccidentStateResponse`, mantendo `accident_id`, `awareness_status`, etc. populados a partir do PRIMEIRO acidente ativo (compatibilidade reversa).
- sistema/app/routers/web_check.py — refatorar get_web_accident_state para construir `active_accidents` com todos os acidentes ativos que pertencem aos projetos do usuário; manter os campos no nível raiz preenchidos a partir do primeiro acidente para não quebrar o cliente atual.
- sistema/app/static/check/accident.js — alterar refreshState para iterar sobre `state.active_accidents` e exibir uma caixa accidentAckDialog para cada acidente em que `awareness_status === 'waiting'`. Usar um Set `_ackShownForAccidentIds` em vez do escalar `_ackShownForAccidentId`. Reescrever showAccidentAckDialog para receber o item específico, e enfileirar exibições sequenciais (mostrar uma, esperar Ciente, mostrar a próxima).

ESCOPO DEFENSIVO
- Se houver apenas UM acidente ativo no projeto do usuário, o comportamento deve ser exatamente o mesmo que após a fase 1.1. Esta fase apenas adiciona suporte para 2+.
- Acknowledge é por acidente_id; o endpoint /accident/acknowledge precisa aceitar `accident_id: int | None` (None = primeiro ativo, comportamento legado).

PASSOS
1. Atualize WebAccidentStateResponse no schemas.py: adicione `active_accidents: list[WebAccidentActiveItem] = []`. Defina WebAccidentActiveItem com campos: `accident_id`, `accident_number_label`, `project_name`, `location_name`, `description`, `awareness_status`, `current_user_report`.
2. Refatore get_web_accident_state para popular tanto os campos raiz (primeiro acidente, compat) quanto active_accidents (todos os matching).
3. Adicione parâmetro opcional `accident_id: int | None = None` em WebAccidentAcknowledgeRequest.
4. Em acknowledge_web_accident, se accident_id veio no payload, use-o; caso contrário, mantenha o comportamento legado (primeiro ativo).
5. Em accident.js: substitua `_ackShownForAccidentId` (escalar) por `_ackShownForAccidentIds` (Set). Em refreshState, percorra `state.active_accidents` e exiba o diálogo para cada `awareness_status === 'waiting' && !_ackShownForAccidentIds.has(item.accident_id)`. Empilhe os diálogos: chame um por vez, e ao clicar "Ciente" envie o accident_id explicitamente no POST acknowledge, depois mostre o próximo.
6. Adicione testes para o cenário 2 acidentes simultâneos:
   - Cria 2 projetos, usuário membro de ambos, admin abre 2 acidentes.
   - GET state retorna `active_accidents` com 2 entradas.
   - POST acknowledge {accident_id: X} marca apenas X como acknowledged; o outro continua waiting.
7. Rode `pytest -x` e cole o sumário.

ANTI-PADRÕES
- NÃO remover os campos raiz (`accident_id`, `awareness_status`, etc.) de WebAccidentStateResponse — quebraria o cliente legado e os outros testes.
- NÃO mostrar 2+ diálogos sobrepostos. Sempre um por vez (queue/fila).
- NÃO fazer broadcast cego: o acknowledge deve impactar UM AccidentUserReport (chave (accident_id, user_id)).

CRITÉRIO DE ACEITAÇÃO
- Em um setup com 2 projetos e 2 acidentes ativos, o App mostra dois diálogos em sequência. Após confirmar o primeiro, o segundo aparece. Após confirmar o segundo, a UI mostra ambos os acidentes (banner/indicador) e a tabela do admin reflete "Ciente" nos dois.

MEMÓRIA / NOTAS PÓS-FASE
- Anote que o front check (App) agora trabalha com múltiplos acidentes ativos. Outras telas (botão Reportar, botão Acionar Emergência, etc.) podem precisar de adaptações em fases futuras. Mas nesta fase, somente o awareness foi adaptado.
```

---

## Fase 2 — Estado pós-reportagem no App (itens 4.2.1, 4.2.2, 4.2.3)

**Objetivo da fase**: após qualquer um dos 3 caminhos (`safety/ok`, `accident/ok`, `accident/help`), o container `accidentInquiryCard` deve mostrar a mensagem **“Situação atual enviada.”** e um botão grande **“Acionar Serviço de Emergência”** — e esse estado deve persistir até que o modo acidente seja revogado, mesmo após recarregar a página ou perder o foco.

**Estado atual**:
- A função `_showPostReportState()` em [accident.js:119-128](../sistema/app/static/check/accident.js#L119-L128) já implementa o visual correto. Ela é chamada após `askConfirm` em [accident.js:257](../sistema/app/static/check/accident.js#L257) e em `renderInquiryCard` quando `s.current_user_report` existe ([accident.js:108-110](../sistema/app/static/check/accident.js#L108-L110)).
- A queixa do usuário (item 4.2) sugere que o estado **não persiste** em todas as situações, especialmente após `accident/help` ou após reload da página, ou que o auto-trigger da chamada de emergência interfere visualmente.

### To-do desta fase

#### 2.1 Auditoria e correção da persistência do estado pós-reportagem

```
Você é um agente de IA implementando uma correção no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Garantir que, após o usuário do App (Checking Web) submeter QUALQUER reportagem de situação no modo acidente (zona+status, via os 3 caminhos abaixo), o container "Estou em" (id=accidentInquiryCard) mostre:
 - Texto: "Situação atual enviada." (id=accidentSituationSentMsg, hoje já existe)
 - Botão grande vermelho: "Acionar Serviço de Emergência" (id=accidentTriggerEmergencyButton, hoje já existe)
E esse estado deve PERMANECER até que o modo acidente seja encerrado pelo admin (ou seja, até `state.is_active === false`), MESMO QUE o usuário recarregue a página, perca conectividade temporariamente, ou faça logout/login.

Os 3 caminhos (cobrindo itens 4.2.1, 4.2.2 e 4.2.3):
 a) Zona de Segurança > Confirma  (zone=safety, status=ok)
 b) Zona de Acidente > Estou bem! > Confirma  (zone=accident, status=ok)
 c) Zona de Acidente > Preciso de Ajuda! > Confirma  (zone=accident, status=help)

Itens cobertos: 4.2.1, 4.2.2, 4.2.3 do docs/temp002_alteracoes.txt.

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (itens 4.2.1, 4.2.2, 4.2.3)
- sistema/app/static/check/accident.js (todo o arquivo, atenção em renderInquiryCard, askConfirm, _showPostReportState, _hidePostReportState)
- sistema/app/static/check/index.html (linhas 71-84 — accidentInquiryCard)
- sistema/app/static/check/styles.css (procurar accident-inquiry, accident-trigger, submit-button)
- sistema/app/routers/web_check.py (linha 898 — get_web_accident_state — para confirmar que `current_user_report` é retornado quando existe)
- sistema/app/services/accident_lifecycle.py (upsert_user_safety_report)

ARQUIVOS A MODIFICAR
- sistema/app/static/check/accident.js (predominantemente)
- (Se necessário) sistema/app/static/check/styles.css — apenas para garantir layout do post-report

PASSOS
1. Faça uma simulação manual ou leitura cuidadosa: ao confirmar safety/ok, depois recarregar a página, o GET /api/web/check/accident/state retorna `current_user_report` populado? Confirme em web_check.py — sim, retorna se o report existe. Então o problema é só de front?
2. Confirme que renderInquiryCard chama _showPostReportState quando s.current_user_report existe. Sim — linhas 108-110 de accident.js.
3. Verifique se existe alguma condição em que renderInquiryCard CHAMA resetInquiryCard SEM antes verificar current_user_report. Hoje, em accident.js linha 105, resetInquiryCard() é chamado SEMPRE que s.is_active é true. Isso BUGA o pós-reportagem: ele reseta os botões de volta para "Zona de Segurança/Zona de Acidente" e depois (linha 109) tenta chamar _showPostReportState — pode haver race ou ordem incorreta.
4. CORRIJA o fluxo de renderInquiryCard:
   - Se `s.is_active && s.current_user_report`: chamar _showPostReportState diretamente, NÃO chamar resetInquiryCard.
   - Se `s.is_active && !s.current_user_report`: chamar resetInquiryCard.
   - Se `!s.is_active`: ocultar tudo, _hidePostReportState.
5. Garanta que askConfirm, após enviar o report, chama refreshState (que vai disparar renderInquiryCard com current_user_report populado e ativar o caminho correto).
6. Para o caminho c (accident/help), confirme que o auto-trigger da chamada de emergência (linha 260-262 em askConfirm) NÃO altera nem oculta o botão `accidentTriggerEmergencyButton`. Atualmente _triggerEmergencyCall escreve em notificationLineSecondary mas não toca no card — está OK. Apenas valide.
7. Adicione um teste e2e simplificado (manual): documente os 3 caminhos no comentário do PR.
8. Adicione um teste de unidade leve (jsdom-friendly se houver setup, ou apenas em backend) para confirmar:
   - POST /api/web/check/accident/report → GET /api/web/check/accident/state retorna current_user_report.
9. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO esconder o botão de emergência após click. Ele permanece visível durante todo o modo acidente.
- NÃO fazer com que o estado depende de localStorage — ele deve refletir o backend (single source of truth).
- NÃO chamar resetInquiryCard junto com _showPostReportState — eles são mutuamente exclusivos.

CRITÉRIO DE ACEITAÇÃO
- Após cada um dos 3 caminhos:
   * "Situação atual enviada." é mostrada.
   * Botão "Acionar Serviço de Emergência" aparece.
   * Refresh da página mantém o estado.
   * Logout/login (mesmo usuário) mantém o estado (porque current_user_report está no DB).
- Quando o admin encerra o acidente, o card volta a esconder (visual de modo normal).
```

---

## Fase 3 — Auto check-in disparado pelo modo acidente (item 4.1)

**Objetivo da fase**: ao ativar o modo acidente, **se** o usuário tiver `Atividades Automáticas` marcado, **forçar uma tentativa de check-in imediato**. Se a primeira tentativa falhar por precisão insuficiente, repetir mais 2 vezes. Se as 3 falharem, **desmarcar** `Atividades Automáticas` e exibir, no container "Estou em:", a mensagem "Situação de Acidente. Realize o check-in manual IMEDIATAMENTE.". Após o check-in (manual ou automático), exibir os botões de zona normalmente. Se o usuário estiver em check-out ou em projeto diferente do projeto do acidente, ocultar o container "Estou em".

**Estado atual**:
- `window.AccidentMode.requestAutoCheckin` já existe em [check/app.js:4607](../sistema/app/static/check/app.js#L4607). Ele dispara `runLifecycleUpdateSequence`, que pode resultar em check-in se precisão for suficiente.
- Hoje, `requestAutoCheckin` é chamado apenas após o usuário clicar "Ciente" no diálogo accidentAckDialog ([accident.js:560-562](../sistema/app/static/check/accident.js#L560-L562)). Não há lógica de retentativa.

### To-do desta fase

#### 3.1 Implementar a sequência de auto check-in (3 tentativas) com fallback de mensagem

```
Você é um agente de IA implementando uma melhoria no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Implementar o item 4.1 do docs/temp002_alteracoes.txt: quando o modo acidente é ativado no App (Checking Web) e a checkbox "Atividades Automáticas" (id=automaticActivitiesToggle) está marcada, executar até 3 tentativas de check-in automático. Se as 3 falharem por precisão GPS insuficiente, desmarcar a checkbox e exibir a mensagem "Situação de Acidente. Realize o check-in manual IMEDIATAMENTE." dentro do container "Estou em:". Após qualquer check-in bem-sucedido (auto ou manual), o container volta ao fluxo normal mostrando "Zona de Segurança / Zona de Acidente". Se o usuário estiver em check-out OU se o check-in atual do usuário for em projeto diferente do projeto do acidente, ocultar o container accidentInquiryCard inteiramente (mantendo apenas o tema de acidente ligado no resto da UI).

ARQUIVOS A ESTUDAR ANTES DE EDITAR
- docs/temp002_alteracoes.txt (item 4.1)
- CLAUDE.md (raiz)
- sistema/app/static/check/accident.js (todo)
- sistema/app/static/check/app.js (procurar por: requestAutoCheckin, runLifecycleUpdateSequence, latestHistoryState, AccidentMode.onCheckWebState, isAutomaticActivitiesEnabled, automaticActivitiesToggle)
- sistema/app/static/check/index.html (accidentInquiryCard linhas 71-84, automaticActivitiesToggle linha 183)
- sistema/app/services/accident_lifecycle.py (open_accident — para entender que cada acidente está vinculado a UM project_id)
- sistema/app/routers/web_check.py (get_web_accident_state — confirme que retorna project_id no payload, se NÃO retorna, adicione)

ARQUIVOS A MODIFICAR
- sistema/app/schemas.py — WebAccidentStateResponse: garantir que `project_id: int | None = None` está presente. Se não estiver, adicione-o e popule em get_web_accident_state.
- sistema/app/routers/web_check.py — popular `project_id` no WebAccidentStateResponse e (se você implementou a fase 1.2 antes) em cada item de active_accidents.
- sistema/app/static/check/accident.js — adicionar lógica de auto check-in com 3 retries.
- sistema/app/static/check/app.js — expor uma função `window.AccidentMode.requestAutoCheckinWithRetries(maxAttempts)` que retorna uma Promise<bool> (true=conseguiu, false=falhou após N tentativas). Aproveite runLifecycleUpdateSequence + a leitura de payload.location.accuracy. Sinalize falha quando o GPS retornar precisão acima do threshold após `maxAttempts` tentativas.
- sistema/app/static/check/i18n-dictionaries.js — adicionar chave `accident.fallback.manualCheckin` com a string "Situação de Acidente. Realize o check-in manual IMEDIATAMENTE." em todas as 6 linguas (ou em pt apenas com TODO i18n para as outras).
- (Se necessário) sistema/app/static/check/styles.css — pequenos ajustes visuais para a mensagem dentro do accidentInquiryCard (texto destacado em vermelho).

PASSOS
1. Em app.js, adicione `window.AccidentMode.requestAutoCheckinWithRetries = async function (maxAttempts = 3) {...}`. Internamente:
   - Para até maxAttempts: chama runLifecycleUpdateSequence({ suppressStatus: true, triggerSource: 'accident-auto-checkin' }).
   - Após cada tentativa, lê latestHistoryState. Se o estado refletir um check-in recente (last_checkin_at > start_time da função), retorna true.
   - Se não houve check-in após maxAttempts, retorna false.
   - O wait entre tentativas: 1.5s (suficiente para uma nova captura de GPS, sem travar a UI).
   - Sinalize via setStatus quando estiver tentando (ex: "Tentativa 2 de 3...").
2. Em accident.js, dentro de refreshState (ou logo após showAccidentAckDialog, dependendo do fluxo da fase 1), implemente:
   - Se s.is_active && o usuário pertence ao projeto do acidente (s.project_id está nos projetos do usuário — pode usar o webState.user_projects ou similar):
     a) Se o usuário NÃO está em check-in OU está em check-in em projeto diferente: ocultar accidentInquiryCard e _hidePostReportState. Não tentar auto check-in. Apenas exibir o tema.
     b) Se o usuário ESTÁ em check-in no projeto correto: prossiga com renderInquiryCard normal.
     c) Se o usuário NÃO está em check-in mas PERTENCE ao projeto do acidente e está com Atividades Automáticas marcado: dispare requestAutoCheckinWithRetries(3). Se true, accidente prossegue normal (refresh state vai re-renderizar). Se false: desmarque a checkbox, atualize a UI ("Atividades Automáticas" passa a unchecked), e dentro do accidentInquiryCard substitua o conteúdo (esconda os botões Zona de Segurança/Zona de Acidente) e mostre a mensagem `Situação de Acidente. Realize o check-in manual IMEDIATAMENTE.` Após o usuário fazer check-in manual (pela própria UI do app), o container volta ao normal (no próximo refreshState).
3. CUIDADO: a função AccidentMode.onLogin já chama refreshState. A lógica de auto check-in só deve disparar UMA vez por acidente (use _autoCheckinAttemptedForAccidentId para guardar). Caso contrário, a cada refresh você fica em loop tentando.
4. Adicione um teste backend confirmando que get_web_accident_state retorna project_id corretamente.
5. Adicione documentação na função (1 linha) explicando o comportamento.
6. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO bloquear a UI durante os retries (use Promises, não async loops síncronos).
- NÃO desmarcar Atividades Automáticas se o usuário já está em check-in.
- NÃO tentar check-in se o usuário não tem permissão de geolocalização (gpsLocationPermissionGranted=false). Nesse caso, fallback direto para mensagem de check-in manual.
- NÃO tentar auto check-in se o usuário não pertence ao projeto do acidente.

CRITÉRIO DE ACEITAÇÃO
- Cenário 1: usuário em check-out, GPS preciso, atividade automática ON → após admin abrir acidente, App tenta check-in. Sucesso na 1ª tentativa, card mostra botões de zona.
- Cenário 2: usuário em check-out, GPS impreciso, atividade automática ON → 3 tentativas falham, checkbox desmarcada, card mostra mensagem em vermelho "Situação de Acidente. Realize o check-in manual IMEDIATAMENTE."
- Cenário 3: usuário em check-in no projeto certo, atividade automática ON ou OFF → fluxo normal (card mostra botões de zona).
- Cenário 4: usuário em check-in mas em projeto diferente do acidente → card oculto, só tema acidente ligado.
- Cenário 5: usuário desmarca atividade automática manualmente → não dispara retries.
```

---

## Fase 4 — Múltiplos acidentes simultâneos (itens 5.1, 5.3, 4.5)

**Objetivo da fase**: corrigir os bugs reportados de que, após encerrar um acidente, o admin não consegue iniciar outro sem refresh, e que durante um acidente ativo o botão "Confirmar" do wizard (admin) e do App fica desabilitado. Garantir que `Reportar Novo Acidente` no App esteja sempre habilitado durante modo acidente, igual ao admin.

**Estado atual**:
- O modelo `Accident` já permite múltiplos ativos via índice parcial **por projeto** ([models.py:757-763](../sistema/app/models.py#L757-L763)).
- O endpoint `POST /api/admin/accidents/open` levanta 409 se já existe acidente ativo **no mesmo projeto** (correto).
- Existe um bug no front admin onde o estado `accidentState.is_active` não é atualizado após `submitAccidentClose` antes de o usuário tentar abrir outro acidente. O botão Confirmar do wizard chama `submitAccidentOpen` (linha 7453). Ele já chama `fetchAccidentState` ao final, mas se o usuário JÁ está no wizard preenchendo enquanto outro admin fechou um acidente, o `_currentEmergencyProjectId` pode estar stale.
- O front App (check) tem `accidentReportButton` que durante acidente ativo abre `accidentActionsDialog` ([accident.js:606](../sistema/app/static/check/accident.js#L606)) com um botão `accidentActionsNewButton` ("Reportar Novo Acidente") — esse já chama `openAccidentWizard`. Mas o wizard depois cai em `accidentReportConfirmDialog` e seu botão `accidentReportConfirmSubmit` pode estar disabled em algum estado.

### To-do desta fase

#### 4.1 Reproduzir e corrigir o bug do botão Confirmar (admin) ao abrir acidente após encerrar outro

```
Você é um agente de IA corrigindo um bug no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

BUG REPORTADO (item 5.1 e 5.3 do docs/temp002_alteracoes.txt)
"Encerrei um acidente e tentei iniciar outro acidente através do website do administrador. O botão 'Confirma' estava desabilitado e só me permitiu iniciar um acidente depois que atualizei o website. Um administrador deve ser capaz de acionar acidentes simultâneos."
"Durante o modo acidente, tentei iniciar a reportagem de um segundo acidente simultâneo. ... Cheguei no widget 'Confirmação de Acidente' e o botão 'Confirmar' está desabilitado. Deveria estar habilitado para a criação de um novo acidente, abrindo uma nova aba 'Acidente <projeto>-<numero>'."

OBJETIVO
1. Reproduzir o bug com um teste e isolar a causa raiz.
2. Corrigir o estado do botão "Confirmar" em accidentWizardConfirmModal no admin para que ele NUNCA fique disabled após o wizard ser percorrido completamente. O único caso em que pode ficar disabled é DURANTE a submissão (entre o clique e a resposta do POST).
3. Idem para o front App (check): o botão accidentReportConfirmSubmit deve poder confirmar a abertura mesmo se já existe outro acidente em curso (em outro projeto). O 409 do backend só dispara se já existir acidente no MESMO projeto.

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (itens 5.1, 5.3, 4.5)
- sistema/app/static/admin2/app.js (procurar: submitAccidentOpen, accidentWizardConfirmSubmit, scheduleAccidentRefresh, openAccidentWizard)
- sistema/app/static/admin2/index.html (linhas ~822-832 — accidentWizardConfirmModal)
- sistema/app/static/check/accident.js (advanceWizardToConfirm, advanceWizardToSituation, abertura via accidentReportConfirmSubmit)
- sistema/app/static/check/index.html (linhas ~777-796 — accidentReportConfirmDialog)
- sistema/app/services/accident_lifecycle.py (open_accident — restrição existing por project_id)
- sistema/app/routers/admin.py (linha ~2060 — open_admin_accident)
- sistema/app/routers/web_check.py (linha ~941 — open_web_accident)

ARQUIVOS A MODIFICAR
- sistema/app/static/admin2/app.js
- sistema/app/static/check/accident.js
- (Se aplicável) sistema/app/static/admin2/index.html — apenas se o atributo `disabled` estiver hardcoded no HTML.

PASSOS DE DIAGNÓSTICO
1. Em admin2/app.js, leia submitAccidentOpen (linha ~7453). Observe `if (submitBtn) submitBtn.disabled = false;` apenas em casos de erro. Quando o POST sucede, _hideAccidentModal é chamado, e o botão fica com disabled=true do clique anterior (linha onde foi seteado, se aplicável). Procure por onde o botão é desabilitado.
2. Em scheduleAccidentRefresh (linha ~7705), quando wasActive && !is_active (acidente foi encerrado), ele recarrega o histórico, mas não reseta o estado do botão accidentWizardConfirmSubmit do próximo wizard.
3. A causa raiz mais provável: submitAccidentOpen seteia `submitBtn.disabled = true` no início e só re-habilita em caso de erro; em caso de sucesso, o modal é escondido (_hideAccidentModal) mas o disabled fica nele. Na próxima abertura do wizard, o botão vem disabled.

CORREÇÃO
4. Em submitAccidentOpen, no início do try, garantir `submitBtn.disabled = true`. Em todos os return paths (incluindo o de sucesso), re-habilite o botão antes do _hideAccidentModal. Use try/finally para ter certeza.
5. Em openAccidentWizard (linha 7331), no início, force o reset:
   - `document.getElementById("accidentWizardConfirmSubmit").disabled = false;`
   - `document.getElementById("accidentWizardLocationAdvance").disabled = true;`
   - `document.getElementById("accidentWizardProjectAdvance").disabled = true;`
   - `document.getElementById("accidentWizardDescriptionAdvance").disabled = false;`
6. Em accident.js (front check), faça revisão equivalente para accidentReportConfirmSubmit em advanceWizardToConfirm (linha ~449). Hoje a função NÃO desabilita o botão antes do clique, mas após o POST (linhas 471-498) ela pode ficar em estado intermediário se ocorrer erro. Reset o disabled no início de openAccidentWizard (linha 270).
7. Adicione testes:
   - Teste e2e (backend): admin cria projeto A, abre acidente em A, fecha, abre acidente em A de novo. Espera 200, espera os dois acidentes serem listados (um closed, um active). 
   - Teste e2e (backend): admin cria projetos A e B. Abre acidente em A. Abre acidente em B sem fechar A. Espera 200 (ambos abertos simultaneamente).
8. Rode `pytest -x`.

PEDIDO COMPLEMENTAR (item 4.5)
9. No App (check), o botão "Reportar Novo Acidente" (id=accidentActionsNewButton, dentro de accidentActionsDialog) já existe. Confirme que ele sempre está habilitado quando o usuário abre actions dialog. Não desabilite.
10. Aproveite para validar: no fluxo do App, após o usuário abrir um segundo acidente (em outro projeto), o accident.js deve voltar a mostrar o accidentReportButton com texto "Acidente Reportado" e re-renderizar o accidentInquiryCard. Se você terminou a fase 1.2, isso já está preparado.

ANTI-PADRÕES
- NÃO desabilitar o botão Confirmar permanentemente. Ele só pode ficar disabled durante o clique (ms).
- NÃO assumir que existe apenas um acidente ativo no sistema. O índice é por project_id, não global.
- NÃO criar lógica de retry no front para 409 — exibir a mensagem retornada pelo backend ("Já existe um acidente ativo neste projeto.").

CRITÉRIO DE ACEITAÇÃO
- Admin fecha acidente A. Sem refresh, abre wizard de novo, escolhe projeto A novamente, prossegue até Confirmar. O botão está enabled. Click → 200. Aparece o novo acidente.
- Admin abre wizard em outro projeto B enquanto A está ativo. Botão Confirmar enabled. Click → 200. Lista de active_accidents passa a ter 2 itens.
- App, durante modo acidente, abre Acidente > Reportar Novo Acidente, escolhe outro projeto, prossegue. Botão Confirmar enabled. Click → 200.

MEMÓRIA / NOTAS PÓS-FASE
- Lembre que o índice é parcial por projeto. Os agentes futuros podem se confundir e tentar globalizar.
```

---

## Fase 5 — Descrição detalhada no wizard do App (item 4.6)

**Objetivo da fase**: incluir, no fluxo do wizard do App de reportar acidente, um widget **“Descrição Detalhada”** com `<textarea maxlength=500>` e botões `Cancelar` / `Avançar`, entre o widget "Local" e o widget "Sua Situação".

**Estado atual**:
- O widget HTML `accidentReportDescriptionDialog` já existe em [check/index.html:720-742](../sistema/app/static/check/index.html#L720-L742). 
- A função `advanceWizardToDescription` em [accident.js:402-423](../sistema/app/static/check/accident.js#L402-L423) já existe e é chamada pelo botão "Avançar" do step Local.
- A descrição é incluída no POST em [accident.js:485](../sistema/app/static/check/accident.js#L485).
- O backend já aceita `description` em `WebAccidentOpenRequest` ([schemas.py:4437-4464](../sistema/app/schemas.py#L4437-L4464)) e em `AdminAccidentOpenRequest`.

**Conclusão**: o item 4.6 **já parece implementado**, mas o usuário marcou como **não implementado**. Vale uma re-validação criteriosa — talvez haja um bug visual ou de fluxo que faz o passo ser pulado.

### To-do desta fase

#### 5.1 Re-validar o fluxo do wizard do App (Descrição Detalhada) e corrigir gaps

```
Você é um agente de IA validando e corrigindo um fluxo no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Validar e, se necessário, corrigir o fluxo do wizard de reportagem de acidente no App (Checking Web) conforme o item 4.6 do docs/temp002_alteracoes.txt: após o usuário escolher Projeto > Local, o widget "Descrição Detalhada" (textarea maxlength=500 + botões Cancelar e Avançar) DEVE aparecer antes do widget "Sua Situação". Após a confirmação, o container "Estou em" do App deve mostrar "Situação atual enviada." e o botão "Acionar Serviço de Emergência" (idem fase 2). A tabela no admin deve receber o registro.

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (item 4.6)
- sistema/app/static/check/accident.js (todo, atenção em openAccidentWizard, advanceWizardToLocations, advanceWizardToDescription, advanceWizardToSituation, advanceWizardToConfirm)
- sistema/app/static/check/index.html (linhas 672-796 — todos os accidentReport*Dialog)
- sistema/app/schemas.py (WebAccidentOpenRequest)
- sistema/app/routers/web_check.py (open_web_accident)

ARQUIVOS A MODIFICAR (provavelmente nenhum, ou apenas pequenos ajustes)
- sistema/app/static/check/accident.js
- (Se necessário) sistema/app/static/check/i18n-dictionaries.js

PASSOS
1. Faça uma leitura completa do fluxo: clique no botão Reportar Acidente (linha 605) → state.is_active=false → openAccidentWizard → advanceWizardToLocations → advanceWizardToDescription → advanceWizardToSituation → advanceWizardToConfirm → submit. Confirme cada chamada.
2. Validar manualmente (ou via inspeção do DOM): a sequência é renderizada na ordem correta? O backdrop do step anterior é fechado quando o seguinte abre?
3. Verifique se `accidentReportDescriptionDialog` aparece quando o usuário clica em Avançar no step de Local. Em advanceWizardToDescription, a checagem `if (!descDialog) { advanceWizardToSituation(prevDialog, prevBackdrop); return; }` pode estar pulando o step se o ID não bater. Confirme que o ID accidentReportDescriptionDialog existe e está no index.html.
4. Se tudo estiver OK no código mas o usuário ainda relatar que o passo não aparece, é possível que:
   - O cliente tenha cache JS desatualizado (não é problema de código).
   - O accidentReportDescriptionDialog esteja invisível por CSS (.is-hidden ou display:none herdado). Verifique styles.css.
5. Adicione um teste backend e2e que:
   - Faz login web, abre acidente com description='Texto longo de teste, com acentuação áéíóú', confirma persistência no DB (Accident.description == 'Texto longo de teste, com acentuação áéíóú').
6. Adicione um log temporário (console.debug) no front para confirmar que o step de descrição é exibido. Se confirmar via inspeção, remova os console.debug antes de fechar.
7. Reescreva (se necessário) a função advanceWizardToDescription para ser mais defensiva: SEMPRE exibir o diálogo, NUNCA fazer fallback silencioso para situation. Se o diálogo não existir no DOM, lance um erro explícito no console (failhard).
8. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO pular o step de descrição mesmo que a textarea esteja vazia (é opcional, mas o widget DEVE aparecer).
- NÃO permitir mais de 500 caracteres — o maxlength=500 já garante no front; valide no backend também (Field(max_length=500) já presente).

CRITÉRIO DE ACEITAÇÃO
- Reportar Acidente no App passa pelos 4 widgets em ordem: Projeto → Local → Descrição Detalhada → Sua Situação → Confirmação.
- A descrição (mesmo vazia) é enviada no POST /api/web/check/accident/open.
- Aparece na tabela do admin (coluna Descrição, se a fase 2.2 / 2.3 do temp002 já foi feita).
```

---

## Fase 6 — Visibilidade do botão “Reportar Acidente” (item 4.4)

**Objetivo da fase**: o botão `accidentReportButton` no App só deve aparecer se **a última atividade do usuário foi um check-in NA DATA ATUAL** (timezone do projeto). Durante o modo acidente, o botão deve aparecer mesmo assim para permitir reportar OUTRO acidente.

**Estado atual**:
- `_canReportAccident` em [accident.js:170](../sistema/app/static/check/accident.js#L170) já incorpora a regra "has_current_day_checkin && current_action === 'checkin'".
- `_applyReportButtonVisibility` em [accident.js:167-171](../sistema/app/static/check/accident.js#L167-L171) prioriza `state.is_active` (sempre mostra durante acidente).
- A função `AccidentMode.onCheckWebState` é chamada por [check/app.js:5907-5910](../sistema/app/static/check/app.js#L5907-L5910).
- O usuário marcou como "NÃO SEI SE FOI IMPLEMENTADO" porque não conseguiu testar simulando um usuário que tenha feito check-in há mais de 1 dia.

### To-do desta fase

#### 6.1 Validar `has_current_day_checkin` e cobrir o cenário "check-in foi ontem"

```
Você é um agente de IA validando uma regra de negócio no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Validar que o botão "Reportar Acidente" no App (Checking Web) atende rigorosamente o item 4.4 do docs/temp002_alteracoes.txt: ele permanece OCULTO se a última atividade do usuário não for um check-in NA DATA ATUAL (na timezone do projeto). Durante um modo acidente ativo, ele DEVE aparecer (para permitir "Reportar Outro Acidente"). Como o usuário não conseguiu testar manualmente, escreva testes automatizados que cobrem esses cenários.

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (item 4.4)
- sistema/app/static/check/accident.js (linhas 166-171, 687-692)
- sistema/app/static/check/app.js (procurar por: has_current_day_checkin, current_action, WebCheckStateResponse, /api/web/check/state)
- sistema/app/routers/web_check.py (procurar pelo endpoint /api/web/check/state — definição de has_current_day_checkin)
- sistema/app/schemas.py (procure WebCheckStateResponse — confirme o campo has_current_day_checkin)
- sistema/app/services/time_utils.py (now_sgt, conversão para timezone do projeto)

ARQUIVOS A MODIFICAR
- (Se necessário) sistema/app/routers/web_check.py — corrigir o cálculo de has_current_day_checkin se ele estiver usando timezone errado.
- sistema/app/static/check/accident.js — apenas comentários explicativos, se precisar.
- tests/ — novo arquivo de teste.

PASSOS
1. Localize a definição de `has_current_day_checkin` no backend (provavelmente em web_check.py). Confirme que ele:
   - Usa a timezone do projeto ATIVO do usuário (User.projeto) para determinar o "hoje".
   - Retorna true APENAS se a data do último check-in (em timezone do projeto) for igual à data atual.
2. Se a regra está usando UTC ou timezone do servidor, CORRIJA para usar a timezone do projeto. Crie helper se necessário em time_utils.py.
3. Escreva testes para o endpoint /api/web/check/state cobrindo:
   - Usuário fez check-in HOJE. Esperado: has_current_day_checkin=true.
   - Usuário fez check-in ONTEM. Esperado: has_current_day_checkin=false.
   - Usuário em check-out (mesmo que hoje). Esperado: has_current_day_checkin=true (porque houve check-in hoje antes do check-out)? — Releia o item 4.4: "a última atividade do usuário não for um check-in na data atual". Então check-in ontem + check-out hoje = última atividade não é check-in → false. Check-in hoje + check-out hoje = última atividade é check-out → false. Check-in hoje (sem check-out depois) = última atividade é check-in → true.
   - Usuário em projeto X com timezone +08, fez check-in às 22h UTC (que é 06h do dia seguinte no projeto): a data do projeto é a do dia seguinte, então mesmo que UTC ainda esteja no "dia anterior", o backend deve considerar o checkin como "hoje".
4. Escreva também um teste para a interação entre _canReportAccident e accidentReportButton.hidden no front (use jsdom se já tiver setup, senão documente o cenário no PR).
5. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO usar UTC para determinar "hoje" — sempre usar a timezone do projeto.
- NÃO confundir "última atividade" com "checkin == true em User.checkin": a regra é sobre o último evento de check-in, não o estado de boolean.

CRITÉRIO DE ACEITAÇÃO
- Testes cobrem os 4 cenários acima e passam.
- Durante modo acidente, o botão Reportar Acidente aparece independentemente de _canReportAccident (já implementado em _applyReportButtonVisibility).
- Em modo normal, botão oculto se a regra não bate.
```

---

## Fase 7 — Descrição detalhada no XLSX gerado (item 2.3)

**Objetivo da fase**: garantir que o arquivo XLSX gerado no encerramento de um acidente contém a descrição detalhada escrita pelo administrador/usuário ao criar o acidente.

**Estado atual**:
- `accident_archive_builder.py` já inclui `f"Descrição: {accident.description or '(sem descrição)'}"` na linha 79.
- Isso atende o item 2.3.
- O usuário marcou como "NÃO SEI SE FOI IMPLEMENTADO" — provavelmente porque não baixou ou conferiu o ZIP recente.

### To-do desta fase

#### 7.1 Validar a presença da descrição no XLSX e adicionar teste

```
Você é um agente de IA validando uma funcionalidade no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Validar que o item 2.3 do docs/temp002_alteracoes.txt está implementado: o XLSX gerado quando um acidente é encerrado contém a descrição detalhada (campo Accident.description) escrita pelo responsável por registrar o acidente. Escrever um teste automatizado que confirma isso.

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (item 2.3)
- sistema/app/services/accident_archive_builder.py (toda)
- sistema/app/models.py (Accident — confirme description: Mapped[str])
- sistema/app/services/accident_lifecycle.py (open_accident, close_accident)
- tests/ — procure por test_accident_archive*.py para reaproveitar fixtures

ARQUIVOS A MODIFICAR
- tests/test_accident_archive_xlsx.py (novo ou aumentar existente)
- (Se a descrição NÃO estiver no XLSX) sistema/app/services/accident_archive_builder.py — adicione.

PASSOS
1. Leia _build_xlsx em accident_archive_builder.py. Confirme que header_rows (linha ~74) inclui a entrada "Descrição".
2. Escreva um teste que:
   - Cria projeto, usuário, abre acidente via admin com description="Descrição com acentuação áéíóú e emoji 🚨".
   - Fecha o acidente.
   - Dispara build_and_attach_archive_for_accident manualmente (ou aguarda o background task).
   - Baixa o XLSX do storage local (object_storage em dev usa _local_root).
   - Abre o XLSX com openpyxl e verifica que a célula A5 (ou onde quer que esteja a descrição) contém o texto exato.
   - Verifica também que o arquivo zip foi gerado em accidents/<label>/archive/<label>.zip.
3. Adicione asserts para validar que o emoji e os acentos sobrevivem (UTF-8 corretamente).
4. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO modificar a estrutura do XLSX existente (colunas A-K na tabela de pessoal devem permanecer iguais — definição em COLUMN_ORDER).
- NÃO assumir paths absolutos no teste; use tmp_path ou variáveis de ambiente.

CRITÉRIO DE ACEITAÇÃO
- Teste passa. A descrição (com acentos e emoji) está presente no XLSX gerado.
- Em produção (DO Spaces), o XLSX baixado pelo admin contém a descrição.
```

---

## Fase 8 — Numeração sequencial vitalícia + notificações padronizadas (itens 3.2.5 e 5.5.1)

**Objetivo da fase**: implementar a barra de notificação persistente do botão "Acionar Serviço Local de Emergência" no admin, mostrando mensagens padronizadas com **número sequencial vitalício de 6 dígitos** que nunca reseta. Inclui notificações de: chamada solicitada, sendo completada, atendida, finalizada pelo receptor/sistema. Se o Twilio não retornar callbacks, ao menos a mensagem "foi solicitada com sucesso" deve aparecer.

**Estado atual**:
- O modelo `AccidentCallLog` já existe ([models.py:878-908](../sistema/app/models.py#L878-L908)) com `call_number` (numérico) e `_next_call_number` em [twilio_caller.py:115-119](../sistema/app/services/twilio_caller.py#L115-L119) já calcula `max(call_number) + 1`.
- Callbacks de status já são gravados ([twilio_callbacks.py](../sistema/app/routers/twilio_callbacks.py)) e disparam SSE `emergency_call_status_update`.
- O front admin tem `_handleEmergencyCallUpdate` ([admin2/app.js:7689-7702](../sistema/app/static/admin2/app.js#L7689-L7702)) que atualiza `emergencyNotif-<accidentId>`, mas a mensagem **não segue o padrão** descrito no item 3.2.5.
- Falta:
  - Padronização do texto (data/hora exata, número 6 dígitos zero-padded, nome do admin e chave, etc.).
  - O número sequencial vitalício já existe (call_number) mas não está formatado consistentemente em 6 dígitos em todos os lugares.
  - Histórico persistente das notificações na UI do admin (`emergency-history-button` já existe).
  - O fallback `Foi solicitada com sucesso` quando o Twilio SDK não está instalado / não há callback configurado.

### To-do desta fase

#### 8.1 Definir o formato canônico das notificações e o número de chamada vitalício

```
Você é um agente de IA implementando uma melhoria no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Padronizar TODAS as notificações da barra "Acionar Serviço Local de Emergência" no admin (item 3.2.5 do docs/temp002_alteracoes.txt) com o seguinte formato:

(dd/mm/yyyy hh:mm:ss) Ligação <NNNNNN> solicitada por <nome do admin (chave)>, através do website do administrador, para o projeto <projeto>.
(dd/mm/yyyy hh:mm:ss) A ligação <NNNNNN> está sendo completada.
(dd/mm/yyyy hh:mm:ss) A ligação <NNNNNN> foi atendida.
(dd/mm/yyyy hh:mm:ss) A ligação <NNNNNN> foi finalizada pelo receptor. Duração total: <S> segundos.
(dd/mm/yyyy hh:mm:ss) A ligação <NNNNNN> foi finalizada pelo sistema. Duração total: <S> segundos.

NNNNNN = número de 6 dígitos zero-padded, sequencial GLOBAL E VITALÍCIO (NUNCA reseta entre acidentes nem entre fechamentos). Já existe em AccidentCallLog.call_number; apenas formate consistentemente. dd/mm/yyyy hh:mm:ss em timezone do projeto.

Quando o Twilio NÃO retornar callbacks de status (porque o SDK não está instalado em dev OU porque o public_base_url não está configurado), emita pelo menos UMA notificação "(dd/mm/yyyy hh:mm:ss) A ligação NNNNNN foi solicitada com sucesso." (item 5.5.1).

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (itens 3.2.5, 5.5.1)
- sistema/app/services/twilio_caller.py (make_emergency_call, _next_call_number)
- sistema/app/routers/twilio_callbacks.py (callback handler)
- sistema/app/routers/admin.py (trigger_admin_emergency_call linha ~2162)
- sistema/app/static/admin2/app.js (_triggerEmergencyCall linha ~7650, _handleEmergencyCallUpdate linha ~7689)
- sistema/app/services/admin_updates.py (notify_admin_data_changed)
- sistema/app/schemas.py (EmergencyCallResponse, AccidentCallLogRow)
- sistema/app/services/time_utils.py
- sistema/app/models.py (AccidentCallLog.call_status — valores permitidos: queued, initiated, ringing, in-progress, completed, failed, busy, no-answer, canceled)

ARQUIVOS A MODIFICAR
- sistema/app/services/twilio_caller.py — confirmar formato 6-dígitos no metadata SSE.
- sistema/app/routers/twilio_callbacks.py — emitir SSE com metadata enriquecida (call_number_label, status_event, started_at, ended_at se aplicável, ended_by se aplicável, duration_seconds).
- sistema/app/services/admin_updates.py — adicionar helper de formatação se necessário (não obrigatório).
- sistema/app/static/admin2/app.js — implementar `_buildNotificationLine(event, log)` que retorna a string padronizada em pt-BR. Atualizar _handleEmergencyCallUpdate para empilhar (não substituir) notificações na barra emergencyNotif-<accidentId>. Adicionar ao histórico (_openEmergencyCallHistory).

PASSOS
1. Releia _next_call_number em twilio_caller.py. Ele calcula max+1 globalmente, OK. Não há lógica de reset por acidente.
2. Em make_emergency_call, ao criar AccidentCallLog, garante que a notificação inicial via notify_admin_data_changed inclua todo o metadata necessário: { call_number, call_number_label (6 dígitos), accident_id, project_id, project_name, triggered_by_name, triggered_by_chave, triggered_by_role ('admin'|'user'), call_status, created_at_iso }.
3. Quando o Twilio SDK não está instalado (ImportError em twilio_caller.py linha ~217), o AccidentCallLog é salvo com call_status='failed'. CASO O CALLBACK NÃO SEJA POSSÍVEL POR FALTA DE public_base_url ou SDK ausente, mude para call_status='queued' (já está) e dispare uma notificação SSE com event='requested' (uma label custom). Essa será o fallback do item 5.5.1.
4. Em twilio_callbacks.py, quando o callback chega, dispare SSE com event mapeado:
   - initiated → "está sendo completada"
   - ringing → ignorar (não pedido) ou notificar como variação. Por simplicidade, mapear como "está sendo completada".
   - in-progress → "foi atendida"
   - completed → "foi finalizada pelo sistema, duração X". Se Twilio Voice indicar quem desligou (`CompletedBy` ou inferência), use receiver vs system; por agora, padrão = system.
   - failed/busy/no-answer/canceled → enviar mensagem de erro de variação.
5. No front admin: substitua `emergencyNotif-<id>` por um container que acumula linhas (HTML lista <ul>). Cada linha é renderizada com _buildNotificationLine. Mantenha um buffer em memória `_emergencyNotifications: Map<accidentId, Array<string>>` para sobreviver a re-renders parciais. O histórico (_openEmergencyCallHistory) deve listar as notificações da chamada, ordenadas por created_at.
6. Para o item 5.5.1: ao receber o evento SSE 'emergency_call_initiated' (já existe), se nunca houver callback subsequente (timeout 30s), continue com a notificação "(timestamp) A ligação NNNNNN foi solicitada com sucesso." Adicione esse timeout no front.
7. Escreva testes:
   - Backend: make_emergency_call sem SDK instalado → AccidentCallLog criado, notify_admin_data_changed disparado com call_number_label de 6 dígitos.
   - Backend: callback Twilio "completed" → AccidentCallLog.call_status='completed', duration_seconds preenchido, notify_admin_data_changed disparado.
   - Frontend (jsdom se setup permite, senão pulando): _buildNotificationLine retorna string correta para cada event.
8. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO resetar call_number entre acidentes. É um contador GLOBAL VITALÍCIO.
- NÃO formatar com menos de 6 dígitos. Sempre zfill(6).
- NÃO sobrescrever notificações antigas no front. Empilhar.

CRITÉRIO DE ACEITAÇÃO
- Ao clicar no botão de emergência, a notificação imediata aparece com o formato canônico.
- O histórico de notificações (ícone ⏱) lista todas as notificações dessa chamada e das anteriores (já existentes).
- Em dev (sem Twilio SDK), apenas a notificação "foi solicitada com sucesso" aparece após 30s.
```

#### 8.2 Persistir as notificações (lado servidor) para sobreviver a refresh do admin

```
Você é um agente de IA implementando uma melhoria no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Persistir todas as notificações da barra de emergência no backend para que, mesmo após refresh do admin, o histórico de notificações por acidente seja recuperável. Hoje, _emergencyNotifications é apenas memória local do JS. O usuário pediu uma "barra de notificações persistente" (item 3.2.3) — atender via endpoint que retorna todas as notificações armazenadas.

ESCOPO
- Criar uma tabela `accident_call_notifications` com (id, call_log_id FK, accident_id FK, event_type, message_pt, occurred_at, created_at).
- Cada vez que make_emergency_call ou twilio_callbacks.twilio_status_callback dispararia uma notificação SSE, também INSERE uma linha em accident_call_notifications.
- Endpoint GET /api/admin/accidents/{id}/notifications retorna ordenado por occurred_at.
- Front admin: ao carregar a aba de acidente, faz GET inicial e popula _emergencyNotifications. SSE continua atualizando incrementalmente.

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (itens 3.2.3, 3.2.5, 5.5.1)
- alembic/versions/ (último número de migration; verifique Glob alembic/versions/*.py)
- sistema/app/models.py (padrões de declaração)
- sistema/app/routers/admin.py
- sistema/app/services/twilio_caller.py
- sistema/app/routers/twilio_callbacks.py

ARQUIVOS A MODIFICAR
- alembic/versions/00XX_add_accident_call_notifications.py (novo)
- sistema/app/models.py — adicionar AccidentCallNotification
- sistema/app/schemas.py — adicionar AccidentCallNotificationRow + endpoint response model
- sistema/app/routers/admin.py — novo endpoint GET /accidents/{id}/notifications
- sistema/app/services/twilio_caller.py — função helper _record_notification(db, log, event, message) que insere AccidentCallNotification e dispara SSE
- sistema/app/routers/twilio_callbacks.py — chamar _record_notification
- sistema/app/static/admin2/app.js — ao abrir/atualizar accidentPanel, chamar GET /accidents/{id}/notifications e popular a lista; ao receber SSE emergency_call_status_update, dar push() na lista.

PASSOS
1. Glob alembic/versions/*.py para descobrir o último número. Use o próximo livre.
2. Crie a migration:
   create_table accident_call_notifications:
     id PK
     call_log_id FK → accident_call_logs.id ON DELETE CASCADE
     accident_id FK → accidents.id ON DELETE CASCADE
     event_type String(32) NOT NULL  -- 'requested' | 'in-progress' | 'completed' | 'failed' | 'busy' | etc
     message_pt Text NOT NULL
     occurred_at DateTime(tz) NOT NULL
     created_at DateTime(tz) NOT NULL
   Index em (accident_id, occurred_at).
3. Adicione AccidentCallNotification em models.py.
4. Adicione um helper `record_call_notification(db, *, log, event_type, message, occurred_at=None)` em twilio_caller.py.
5. Use o helper em make_emergency_call (após criar o AccidentCallLog) e em twilio_callbacks (a cada callback).
6. Endpoint:
   @router.get("/accidents/{accident_id}/notifications", response_model=list[AccidentCallNotificationRow])
   def list_accident_call_notifications(...):
     ...
7. No front: na função _renderSingleAccidentPanel (admin2/app.js), após renderizar o painel, dispare um fetch e popule a lista. Ao receber SSE, push().
8. Adicione testes para:
   - record_call_notification persiste corretamente.
   - GET /accidents/{id}/notifications retorna ordenado.
   - Cascade delete funciona (apagar acidente apaga notificações).
9. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO substituir notify_admin_data_changed pelo persist — fazer AMBOS.
- NÃO duplicar a mensagem: persistir a versão localizada (pt) e gerar via mesma função do front (_buildNotificationLine no servidor — você pode espelhar a lógica em Python).

CRITÉRIO DE ACEITAÇÃO
- Após acionar emergência, fazer refresh do admin, o histórico das notificações continua exibido.
- Apagar o acidente apaga as notificações em cascata.

NOTAS DE MEMÓRIA
- Anotar que existe uma nova migration. Atualizar [CLAUDE.md](../CLAUDE.md) na seção "Modo Acidente" mencionando a tabela accident_call_notifications.
```

---

## Fase 9 — Feedback de upload de vídeo + arquivos no ZIP/XLSX (item 5.2)

**Objetivo da fase**: 
1. No App, ao gravar/encerrar um vídeo, exibir na barra de notificações `Enviando o registro...`, depois `Registro enviado com sucesso.`, ou `Erro: registro não enviado.` em caso de falha.
2. Na tabela do acidente no admin, a coluna `Registros` deve mostrar links clicáveis aos vídeos enviados (item já parcialmente em [admin2/app.js:7224-7227](../sistema/app/static/admin2/app.js#L7224-L7227) — porém usuário diz que "nenhum link nunca foi disponibilizado").
3. O ZIP gerado deve conter uma pasta por usuário (nome = chave de 4 caracteres) com seus vídeos.
4. O XLSX deve ter, na coluna `Registros`, links que apontem para os vídeos dentro do ZIP (caminhos relativos `Registros/<chave>/<arquivo>`).

**Estado atual**:
- Itens 3 e 4 já parecem implementados em [accident_archive_builder.py:163-178](../sistema/app/services/accident_archive_builder.py#L163-L178) — usa `chave_by_user_id` e gera `Registros/<chave>/<filename>`.
- Item 1 já implementa parcialmente em [accident-camera.js:62-77](../sistema/app/static/check/accident-camera.js#L62-L77) com `setExternalStatus`. Textos atuais: "Enviando registro de vídeo…", "Registro de vídeo enviado.", "Erro: registro de vídeo não enviado.". O usuário pediu textos mais simples: "Enviando o registro...", "Registro enviado com sucesso.", "Erro: registro não enviado.".
- Item 2: o usuário relata que "nenhum link nunca foi disponibilizado". Pode ser bug em `public_url` retornado pelo backend, ou bug no SSE não disparando.

### To-do desta fase

#### 9.1 Padronizar mensagens de upload e verificar fluxo end-to-end de vídeo

```
Você é um agente de IA implementando uma melhoria no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
Corrigir e padronizar o fluxo de upload de vídeo no App (Checking Web) e validar o link na tabela do admin. Item 5.2 do docs/temp002_alteracoes.txt.

Padronizar as mensagens da barra de notificações inferior do App (id=notificationLineSecondary) para EXATAMENTE:
 - Antes do upload começar: "Enviando o registro..."
 - Sucesso: "Registro enviado com sucesso."
 - Erro: "Erro: registro não enviado."

Validar:
 - O backend efetivamente persiste o vídeo (AccidentVideoUpload row criada, public_url gerado).
 - O SSE accident_video_uploaded é emitido e o admin re-renderiza a tabela exibindo o link.
 - O ZIP gerado ao encerrar o acidente contém o vídeo em Registros/<chave>/<arquivo>.
 - O XLSX coluna Registros lista (texto multilinha) e tem hyperlink para o primeiro vídeo.

ARQUIVOS A ESTUDAR
- docs/temp002_alteracoes.txt (item 5.2)
- sistema/app/static/check/accident-camera.js (todo)
- sistema/app/static/check/i18n-dictionaries.js (procure por video, recording, sending)
- sistema/app/routers/web_check.py (upload_accident_video — linha ~1136)
- sistema/app/services/accident_lifecycle.py (attach_video_upload)
- sistema/app/services/object_storage.py (stream_upload_to_storage, generate_presigned_url, public_url generation)
- sistema/app/static/admin2/app.js (_renderVideosHtml linha ~7224)
- sistema/app/services/accident_archive_builder.py

ARQUIVOS A MODIFICAR
- sistema/app/static/check/accident-camera.js — substituir textos por padrão pedido. Internacionalizar via i18n se possível.
- sistema/app/static/check/i18n-dictionaries.js — adicionar chaves `accident.video.sending`, `accident.video.sent`, `accident.video.error`.
- sistema/app/services/object_storage.py (se public_url estiver vazio em dev) — gerar URL local funcional (ex: /api/admin/accidents/local-asset/<object_key>).
- sistema/app/routers/web_check.py — confirme que após attach_video_upload, public_url retornado é válido. Em dev, deve apontar para /api/admin/accidents/local-asset/<object_key>.
- Testes em tests/test_accident_video*.py.

PASSOS
1. Em accident-camera.js, linhas 62-75:
   - Linha 63: setExternalStatus("Enviando o registro...") em vez de "Enviando registro de vídeo…".
   - Linha 72: setExternalStatus("Registro enviado com sucesso.").
   - Linha 75: setExternalStatus("Erro: registro não enviado.").
   - Aplique i18n (t("accident.video.sending"), etc.) para suportar as 6 línguas.
2. Em object_storage.py, examine o _local_root e como public_url é construído. Se ele estiver retornando string vazia em dev (sem DO Spaces configurado), substitua por uma URL local funcional. O endpoint /api/admin/accidents/local-asset/<path:path> já existe em admin.py (linha 2344). Use-o.
3. Em attach_video_upload, garanta public_url não-vazio.
4. Em admin2/app.js _renderVideosHtml, a linha gera <a href=public_url>. Se public_url não-vazio, o link aparece. Confirme via teste.
5. Adicione testes:
   - POST /api/web/check/accident/video → AccidentVideoUpload criado, public_url não-vazio.
   - GET /api/admin/accidents/active retorna situation_rows[i].videos[0].public_url não-vazio.
   - Build do archive: o ZIP contém Registros/<chave>/<filename> e o XLSX coluna Registros tem o texto.
6. Manual sanity: abrir o App, gravar 5s de vídeo, encerrar, ver mensagem na barra. Abrir admin, ver link na tabela. Fechar acidente, baixar ZIP, abrir e ver os vídeos na pasta correta.
7. Rode `pytest -x`.

ANTI-PADRÕES
- NÃO usar strings hardcoded em accident-camera.js. Use i18n.
- NÃO assumir que DO Spaces está configurado em dev — sempre fallback para storage local.
- NÃO remover o /api/admin/accidents/local-asset endpoint (mesmo que pareça pouco utilizado).

CRITÉRIO DE ACEITAÇÃO
- Mensagens exatas: "Enviando o registro...", "Registro enviado com sucesso.", "Erro: registro não enviado." (em PT).
- Link clicável aparece imediatamente na tabela do admin após o upload.
- ZIP baixado tem estrutura `Registros/<chave 4 chars>/<arquivo>`.
- XLSX tem texto multilinha na coluna Registros.

NOTAS DE MEMÓRIA
- Anote que os textos exatos das mensagens são parte do requisito (item 5.2). Não os mude sem nova autorização.
```

---

## Fase 10 — Espelho deploy + regressões finais

**Objetivo da fase**: Sincronizar [deploy/docker/admin2-web/](../deploy/docker/admin2-web/) com [sistema/app/static/admin2/](../sistema/app/static/admin2/) (precisam ficar byte-idênticos, ver `admin2_mirror_sync`), e rodar a suíte completa de testes para confirmar que nenhuma regressão foi introduzida.

### To-do desta fase

#### 10.1 Sincronizar o espelho admin2-web e validar suíte completa

```
Você é um agente de IA finalizando um sprint no projeto "Checking". Raiz: c:/dev/projetos/checkcheck.

OBJETIVO
1. Sincronizar deploy/docker/admin2-web/ com sistema/app/static/admin2/ — eles devem ficar byte-idênticos.
2. Rodar a suíte completa de testes (pytest).
3. Resumir as alterações feitas em todas as fases anteriores em um único PR ou commit message.

CONTEXTO
- Memória "admin2_mirror_sync" no diretório auto-memory documenta que esses dois diretórios são espelhos.
- Memória "admin2_deploy_pipeline" documenta que o deploy usa o workflow do PARENT repo, não do nested.

PASSOS
1. Verifique se as duas pastas estão em sync agora:
   - `diff -r sistema/app/static/admin2/ deploy/docker/admin2-web/` (no Windows: PowerShell `Compare-Object`)
   - Se não estiverem, copie sistema/app/static/admin2/ sobre deploy/docker/admin2-web/.
2. Rode `pytest -x` na raiz. Cole o sumário.
3. Rode `pytest --tb=line` para qualquer falha (não trunque).
4. Se houver testes falhando, identifique se a falha é regressão das mudanças desse plano ou é independente. Documente.
5. Gere a lista das mudanças por fase em formato changelog (não commitar — apenas o resumo no PR description quando o usuário pedir).
6. Verifique se há TODO i18n pendentes em i18n-dictionaries.js e enumere-os (para o usuário decidir se traduz nesta etapa ou em fase futura).

ANTI-PADRÕES
- NÃO commitar nada sem pedido explícito do usuário.
- NÃO criar PR, branch ou push sem pedido explícito.
- NÃO sobrescrever sistema/app/static/admin2/ a partir de deploy/docker/admin2-web/ (a fonte da verdade é sistema/app/static/admin2/).

CRITÉRIO DE ACEITAÇÃO
- Diretórios espelho byte-idênticos.
- Suíte pytest passa (ou as falhas são pré-existentes e documentadas).
- Resumo das fases pronto para o PR.
```

---

## Apêndice A — Mapa de arquivos por tema

| Tema | Arquivos principais |
|---|---|
| **Modelos do acidente** | [models.py:753-933](../sistema/app/models.py#L753-L933) — Accident, AccidentUserReport, AccidentVideoUpload, AccidentArchive, AccidentCallLog, EmailDeliveryLog |
| **Schemas Pydantic do acidente** | [schemas.py:4350-4537](../sistema/app/schemas.py#L4350-L4537) |
| **Endpoints admin acidente** | [admin.py:2040-2389](../sistema/app/routers/admin.py#L2040-L2389) |
| **Endpoints web acidente** | [web_check.py:894-1224](../sistema/app/routers/web_check.py#L894-L1224) |
| **Lifecycle (open/close/report/ack)** | [services/accident_lifecycle.py](../sistema/app/services/accident_lifecycle.py) |
| **Tabela de situação** | [services/accident_situation_table.py](../sistema/app/services/accident_situation_table.py) |
| **XLSX + ZIP archive** | [services/accident_archive_builder.py](../sistema/app/services/accident_archive_builder.py) |
| **Numeração** | [services/accident_numbering.py](../sistema/app/services/accident_numbering.py) |
| **Twilio voice** | [services/twilio_caller.py](../sistema/app/services/twilio_caller.py), [routers/twilio_callbacks.py](../sistema/app/routers/twilio_callbacks.py) |
| **Emails de emergência** | [services/email_sender.py](../sistema/app/services/email_sender.py), [services/email_templates.py](../sistema/app/services/email_templates.py) |
| **SSE Brokers** | [services/admin_updates.py](../sistema/app/services/admin_updates.py) |
| **Admin identity** | [services/admin_identity.py](../sistema/app/services/admin_identity.py), [services/admin_auth.py](../sistema/app/services/admin_auth.py) |
| **Front Admin acidente** | [admin2/app.js:255-260, 7080-7740](../sistema/app/static/admin2/app.js#L255), [admin2/index.html:36-65, 160-180, 388-405, 773-940](../sistema/app/static/admin2/index.html#L36) |
| **Front App acidente** | [check/accident.js](../sistema/app/static/check/accident.js), [check/accident-camera.js](../sistema/app/static/check/accident-camera.js), [check/index.html:71-84, 627-796](../sistema/app/static/check/index.html#L71), [check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js) |

---

## Apêndice B — Glossário de razões SSE relevantes

Razões emitidas hoje (consulte [services/admin_updates.py](../sistema/app/services/admin_updates.py)):

| Reason | Origem | Quem escuta |
|---|---|---|
| `accident_opened` | open_accident (admin/web) | admin + web |
| `accident_closed` | close_accident, delete_accident | admin + web |
| `accident_user_report` | upsert_user_safety_report, update_accident_membership_for_check_event | admin + web |
| `accident_acknowledged` | acknowledge_accident | admin |
| `accident_video_uploaded` | attach_video_upload | admin + web |
| `emergency_call_initiated` | make_emergency_call | admin |
| `emergency_call_status_update` | twilio_status_callback | admin |

A fase 8 acrescenta:
| Reason | Origem | Quem escuta |
|---|---|---|
| `emergency_call_notification` (proposto) | record_call_notification | admin |

---

## Apêndice C — Padrão de prompt didático

Para que cada item de to-do seja consumível por um agente sem contexto, mantenha esta estrutura:

1. **Linha 1**: "Você é um agente de IA implementando/corrigindo/validando ... no projeto 'Checking'. Raiz: c:/dev/projetos/checkcheck."
2. **OBJETIVO** — descrição curta do que entregar.
3. **ARQUIVOS A ESTUDAR ANTES DE EDITAR** — lista absoluta e completa.
4. **ARQUIVOS A MODIFICAR** — lista esperada (pode mudar).
5. **PASSOS** — numerados, com detalhes mecânicos.
6. **ANTI-PADRÕES** — armadilhas conhecidas.
7. **CRITÉRIO DE ACEITAÇÃO** — funcional, testável.
8. **MEMÓRIA / NOTAS PÓS-FASE** — o que registrar para futuras conversas.

> Os agentes não devem **assumir** que migrations 0060+ existem — sempre fazer Glob `alembic/versions/*.py` para descobrir o próximo número livre.
>
> Os agentes não devem **commitar** sem autorização explícita do usuário; finalizar cada fase com `git status` e aguardar instruções.
