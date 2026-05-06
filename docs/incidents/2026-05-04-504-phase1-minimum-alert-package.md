# Pacote minimo de alertas operacionais - Fase 1 - incidente 504 de 2026-05-04

## 1. Status desta definicao

- Resultado atual: aprovado como pacote minimo inicial para rollout principal.
- Escopo deste arquivo: definir o conjunto minimo de alertas que precisa existir antes do rollout principal, usando apenas os sinais que ja estao disponiveis hoje no backend, no Docker e no edge.
- Limitacao atual: o repo ainda nao versiona uma stack central de monitoracao como Prometheus, Grafana ou Alertmanager. Portanto, este arquivo define tanto os thresholds iniciais quanto o fallback operacional temporario enquanto a monitoracao central nao estiver pronta.
- Regra de uso: os thresholds abaixo sao thresholds iniciais de protecao operacional. Eles devem ser recalibrados depois da Fase 10, quando existir baseline de carga antes/depois com p50, p95, p99 e backlog sob carga realista.

## 2. Sinais disponiveis hoje

### 2.1 API HTTP

- Logs estruturados de request no logger `checking.http`.
- Campos uteis ja expostos: `path`, `status_code`, `latency_ms`, `request_id`, `client_surface`, `authenticated_kind`, `is_critical_route`.
- Rotas criticas ja marcadas no backend:
  - `/api/health`
  - `/api/web/check/state`
  - `/api/mobile/state`
  - `/api/admin/stream`
  - `/api/admin/checkin`
  - `/api/admin/checkout`
  - `/api/admin/projects`

### 2.2 Fila do Forms

- Endpoint autenticado: `GET /api/admin/forms/queue/diagnostics`.
- Logs estruturados no logger `checking.forms_queue`.
- Sinais uteis ja expostos:
  - `backlog_count`
  - `pending_count`
  - `processing_count`
  - `oldest_backlog_age_seconds`
  - `recent_average_processing_ms`
  - `success_count`
  - `failed_count`
  - `worker.enabled`
  - `worker.running`
  - `worker.last_error`

### 2.3 Banco e pool

- Endpoint autenticado: `GET /api/admin/diagnostics/database`.
- Logs estruturados no logger `checking.db` para queries lentas.
- Sinais uteis ja expostos:
  - `pool.checked_out`
  - `pool.total_capacity`
  - `pool.usage_ratio`
  - `pool.saturation`
  - `pool.checked_out_high_watermark`
  - `latency.recent_average_query_ms`
  - `latency.recent_p95_query_ms`
  - `latency.hot_paths[]`
  - `server_connections.active_database_connections`
  - `server_connections.waiting_database_connections`
  - `server_connections.idle_in_transaction_connections`

### 2.4 Runtime e edge

- Healthcheck do container `app` via `http://127.0.0.1:8000/api/health` no `docker-compose.yml`.
- Healthcheck do container `db` via `pg_isready` no `docker-compose.yml`.
- `restart: unless-stopped` para `app` e `db`.
- Logs de acesso e erro do Nginx no host.
- `docker inspect` expoe `State.Health` e `RestartCount`.
- `docker stats`, `free -m` e `uptime` permitem leitura temporaria de CPU e memoria ate a stack central de monitoracao existir.

## 3. Pacote minimo priorizado de alertas

## P0 - Deve existir antes do rollout principal

### 3.1 App `unhealthy`

- Fonte: `docker inspect checkcheck-app-1`, `docker compose ps`.
- Threshold inicial:
  - `critical`: qualquer estado `unhealthy` do app.
- Justificativa: o healthcheck do app ja faz probing em `/api/health`. Se o container chegou a `unhealthy`, a degradacao ja durou o suficiente para ser operacionalmente relevante.
- Acao esperada: abrir incidente, congelar rollout em curso, comparar saude local e publica e coletar logs antes de qualquer restart.

### 3.2 Banco `unhealthy`

- Fonte: `docker inspect checkcheck-db-1`, `docker compose ps`.
- Threshold inicial:
  - `critical`: qualquer estado `unhealthy` do banco.
- Justificativa: com `depends_on: service_healthy`, a degradacao do banco compromete toda a stack API.

### 3.3 `5xx` nas rotas criticas

- Fonte: `checking.http` ou logs de acesso do Nginx.
- Rotas cobertas:
  - `/api/health`
  - `/api/web/check/state`
  - `/api/mobile/state`
  - `/api/admin/checkin`
  - `/api/admin/checkout`
  - `/api/admin/projects`
  - `/api/admin/stream`
- Threshold inicial:
  - `/api/health`
    - `critical`: qualquer `5xx` em 2 minutos ou 2 falhas consecutivas de health publico.
  - demais rotas criticas de request-resposta
    - `warning`: `>= 5` respostas `5xx` ou taxa `> 2%` em janela de 5 minutos.
    - `critical`: `>= 10` respostas `5xx` ou taxa `> 5%` em janela de 5 minutos.
  - `/api/admin/stream`
    - `warning`: `>= 3` falhas `5xx` ou reconexoes anormais em 5 minutos.
    - `critical`: `>= 6` falhas `5xx` ou reconexoes anormais em 5 minutos.
- Justificativa: `/api/health` precisa ser muito mais sensivel. As demais rotas criticas precisam tolerar ruido baixo, mas nao podem acumular erros sustentados sem alerta.

### 3.4 Backlog da fila do Forms

- Fonte: `GET /api/admin/forms/queue/diagnostics`, logs `checking.forms_queue`.
- Threshold inicial:
  - `warning`: `backlog_count >= 10` por 5 minutos ou `oldest_backlog_age_seconds > 120`.
  - `critical`: `backlog_count >= 25` por 5 minutos ou `oldest_backlog_age_seconds > 300`.
  - `critical`: `worker.enabled = true`, `worker.running = false` e `backlog_count > 0`.
- Justificativa: a fila existe para absorver burst sem derrubar o HTTP. Se o backlog envelhece demais ou o worker para com backlog pendente, o risco operacional volta a crescer rapidamente.

### 3.5 Conexoes de banco elevadas ou esperando

- Fonte: `GET /api/admin/diagnostics/database`.
- Threshold inicial:
  - `warning`: `active_database_connections >= 24` por 5 minutos.
  - `critical`: `active_database_connections >= 32` por 5 minutos.
  - `warning`: `waiting_database_connections >= 1` por 2 minutos.
  - `critical`: `waiting_database_connections >= 3` por 1 minuto.
  - `warning`: `idle_in_transaction_connections >= 1` por 5 minutos.
- Justificativa: o Postgres esta configurado com `max_connections=40`, entao `24` e `32` representam pressao relevante antes da borda dura. Espera por conexao ou `idle in transaction` sustentado indica problema operacional mesmo antes de esgotar o limite.

## P1 - Deve entrar na mesma janela do rollout ou imediatamente depois

### 3.6 Latencia p95/p99 por rota critica

- Fonte: `checking.http`.
- Regras gerais:
  - usar janela de 10 minutos para `warning` e 5 minutos para `critical`.
  - calcular p95 e p99 por rota, nao agregado geral.
  - `/api/admin/stream` fica fora desta regra porque e stream longo; nela valem alertas de erro e churn de reconexao.
- Threshold inicial por rota:
  - `/api/health`
    - `warning`: `p95 > 300 ms` ou `p99 > 800 ms`
    - `critical`: `p95 > 800 ms` ou `p99 > 1500 ms`
  - `/api/web/check/state`
    - `warning`: `p95 > 750 ms` ou `p99 > 1500 ms`
    - `critical`: `p95 > 1500 ms` ou `p99 > 3000 ms`
  - `/api/mobile/state`
    - `warning`: `p95 > 750 ms` ou `p99 > 1500 ms`
    - `critical`: `p95 > 1500 ms` ou `p99 > 3000 ms`
  - `/api/admin/checkin`
    - `warning`: `p95 > 1000 ms` ou `p99 > 2000 ms`
    - `critical`: `p95 > 2000 ms` ou `p99 > 4000 ms`
  - `/api/admin/checkout`
    - `warning`: `p95 > 1000 ms` ou `p99 > 2000 ms`
    - `critical`: `p95 > 2000 ms` ou `p99 > 4000 ms`
  - `/api/admin/projects`
    - `warning`: `p95 > 1200 ms` ou `p99 > 2500 ms`
    - `critical`: `p95 > 2500 ms` ou `p99 > 5000 ms`
- Justificativa: `health` precisa permanecer folgado. `state` e rotas de presenca precisam responder com fluidez sob burst legitimo. `projects` pode tolerar um pouco mais, mas nao deve se aproximar de timeouts do edge.

### 3.7 RestartCount anormal

- Fonte: `docker inspect checkcheck-app-1`, `docker inspect checkcheck-db-1`.
- Threshold inicial:
  - `warning`: `RestartCount` aumenta em `1` dentro de 30 minutos.
  - `critical`: `RestartCount` aumenta em `>= 2` dentro de 30 minutos.
  - `critical`: qualquer aumento de `RestartCount` combinado com `unhealthy` ou pico de `5xx` em rota critica.
- Justificativa: um restart isolado ja merece investigacao num ambiente pequeno; recorrencia curta indica instabilidade real.

### 3.8 CPU alta sustentada

- Fonte: monitoracao central futura; fallback temporario via `docker stats` e `uptime`.
- Threshold inicial para o host ou container `app`:
  - `warning`: CPU `> 80%` por 10 minutos.
  - `critical`: CPU `> 90%` por 5 minutos.
- Justificativa: o incidente original ocorreu em droplet pequeno e com runtime dividido com Postgres, Python, Playwright e Chromium. CPU alta sustentada reduz capacidade de absorver burst e piora latencia antes do colapso.

### 3.9 Memoria alta sustentada

- Fonte: monitoracao central futura; fallback temporario via `docker stats` e `free -m`.
- Threshold inicial para o host:
  - `warning`: memoria usada `> 80%` por 10 minutos ou memoria livre `< 400 MB`.
  - `critical`: memoria usada `> 90%` por 5 minutos ou memoria livre `< 200 MB`.
- Observacao: se a mitigacao do droplet para `2 GB / 2 vCPU` ainda nao tiver sido aplicada, mantenha os thresholds percentuais e reduza os pisos absolutos de memoria livre pela metade para evitar falso positivo antes do resize.
- Justificativa: Chromium e Playwright ampliam pico de memoria. Esperar ate swap ou OOM e tarde demais.

### 3.10 Pool e latencia de query do banco

- Fonte: `GET /api/admin/diagnostics/database`, logs `checking.db`.
- Threshold inicial:
  - `warning`: `pool.usage_ratio >= 0.8` por 5 minutos.
  - `critical`: `pool.usage_ratio >= 1.0` em qualquer janela.
  - `warning`: `latency.recent_p95_query_ms > 150` por 10 minutos.
  - `critical`: `latency.recent_p95_query_ms > 300` por 5 minutos.
  - `warning`: crescimento de `slow_query_count_total` junto com `db_query_slow` recorrente por 10 minutos.
- Justificativa: esses thresholds ja foram materializados no proprio backend como limites recomendados iniciais. Eles antecipam saturacao do pool e degradação de query antes de virarem `5xx` publicos.

## 4. Ordem minima recomendada de implementacao de alertas

1. `app unhealthy` e `db unhealthy`
2. `5xx` em `/api/health` e nas demais rotas criticas
3. backlog e idade da fila do Forms
4. conexoes de banco ativas/em espera e saturacao do pool
5. RestartCount anormal
6. latencia p95/p99 por rota critica
7. CPU alta sustentada
8. memoria alta sustentada

## 5. Fallback operacional temporario enquanto a monitoracao central nao estiver pronta

## 5.1 Dependencias explicitas

- Os endpoints `GET /api/admin/forms/queue/diagnostics` e `GET /api/admin/diagnostics/database` exigem sessao administrativa valida.
- Este repo nao versiona credenciais operacionais. Portanto, qualquer consulta automatizada a esses endpoints depende de chave e senha administrativas fornecidas ao operador no host.
- Se essas credenciais nao estiverem disponiveis na janela do incidente, o fallback temporario deve usar healthchecks, `docker inspect`, `docker stats`, logs do app e logs do Nginx ate que um operador autorizado consulte os endpoints autenticados.

## 5.2 Verificacao rapida de saude do app e do banco

```bash
docker compose ps
docker inspect checkcheck-app-1 --format '{{json .State}}'
docker inspect checkcheck-db-1 --format '{{json .State}}'
curl -i http://127.0.0.1:8000/api/health
curl -i https://tscode.com.br/api/health
```

O que procurar:

- `Health.Status` diferente de `healthy`
- aumento de `RestartCount`
- diferenca entre saude local do upstream e saude publica no edge

## 5.3 Verificacao de `5xx` e timeouts no edge

```bash
grep ' 5[0-9][0-9] ' /var/log/nginx/access.log | tail -n 200
grep 'upstream timed out' /var/log/nginx/error.log | tail -n 100
tail -n 200 /var/log/nginx/error.log
tail -n 200 /var/log/nginx/access.log
```

O que procurar:

- concentracao de `5xx` em `/api/web/check/state`, `/api/mobile/state`, `/api/admin/checkin`, `/api/admin/checkout`, `/api/admin/projects`
- `upstream timed out` repetido
- diferenca entre falha publica no Nginx e health local ainda `ok`

## 5.4 Verificacao de logs estruturados da API

```bash
docker logs --since 10m checkcheck-app-1 | rg 'checking.http|checking.forms_queue|checking.db'
docker logs --since 10m checkcheck-app-1 | rg '"event":"http_request"|"event":"forms_queue_|"event":"db_query_slow"'
```

O que procurar:

- `status_code` `5xx` nas rotas criticas
- `latency_ms` crescente nas rotas de `state` e de presenca
- `forms_queue_processed` com falhas repetidas
- `db_query_slow` recorrente na mesma rota

## 5.5 Verificacao temporaria de CPU e memoria

```bash
docker stats --no-stream checkcheck-app-1 checkcheck-db-1
free -m
uptime
```

O que procurar:

- CPU do `app` ou do host acima dos thresholds definidos
- memoria livre do host abaixo do piso
- load average crescendo junto com latencia e `5xx`

## 5.6 Verificacao autenticada da fila do Forms e do banco

Exemplo operacional em host Linux, se o operador tiver credenciais administrativas validas:

```bash
curl -sS -c /tmp/checkcheck_admin.cookies \
  -H 'Content-Type: application/json' \
  -d '{"chave":"'$CHECKCHECK_ADMIN_KEY'","senha":"'$CHECKCHECK_ADMIN_PASSWORD'"}' \
  http://127.0.0.1:8000/api/admin/auth/login

curl -sS -b /tmp/checkcheck_admin.cookies \
  http://127.0.0.1:8000/api/admin/forms/queue/diagnostics

curl -sS -b /tmp/checkcheck_admin.cookies \
  http://127.0.0.1:8000/api/admin/diagnostics/database
```

O que procurar no endpoint da fila:

- `backlog_count`
- `oldest_backlog_age_seconds`
- `worker.running`
- `worker.last_error`

O que procurar no endpoint do banco:

- `pool.usage_ratio`
- `latency.recent_p95_query_ms`
- `server_connections.active_database_connections`
- `server_connections.waiting_database_connections`

## 6. Conclusao operacional

O pacote minimo de alertas antes do rollout principal precisa cobrir, nesta ordem, indisponibilidade real do app, erro `5xx` em rotas criticas, backlog da fila do Forms, pressao de conexoes de banco, restart anormal e degradacao sustentada de latencia, CPU e memoria.

Mesmo sem uma stack central de monitoracao pronta, o projeto ja tem sinais suficientes para operar com alerta precoce: healthchecks do compose, logs estruturados `checking.http`, `checking.forms_queue` e `checking.db`, mais os endpoints autenticados de diagnostico da fila e do banco.

O proximo passo natural e transformar este pacote em configuracao efetiva de alertas e, em seguida, consolidar o runbook operacional final com base nesses mesmos sinais.