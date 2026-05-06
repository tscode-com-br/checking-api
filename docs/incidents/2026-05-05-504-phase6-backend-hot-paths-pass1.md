# Otimizacao inicial dos hot paths backend - Fase 6 - incidente 504 de 2026-05-05

## 1. Objetivo executado

Auditar e reduzir o trabalho por request nos primeiros hot paths backend priorizados nesta fase:

1. `GET /api/web/check/state`
2. `GET /api/mobile/state`
3. `GET /api/admin/checkin`
4. `GET /api/admin/checkout`
5. `GET /api/admin/projects`

O foco desta passada foi remover repeticoes e N+1 no caminho real de leitura, sem alterar o contrato HTTP das rotas.

## 2. Diagnostico local que guiou o patch

Os handlers dessas rotas eram finos. O custo real estava nos helpers compartilhados:

1. `build_presence_rows` em `sistema/app/routers/admin.py` carregava usuarios e chamava `resolve_latest_user_activity` um por um, caracterizando N+1 claro para `checkin` e `checkout`.
2. `build_mobile_sync_state` em `sistema/app/services/user_sync.py` fazia varias consultas sequenciais para o mesmo usuario: sync `checkin`, sync `checkout`, atividade mais recente, fallback de `checkin` e fallback de `checkout`.
3. `build_web_check_history_state` reaproveitava `build_mobile_sync_state`, mas ainda fazia uma consulta extra de timezone do projeto.
4. `GET /api/admin/projects` ja estava estruturalmente barato: leitura unica ordenada de projetos e serializacao simples. Nao era o hotspot principal desta passada.

## 3. Alteracoes aplicadas

### 3.1 `sistema/app/services/user_sync.py`

Foi introduzido preload em lote dos insumos usados para resolver atividade do usuario:

1. preload de `UserSyncEvent` por conjunto de `user_id`;
2. preload de `CheckEvent` por conjunto de `rfid`;
3. preload de timezones de projeto usados nesses eventos.

Com isso:

1. `resolve_latest_user_activity` passou a reutilizar dados pre-carregados em vez de reconsultar a base por etapa;
2. `build_mobile_sync_state` passou a montar `last_checkin_at`, `last_checkout_at` e `current_action` a partir do mesmo lote carregado uma unica vez;
3. `build_web_check_history_state` passou a reaproveitar o timezone do projeto ja resolvido no mesmo fluxo, sem consulta extra dedicada.

### 3.2 `sistema/app/routers/admin.py`

`build_presence_rows` deixou de resolver ultima atividade por usuario de forma isolada.

Agora o fluxo e:

1. carregar catalogo de projetos uma vez;
2. aplicar escopo administrativo na query de usuarios;
3. resolver atividades mais recentes em lote para a lista filtrada;
4. serializar apenas os usuarios efetivamente elegiveis para a resposta.

Isso remove o N+1 dominante de `GET /api/admin/checkin` e `GET /api/admin/checkout`.

### 3.3 `sistema/app/services/project_catalog.py`

`list_project_names` deixou de carregar objetos `Project` completos quando apenas os nomes eram necessarios.

## 4. Rotas auditadas e decisao por rota

### `GET /api/web/check/state`

Alterada.

O custo vinha da montagem serial do estado do usuario. O endpoint agora reaproveita um unico lote de leitura para sync, fallback e timezone.

### `GET /api/mobile/state`

Alterada.

Recebeu a mesma consolidacao aplicada ao estado web, com menos consultas por usuario.

### `GET /api/admin/checkin`

Alterada.

O N+1 de atividade por usuario foi substituido por resolucao em lote.

### `GET /api/admin/checkout`

Alterada.

A mesma remocao de N+1 aplicada em `checkin` passa a valer aqui.

### `GET /api/admin/projects`

Auditada, sem refatoracao estrutural nesta passada.

O endpoint ja era composto por leitura unica e serializacao curta. A medicao local desta etapa confirmou custo baixo o bastante para nao priorizar mudanca nele agora.

## 5. Evidencia operacional desta passada

Leitura rapida em ambiente de teste local, usando a telemetria de banco ja existente e executando uma request por rota, apos seed minimo:

1. `GET /api/web/check/state`: `4` queries
2. `GET /api/mobile/state`: `3` queries
3. `GET /api/admin/checkin`: `6` queries
4. `GET /api/admin/checkout`: `6` queries
5. `GET /api/admin/projects`: `2` queries

Leitura objetiva:

1. `admin/projects` nao apareceu como gargalo nesta rodada;
2. `web/mobile state` ficaram suficientemente compactados para uma primeira passada;
3. `admin/checkin` e `admin/checkout` ainda sao mais caros do que os endpoints de estado unitario, mas sem o N+1 anterior.

## 6. Arquivos alterados

1. `sistema/app/services/user_sync.py`
2. `sistema/app/routers/admin.py`
3. `sistema/app/services/project_catalog.py`
4. `docs/incidents/2026-05-05-504-phase6-backend-hot-paths-pass1.md`

## 7. Validacao executada

### 7.1 Contrato funcional

Comando:

1. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_explicit_checkin_and_checkout_flow or test_provider_current_state_uses_forms_as_local_when_provider_event_wins or test_web_check_state_returns_latest_public_history or test_mobile_checkout_preserves_previous_checkin_history_without_existing_sync_events or test_mobile_state_falls_back_to_check_events_history"`

Resultado:

1. `5 passed`

### 7.2 Checagem estatica

Arquivos verificados sem erros de editor:

1. `sistema/app/services/user_sync.py`
2. `sistema/app/routers/admin.py`
3. `sistema/app/services/project_catalog.py`

### 7.3 Medicao operacional curta

Foi executado um snippet Python local sobre a app de teste, lendo a telemetria de banco por rota apos uma request de cada hot path auditado.

## 8. Risco residual

1. `build_inactive_rows` ainda usa a estrategia antiga de resolver atividade por usuario individualmente e pode merecer a mesma consolidacao se entrar no conjunto de rotas quentes.
2. Esta passada removeu redundancia e N+1 obvios, mas nao adiciona ainda indices novos ou leitura especializada por SQL para tabelas de eventos muito grandes.
3. A medicao desta etapa e local e curta; ainda falta correlacionar isso com latencia/pool reais em host produtivo.

## 9. Resultado

Aprovado para a primeira passada da Fase 6.

Os hotspots selecionados deixaram de recomputar estado do usuario por consultas repetidas e o N+1 mais claro dos endpoints administrativos foi removido. `GET /api/admin/projects` foi auditado e ficou fora da priorizacao imediata por ja estar barato nesta medicao.

## 10. Proximo passo recomendado

Continuar a Fase 6 atacando o segundo nivel de custo backend:

1. medir `build_inactive_rows` e outros endpoints administrativos que ainda usam `resolve_latest_user_activity` por usuario;
2. revisar indices e estrategia de leitura das tabelas `user_sync_events` e `check_events` para volume maior;
3. validar em preview/producao a queda de latencia e a pressao no pool apos estas reducoes de queries por request.