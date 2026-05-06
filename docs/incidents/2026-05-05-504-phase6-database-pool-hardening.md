# Hardening do pool de banco e da camada de acesso - Fase 6 - incidente 504 de 2026-05-05

## 1. Objetivo executado

Endurecer a configuracao do pool de conexoes e tornar explicito o sizing do acesso ao Postgres para o runtime alvo da stack.

O escopo desta passada cobriu:

1. `sistema/app/database.py`
2. `sistema/app/core/config.py`
3. `docker-compose.yml`
4. `docker-compose.api.yml`

## 2. Hipotese ou risco atacado

O risco local confirmado nesta auditoria era saturacao oculta de conexoes por defaults implicitos do SQLAlchemy.

Estado anterior relevante:

1. o runtime HTTP alvo do repo usa `gunicorn` com `APP_WORKERS=2`;
2. existe tambem `1` processo separado para `forms-worker`;
3. o Postgres principal esta limitado a `max_connections=40` em `docker-compose.yml`;
4. o `create_engine(..., pool_pre_ping=True)` usava o `QueuePool` default do SQLAlchemy para Postgres, que hoje equivale a `pool_size=5` e `max_overflow=10` por processo.

Consequencia teorica do estado anterior para o desenho atual da stack:

1. `2` workers HTTP x `15` conexoes possiveis por processo = `30`;
2. `1` processo `forms-worker` x `15` conexoes possiveis = `15`;
3. capacidade teorica total = `45`, acima de `max_connections=40`, sem reservar headroom para migracoes, shells operacionais, health probes e acessos administrativos.

## 3. Decisao tecnica de sizing

O sizing aplicado foi conectado ao runtime alvo conhecido do repo e ao host baseline desta fase, que trabalha com `2 GB / 2 vCPU` como patamar minimo de operacao mais seguro.

### 3.1 App HTTP

Parametros explicitos por processo HTTP:

1. `pool_size=6`
2. `max_overflow=2`
3. `pool_timeout=5s`
4. `pool_recycle=1800s`
5. `pool_pre_ping=true`

Justificativa:

1. com `2` workers HTTP, o teto de burst do app fica em `16` conexoes (`2 x (6 + 2)`), suficiente para bursts curtos sem deixar o app consumir sozinho a maior parte das `40` conexoes do Postgres;
2. `5s` de `pool_timeout` e intencionalmente muito menor que o `APP_TIMEOUT_SECONDS=90`, para falhar cedo quando o banco estiver exaurido em vez de transformar espera por pool em request pendurado;
3. `1800s` de `pool_recycle` limita a idade das conexoes de workers long-lived sem causar churn agressivo a cada request;
4. `pool_pre_ping=true` foi mantido para evitar reutilizacao cega de conexoes quebradas.

### 3.2 Forms worker

Parametros explicitos do worker separado:

1. `pool_size=2`
2. `max_overflow=1`
3. `pool_timeout=5s`
4. `pool_recycle=1800s`
5. `pool_pre_ping=true`

Justificativa:

1. o `forms-worker` processa a fila de forma serial e usa sessoes curtas por etapa, portanto nao precisa carregar o mesmo teto do app HTTP;
2. limitar o worker a `3` conexoes teoricas preserva headroom para a API mesmo sob backlog do Forms.

### 3.3 Capacidade agregada resultante

Com a stack alvo desta fase:

1. app HTTP: `16` conexoes teoricas maximas;
2. `forms-worker`: `3` conexoes teoricas maximas;
3. total agregado: `19` conexoes;
4. headroom preservado dentro de `max_connections=40`: `21` conexoes.

Esse headroom cobre melhor migracoes, shells operacionais, health checks, diagnosticos e variacao de runtime sem depender de defaults implicitos.

## 4. Alteracoes aplicadas

### `sistema/app/core/config.py`

Foram introduzidas configuracoes explicitas para:

1. `database_pool_size`
2. `database_max_overflow`
3. `database_pool_timeout_seconds`
4. `database_pool_recycle_seconds`

### `sistema/app/database.py`

Foi criada resolucao explicita do pool por URL de banco:

1. Postgres passa a receber `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle` e `pool_pre_ping` explicitamente;
2. SQLite continua sem forcar overrides de `QueuePool`, preservando o comportamento adequado para testes e execucoes locais;
3. a telemetria do endpoint de diagnostico passa a expor tambem `configured_pool_timeout_seconds`, `configured_pool_recycle_seconds` e `pool_pre_ping`.

### `docker-compose.yml`

Foram materializados os parametros explicitos por papel:

1. `app` recebe defaults de pool para o runtime HTTP;
2. `forms-worker` recebe defaults menores, coerentes com seu padrao serial de consumo.

### `docker-compose.api.yml`

Foi alinhado o perfil de API isolada para evitar drift:

1. o `db` recebeu o mesmo envelope de memoria e `max_connections=40` do compose principal;
2. o servico `api` recebeu os mesmos parametros explicitos de pool do app HTTP.

## 5. Arquivos alterados

1. `sistema/app/core/config.py`
2. `sistema/app/database.py`
3. `sistema/app/schemas.py`
4. `docker-compose.yml`
5. `docker-compose.api.yml`
6. `tests/test_api_flow.py`
7. `docs/incidents/2026-05-05-504-phase6-database-pool-hardening.md`

## 6. Comandos executados

1. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "test_database_diagnostics_endpoint_reports_query_and_pool_metrics or test_database_engine_kwargs_apply_explicit_queue_pool_settings_for_postgres or test_database_engine_kwargs_leave_sqlite_pool_defaults"`
2. tentativa de `docker compose -f docker-compose.yml config -q`
3. tentativa de `docker compose -f docker-compose.api.yml config -q`
4. snippet Python local para validar parse estrutural de `docker-compose.yml` e `docker-compose.api.yml`

## 7. Evidencias geradas

1. testes focados passando sobre configuracao de pool e endpoint de diagnostico;
2. telemetria do endpoint de banco agora carregando tambem timeout, recycle e `pool_pre_ping`;
3. este relatorio versionado em `docs/incidents/2026-05-05-504-phase6-database-pool-hardening.md`.

## 8. Validacao executada

### 8.1 Testes focados

Resultado:

1. `3 passed`

Cobertura relevante:

1. o endpoint `/api/admin/diagnostics/database` continua funcional;
2. a configuracao explicita para Postgres efetivamente materializa `QueuePool` com `pool_size=6`, `max_overflow=2`, `pool_timeout=5` e `pool_recycle=1800`;
3. SQLite continua sem forcar esses overrides.

### 8.2 Checagem estatica

Os arquivos alterados ficaram sem erros de editor.

### 8.3 Validacao de compose

O parse com `docker compose config` nao pode ser executado neste ambiente porque o binario `docker` nao estava disponivel.

Fallback executado:

1. parse estrutural dos YAMLs via Python, confirmando que `docker-compose.yml` continua com `services: [app, db, forms-worker]`;
2. parse estrutural dos YAMLs via Python, confirmando que `docker-compose.api.yml` continua com `services: [api, db]`.

## 9. Resultado

Aprovado.

O pool deixou de depender de defaults implicitos que permitiam capacidade teorica acima do teto configurado no Postgres para a topologia atual da stack. A configuracao agora e explicita por papel de processo, observavel no endpoint de diagnostico e coerente com o runtime alvo de `2` workers HTTP mais `1` worker serial de Forms.

## 10. Rollback

Para desfazer apenas esta execucao:

1. remover os campos de configuracao de pool adicionados em `sistema/app/core/config.py`;
2. voltar `sistema/app/database.py` ao `create_engine(..., pool_pre_ping=True)` sem sizing explicito;
3. remover os env vars `DATABASE_POOL_*` de `docker-compose.yml` e `docker-compose.api.yml`;
4. reverter os testes e o schema de diagnostico desta passada.

## 11. Proximo passo recomendado

Executar o proximo prompt da Fase 6:

1. validar ganhos de backend e banco com medicoes antes/depois de latencia `p50/p95/p99` das rotas quentes e uso de conexoes em ambiente de preview ou producao controlada;
2. em paralelo, tratar a exposicao externa do Postgres na porta `5432`, que continua como risco operacional separado do sizing do pool.