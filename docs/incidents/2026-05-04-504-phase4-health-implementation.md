# Implementacao de healthchecks fiéis ao estado real - Fase 4 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado em escopo local de implementacao.
- Objetivo desta etapa: fazer o app HTTP deixar de parecer saudavel apenas por estar vivo, separar `liveness` de `readiness` e tornar a degradacao do worker do Forms visivel sem transformar isso em indisponibilidade falsa da API.

## 2. O que mudou

### 2.1 Novos endpoints de health

`sistema/app/routers/health.py` deixou de expor apenas um `status="ok"` raso e passou a ter tres superficies distintas:

1. `GET /api/health/live`
   - prova apenas que o processo HTTP responde;
   - nao toca banco nem worker.
2. `GET /api/health/ready`
   - faz o gate binario de readiness da API;
   - responde `503` quando a API nao esta apta a receber trafego util.
3. `GET /api/health`
   - virou resumo operacional da API;
   - responde `200` quando a API esta pronta, mesmo que haja componente degradado;
   - responde `503` quando a readiness falha.

### 2.2 Regras concretas de readiness

Nesta implementacao, a readiness da API HTTP depende de:

1. banco acessivel via consulta leve `SELECT 1`;
2. superficies estaticas obrigatorias existirem quando a propria API estiver configurada para servir `admin`, `user` e `transport`.

Se qualquer um desses requisitos falhar, `GET /api/health/ready` e `GET /api/health` passam a responder `503` com `status="unready"`.

### 2.3 Worker do Forms agora aparece como componente separado

`GET /api/health` passou a incluir o componente `forms_worker` usando os sinais ja existentes em `sistema/app/services/forms_queue.py`.

Semantica aplicada:

1. worker desabilitado por configuracao -> `disabled`;
2. worker habilitado e saudavel -> `ok`;
3. worker habilitado, mas com heartbeat stale, nao rodando ou excedendo limiar de erros -> `degraded`.

Importante:

- a falha do worker do Forms nao derruba a readiness da API HTTP;
- mas tambem nao fica invisivel, porque aparece explicitamente no resumo de `/api/health`.

### 2.4 Modelo de payload

`sistema/app/schemas.py` passou a modelar:

1. `HealthLivenessResponse`;
2. `HealthComponentResponse`;
3. `HealthResponse` com:
   - `status`
   - `ready`
   - `overall_status`
   - `components`

Estados agregados usados agora:

1. `ok`
2. `degraded`
3. `unready`

### 2.5 Compose agora mira readiness, nao resumo operacional

`docker-compose.yml` e `docker-compose.api.yml` foram ajustados para que o healthcheck do container HTTP consulte:

```sh
http://127.0.0.1:8000/api/health/ready
```

Com isso, o container deixa de parecer saudavel apenas porque um worker respondeu uma rota HTTP minima.

### 2.6 Middleware e classificacao de superficie

`sistema/app/main.py` foi ajustado para tratar `/api/health`, `/api/health/live` e `/api/health/ready` como superficie `health` nas rotinas de request logging e de classificacao de rota critica.

## 3. Arquivos alterados

- `sistema/app/schemas.py`
- `sistema/app/routers/health.py`
- `sistema/app/main.py`
- `docker-compose.yml`
- `docker-compose.api.yml`
- `tests/test_api_flow.py`
- `docs/incidents/2026-05-04-504-phase4-health-implementation.md`

## 4. Validacao executada

### 4.1 Testes focados do slice de health

Comando executado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_health or test_health_live or test_health_ready or test_health_ready_returns_503_when_database_is_unavailable or test_health_surfaces_forms_worker_degradation_without_failing_api or test_http_request_logging_middleware_emits_structured_fields_and_request_id" -s
```

Resultado:

- `6 passed`

Cobertura objetiva:

1. `/api/health` segue respondendo `200` quando a API esta pronta;
2. `/api/health/live` prova liveness minima;
3. `/api/health/ready` prova readiness binaria;
4. banco indisponivel derruba readiness para `503`;
5. worker do Forms degradado aparece em `/api/health` sem derrubar a API;
6. o middleware de request logging continua registrando requests de health corretamente.

### 4.2 Regressao curta de startup e lifespan

Comando executado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_http_app_lifespan_does_not_start_forms_worker or test_http_app_lifespan_starts_and_stops_realtime_brokers" -s
```

Resultado:

- `2 passed`

### 4.3 Boot em subprocesso com IA de transporte desligada

Comando executado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_transport_ai_config.py -s
```

Resultado:

- `2 passed`

### 4.4 Checagem estatica dos arquivos Python alterados

- `get_errors` retornou sem erros para:
  - `sistema/app/routers/health.py`
  - `sistema/app/schemas.py`
  - `sistema/app/main.py`
  - `tests/test_api_flow.py`

## 5. Limitacoes declaradas

1. Nao foi executado `docker compose config` nesta sessao porque o ambiente local desta workspace nao fornece Docker operacional como pre-requisito validado desta fase.
2. O resumo operacional de `/api/health` ainda nao incorpora estado publico proprio do barramento realtime nem backlog detalhado da fila; nesta etapa ele expõe apenas o worker do Forms como componente secundario explicito, que era o requisito minimo pedido aqui.
3. A estrategia de auto-recuperacao baseada nesses novos estados fica para o proximo prompt da Fase 4.

## 6. Resultado tecnico

- a API HTTP agora distingue `liveness` de `readiness`;
- o compose do app passa a usar readiness real;
- o worker do Forms deixa de mascarar a saude da API, mas passa a aparecer no resumo operacional;
- o endpoint publico `/api/health` passa a representar `ok`, `degraded` ou `unready` sem reaproximar o worker do caminho critico HTTP.

## 7. Rollback minimo desta execucao

Se for necessario reverter apenas esta etapa:

1. restaurar `sistema/app/routers/health.py` para o endpoint raso anterior;
2. restaurar `sistema/app/schemas.py` para o schema anterior de health;
3. restaurar `sistema/app/main.py` para a classificacao anterior das rotas de health;
4. recolocar `docker-compose.yml` e `docker-compose.api.yml` apontando para `/api/health`;
5. remover os testes novos de health em `tests/test_api_flow.py`.

## 8. Proximo passo recomendado

O proximo passo natural da Fase 4 e implementar a politica de auto-recuperacao operacional com base nessa nova semantica:

1. quando reiniciar apenas o worker do Forms;
2. quando reiniciar apenas a API HTTP;
3. quando parar para coleta de evidencias antes de qualquer reboot maior.