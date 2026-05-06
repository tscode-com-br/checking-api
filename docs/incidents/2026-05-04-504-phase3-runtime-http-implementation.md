# Implementacao do runtime HTTP compativel com barramento cross-worker - Fase 3 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado em escopo local de implementacao.
- Objetivo desta etapa: trocar o runtime HTTP de `uvicorn` puro para um runtime de producao compativel com o barramento cross-worker ja entregue, sem alterar o contrato publico dos endpoints SSE.

## 2. Implementacao realizada

Arquivos alterados nesta etapa:

- `sistema/app/http_runtime.py`
- `requirements.txt`
- `Dockerfile`
- `deploy/docker/Dockerfile.api`
- `docker-compose.yml`
- `docker-compose.api.yml`
- `deploy/.env.production.example`
- `docs/context/arquitetura_alvo_deploy_separado_monorepo.md`
- `tests/test_api_flow.py`

### 2.1 Novo entrypoint do runtime HTTP

Foi criado `sistema/app/http_runtime.py` como entrypoint unico do runtime HTTP.

Esse modulo faz duas coisas, nesta ordem:

1. executa `python -m alembic upgrade head` como preflight do processo HTTP;
2. troca o processo atual por `gunicorn` via `python -m gunicorn.app.wsgiapp`, usando worker ASGI do Uvicorn.

Comando efetivo montado pelo entrypoint:

```sh
python -m gunicorn.app.wsgiapp sistema.app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers ${APP_WORKERS} \
  --bind ${APP_HOST}:${APP_PORT} \
  --keep-alive ${APP_KEEPALIVE_SECONDS} \
  --timeout ${APP_TIMEOUT_SECONDS} \
  --graceful-timeout ${APP_GRACEFUL_TIMEOUT_SECONDS} \
  --max-requests ${APP_MAX_REQUESTS} \
  --max-requests-jitter ${APP_MAX_REQUESTS_JITTER}
```

### 2.2 Parametros operacionais explicitados

Os parametros do runtime agora ficaram explicitados no compose e no exemplo de ambiente de producao:

- `APP_WORKERS=2`
- `APP_KEEPALIVE_SECONDS=5`
- `APP_TIMEOUT_SECONDS=90`
- `APP_GRACEFUL_TIMEOUT_SECONDS=30`
- `APP_MAX_REQUESTS=1000`
- `APP_MAX_REQUESTS_JITTER=100`

Esses valores seguem a auditoria anterior da Fase 3 para o baseline `2 GB / 2 vCPU`.

### 2.3 Compatibilidade com o barramento de eventos

O runtime HTTP agora e compativel com mais de um processo porque o barramento de realtime ja nao depende mais de memoria local do processo.

Na etapa anterior:

- `admin_updates_broker` e `transport_updates_broker` passaram a usar Postgres `LISTEN/NOTIFY` em runtime PostgreSQL;
- os listeners sobem no lifespan da aplicacao;
- os endpoints SSE continuam usando o mesmo contrato publico.

Implicacao:

- o admin stream, o transport stream e o web transport stream continuam coerentes mesmo quando publishers e subscribers caem em processos HTTP diferentes, desde que a validacao multiworker dedicada da proxima etapa aprove esse comportamento em processo real.

## 3. Decisoes explicitas desta etapa

1. O servidor de producao passou a ser `gunicorn` com workers ASGI do Uvicorn.
2. Redis continua desnecessario para esta fase.
3. O healthcheck interno do container permanece valido, porque a porta interna continua `8000`.
4. Esta etapa nao separa migracao do processo HTTP; isso continua como debito controlado da Fase 9.

## 4. Validacao executada

Validacao focada do novo runtime:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "http_runtime_builds_gunicorn_command_from_environment or http_runtime_runs_migrations_before_execing_server or admin_updates_broker_dispatches_cross_worker_payload_without_local_duplicates or mobile_sync_notifies_admin_realtime_subscribers or web_transport_stream_emits_connected_and_transport_events" -s
```

Cobertura objetiva:

1. o entrypoint monta o comando de `gunicorn` com os parametros esperados;
2. o preflight de migracao continua acontecendo antes do processo HTTP;
3. o barramento cross-worker segue funcional no slice de realtime ja sensivel a multiworker;
4. os streams SSE criticos continuam coerentes no contrato local.

## 5. Limitacoes declaradas

1. Esta execucao foi feita em workspace Windows; portanto o runtime `gunicorn` em multiprocessos Linux de container nao foi executado diretamente aqui como processo de servidor real.
2. A validacao de consistencia com mais de um processo HTTP real permanece como etapa dedicada do proximo prompt da Fase 3.
3. O startup ainda mantem migracao acoplada ao boot HTTP, por decisao deliberada de menor superficie nesta etapa.

## 6. Conclusao tecnica desta etapa

O runtime HTTP de producao deixou de depender de `uvicorn` puro e passou a ser um entrypoint versionado para `gunicorn` com workers ASGI do Uvicorn, com parametros operacionais explicitos e compativeis com o barramento cross-worker ja implementado.

Com isso, a base tecnica para multiworker ficou entregue no repo. A autorizacao de rollout com mais de um processo HTTP continua dependente da validacao controlada da proxima etapa da Fase 3.