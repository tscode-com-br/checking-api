# Validacao de consistencia multiworker - Fase 3 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: bloqueado.
- Autorizacao de rollout multiworker: nao autorizada.
- Objetivo desta etapa: executar um teste controlado com mais de um processo HTTP, abrir sessoes do admin e do transport, gerar eventos publicados por workers diferentes e provar que os streams continuam coerentes.

## 2. Objetivo executado

Foi adicionado um harness E2E dedicado em `tests/test_multiworker_realtime_postgres.py` para validar o caminho real do barramento cross-worker com:

1. dois processos HTTP Uvicorn independentes;
2. um stream do admin conectado em um processo;
3. um stream do transport conectado no outro processo;
4. eventos publicados alternadamente por processos diferentes via `POST /api/admin/auth/change-password`;
5. verificacao de que ambos os streams recebem `reason=event` em cada lado.

O harness foi executado localmente no workspace atual para determinar se a prova podia ser obtida neste ambiente.

## 3. Hipotese ou risco atacado

Hipotese validada nesta etapa:

- se dois processos HTTP distintos apontarem para o mesmo Postgres real, o barramento `LISTEN/NOTIFY` implementado em `sistema/app/services/admin_updates.py` deve propagar os eventos entre processos e manter coerentes os streams `GET /api/admin/stream` e `GET /api/transport/stream`.

Risco operacional atacado:

- habilitar multiworker sem prova executavel de coerencia cross-worker faria o rollout depender de inferencia a partir de testes locais em SQLite, o que nao cobre o barramento real adotado para producao.

## 4. Arquivos alterados

- `tests/test_multiworker_realtime_postgres.py`
- `docs/incidents/2026-05-04-504-phase3-multiworker-validation.md`

## 5. Comandos executados

1. Verificacao de pre-requisitos locais:

```powershell
foreach ($name in 'docker','postgres','initdb','pg_ctl','psql') { $cmd = Get-Command $name -ErrorAction SilentlyContinue; if ($null -ne $cmd) { Write-Output ("{0}`t{1}" -f $name, $cmd.Source) } else { Write-Output ("{0}`t<missing>" -f $name) } }
```

2. Execucao padrao do harness:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_multiworker_realtime_postgres.py -s
```

3. Execucao de desambiguacao apontando para o host Compose padrao `db`:

```powershell
$env:CHECKCHECK_MULTIWORKER_DATABASE_URL = 'postgresql+psycopg://postgres:postgres@db:5432/checking'; c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_multiworker_realtime_postgres.py -s
```

## 6. Evidencias geradas

- `tests/test_multiworker_realtime_postgres.py`: harness executavel da validacao multiworker.
- `docs/incidents/2026-05-04-504-phase3-multiworker-validation.md`: consolidacao desta execucao.
- Evidencia observada no ambiente atual:
  - `docker`, `postgres`, `initdb`, `pg_ctl` e `psql` nao existem no PATH local deste workspace.
  - a execucao sem `CHECKCHECK_MULTIWORKER_DATABASE_URL` terminou em `skip`, bloqueando falso positivo.
  - a execucao com `CHECKCHECK_MULTIWORKER_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/checking` falhou ainda na etapa de `alembic upgrade head` com `psycopg.OperationalError: [Errno 11001] getaddrinfo failed`, provando que nao existe um Postgres acessivel em `db:5432` neste ambiente.

## 7. Validacao executada

### 7.1 Resultado da verificacao de pre-requisitos

Saida objetiva:

```text
docker  <missing>
postgres        <missing>
initdb  <missing>
pg_ctl  <missing>
psql    <missing>
```

### 7.2 Resultado do harness sem URL PostgreSQL real

Saida objetiva:

```text
collected 1 item
tests\test_multiworker_realtime_postgres.py s
============================= 1 skipped in 0.10s =============================
```

Interpretacao:

- o gate ficou fechado corretamente porque nao havia backend PostgreSQL real configurado para o teste.

### 7.3 Resultado do harness com URL Compose padrao

Falha objetiva:

```text
psycopg.OperationalError: [Errno 11001] getaddrinfo failed
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) [Errno 11001] getaddrinfo failed
```

Interpretacao:

- o workspace atual nao enxerga um Postgres real no host `db`, logo o caminho `LISTEN/NOTIFY` nao pode ser provado localmente aqui.

## 8. Resultado

- bloqueado.
- nao existe prova executavel, neste ambiente atual, de coerencia multiworker com mais de um processo HTTP e barramento PostgreSQL real.
- por contrato desta fase, o rollout multiworker permanece nao autorizado.

## 9. Rollback

Esta execucao nao alterou runtime de producao, host, Docker, Nginx nem banco de producao.

Rollback local, se desejado:

1. remover `tests/test_multiworker_realtime_postgres.py`;
2. remover `docs/incidents/2026-05-04-504-phase3-multiworker-validation.md`.

## 10. Proximo passo recomendado

1. disponibilizar um Postgres real acessivel ao workspace executor desta fase, seja por Docker funcional, binarios locais de PostgreSQL ou ambiente remoto de homologacao com credenciais aprovadas;
2. exportar `CHECKCHECK_MULTIWORKER_DATABASE_URL` para esse banco;
3. rerodar `pytest tests/test_multiworker_realtime_postgres.py -s`;
4. somente autorizar rollout multiworker se esse teste passar integralmente.

## 11. Conclusao tecnica

O repo agora possui um harness especifico para provar o caso exigido pela checklist: dois processos HTTP reais, sessoes do admin e do transport, eventos emitidos em workers diferentes e verificacao do refresh SSE correspondente.

Entretanto, a prova nao foi obtida neste workspace porque falta um Postgres real acessivel para exercitar o barramento `LISTEN/NOTIFY`. Como o barramento escolhido para producao depende exatamente desse backend, qualquer conclusao positiva aqui seria especulativa. Portanto, o rollout multiworker permanece bloqueado ate execucao bem-sucedida desse harness em ambiente com PostgreSQL real.