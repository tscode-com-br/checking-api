# Auditoria do realtime e barramento cross-worker - Fase 3 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado em escopo de auditoria e implementacao local.
- Objetivo desta etapa: identificar toda dependencia atual de broker em memoria do processo e substituir esse ponto por um barramento cross-worker pequeno e operacionalmente simples.
- Decisao adotada: usar Postgres `LISTEN/NOTIFY` como barramento cross-worker do realtime.
- Decisao explicita: esta proposta nao exigiu Redis.

## 2. Dependencias atuais de broker em memoria identificadas

### 2.1 Fonte central do acoplamento por processo

Antes desta mudanca, `sistema/app/services/admin_updates.py` definia:

- `admin_updates_broker = AdminUpdatesBroker()`
- `transport_updates_broker = AdminUpdatesBroker()`

Esses brokers existiam apenas em memoria local do processo Python. Em runtime com mais de um worker HTTP, cada processo passaria a manter seu proprio conjunto isolado de assinantes e mensagens.

### 2.2 Rotas SSE dependentes desses brokers locais

Dependencias confirmadas nos routers auditados:

1. `sistema/app/routers/admin.py`
   - `GET /api/admin/stream`
   - assinatura via `admin_updates_broker.subscribe()`
2. `sistema/app/routers/transport.py`
   - `GET /api/transport/stream`
   - assinatura via `admin_updates_broker.subscribe()`
3. `sistema/app/routers/web_check.py`
   - `GET /api/web/transport/stream`
   - assinatura via `transport_updates_broker.subscribe()`

### 2.3 Publishers que dependiam do mesmo broker local

O auditoria confirmou publishers espalhados por varias superfices do sistema, incluindo:

- `sistema/app/routers/device.py`
- `sistema/app/routers/mobile.py`
- `sistema/app/routers/provider.py`
- `sistema/app/routers/admin.py`
- `sistema/app/routers/transport.py`
- `sistema/app/routers/web_check.py`
- `sistema/app/routers/transport_ai.py`
- `sistema/app/services/event_logger.py`
- `sistema/app/services/forms_queue.py`
- `sistema/app/services/forms_submit.py`
- `sistema/app/services/transport_reevaluation_events.py`

Implicacao objetiva:

- um evento publicado em um worker nao chegaria automaticamente aos subscribers conectados em outro worker;
- logo, habilitar multiworker sem trocar o barramento quebraria a coerencia do SSE do admin, do transport e do stream web de transporte.

## 3. Barramento escolhido

Barramento implementado:

- Postgres `LISTEN/NOTIFY`

Justificativa tecnica:

1. O projeto ja depende de Postgres na topologia de producao.
2. A stack ja tem `psycopg` instalado; nao foi necessario introduzir nova dependencia de infraestrutura.
3. O escopo desta fase pede uma solucao pequena e operacionalmente simples.
4. Redis seria viavel, mas aumentaria a superficie operacional e o diff sem necessidade tecnica imediata.

Conclusao objetiva:

- Redis nao e necessario para habilitar o barramento cross-worker desta fase.
- O banco ja existente fornece um mecanismo suficiente para propagar eventos entre processos HTTP.

## 4. Implementacao realizada

Arquivos alterados nesta etapa:

- `sistema/app/services/admin_updates.py`
- `sistema/app/main.py`
- `tests/test_api_flow.py`

### 4.1 Mudanca principal no broker

`sistema/app/services/admin_updates.py` deixou de ser apenas um broker local em memoria e passou a ter dois modos:

1. modo local, mantido como fallback quando o dialeto nao e Postgres, especialmente para SQLite de testes;
2. modo cross-worker, quando o runtime usa Postgres, com:
   - entrega local imediata aos subscribers do proprio processo;
   - `pg_notify(...)` para propagar o evento aos demais processos;
   - listener dedicado por processo usando `LISTEN <channel>` em conexao propria do `psycopg`;
   - deduplicacao por `event_id` para evitar eco duplicado do mesmo processo.

### 4.2 Canais implementados

Foram definidos dois canais separados:

- `checking_admin_updates`
- `checking_transport_updates`

Isso preserva a separacao logica ja existente entre o realtime do admin e o realtime especifico do transporte web.

### 4.3 Lifecycle do app

`sistema/app/main.py` agora inicia e encerra explicitamente os listeners de realtime no lifespan da API:

- `start_realtime_brokers()` antes de a aplicacao aceitar trafego;
- `stop_realtime_brokers()` no shutdown.

Isso garante que cada processo HTTP suba com sua assinatura do barramento cross-worker ativa.

## 5. Propriedades relevantes da solucao

1. Nao houve mudanca no contrato publico dos endpoints SSE.
2. Nao houve mudanca no contrato das funcoes `notify_admin_data_changed(...)` e `notify_transport_data_changed(...)`.
3. Nao houve necessidade de alterar os routers para conhecer Postgres diretamente.
4. O fallback local foi preservado para o ambiente de testes com SQLite.
5. A entrega local passou a tratar corretamente publishers executados fora do loop asyncio principal, usando agendamento thread-safe quando o loop do subscriber esta ativo.

## 6. Validacao executada

Comando focado executado nesta etapa:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "admin_updates_broker_publishes_payload or admin_updates_broker_dispatches_cross_worker_payload_without_local_duplicates or http_app_lifespan_starts_and_stops_realtime_brokers or mobile_sync_notifies_admin_realtime_subscribers or web_transport_stream_emits_connected_and_transport_events" -s
```

Resultado:

- `5 passed`

Cobertura objetiva desse slice:

1. o broker continua publicando payload local valido;
2. o broker faz fanout cross-worker sem duplicar o eco no mesmo processo;
3. o app inicia e encerra o lifecycle dos brokers no lifespan;
4. o fluxo de notificacao do admin continua funcional;
5. o stream web de transporte continua funcional.

## 7. Limitacoes declaradas

1. Esta etapa valida o barramento cross-worker no codigo e no slice local de testes; ela ainda nao autoriza multiworker em producao sozinha.
2. Ainda falta o prompt seguinte da Fase 3 para trocar o runtime HTTP para multiworker de forma compativel com este barramento.
3. Ainda falta a validacao dedicada com mais de um processo HTTP real recebendo e publicando eventos em workers diferentes.

## 8. Conclusao tecnica desta etapa

O acoplamento que bloqueava multiworker estava confirmado: o realtime dependia de brokers locais em memoria do processo.

Essa dependencia foi substituida por um barramento cross-worker baseado em Postgres `LISTEN/NOTIFY`, sem introduzir Redis e sem alterar o contrato dos endpoints SSE. Com isso, a aplicacao deixa de ter o broker em memoria como bloqueador estrutural para a proxima etapa de hardening do runtime HTTP.