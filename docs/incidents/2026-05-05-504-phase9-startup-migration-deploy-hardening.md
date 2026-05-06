# Fase 9 - Startup, migracao e deploy sem janelas frageis

## Objetivo executado

Foi separado o passo de migracao Alembic do processo HTTP do backend. O runtime `sistema.app.http_runtime` agora apenas constroi e executa o servidor Gunicorn/Uvicorn, enquanto os caminhos de deploy do app principal e da API isolada passaram a executar `alembic upgrade head` por meio de um servico dedicado `migrate` antes de recriar o processo HTTP.

## Hipotese ou risco atacado

O risco local atacado era este: manter `alembic upgrade head` dentro do entrypoint HTTP fazia o container de aplicacao acumular dois papeis diferentes, migracao de schema e boot do servidor. Isso ampliava a janela fragil de rollout, porque qualquer migracao lenta ou falha de schema podia atrasar ou impedir o bind do processo HTTP exatamente durante a recriacao do container de producao.

Com a separacao atual:

- a migracao falha antes da recriacao do processo HTTP;
- o boot HTTP deixa de depender implicitamente do tempo de migracao;
- o rollout fica mais previsivel para os dois caminhos de deploy que hoje publicam backend.

## Arquivos alterados

- `sistema/app/http_runtime.py`
- `docker-compose.yml`
- `docker-compose.api.yml`
- `deploy/deploy_do_ssh.ps1`
- `.github/workflows/deploy-oceandrive.yml`
- `scripts/deploy_launcher.py`
- `tests/test_api_flow.py`

## Comandos executados

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "http_runtime_builds_gunicorn_command_from_environment or http_runtime_execs_server_without_migration_preflight" -q
```

Validacao estrutural adicional dos Compose files via Python local:

```python
from pathlib import Path
import yaml
for relative_path in ('docker-compose.yml', 'docker-compose.api.yml'):
    with Path(relative_path).open('r', encoding='utf-8') as handle:
        yaml.safe_load(handle)
```

## Evidencias geradas

- este relatorio: `docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md`

## Validacao executada

1. teste focado do runtime HTTP atualizado em `tests/test_api_flow.py`;
2. parse real dos arquivos `docker-compose.yml` e `docker-compose.api.yml` com `yaml.safe_load`;
3. diagnostico do editor nos arquivos alterados.

## Resultado

Parcialmente aprovado.

A fatia principal foi implementada e validada localmente:

- o runtime HTTP nao executa mais migracao;
- os dois Compose files agora expõem um servico `migrate` dedicado;
- os caminhos de deploy do backend principal e da API isolada passaram a chamar a migracao antes da recriacao do processo HTTP;
- o teste focado do runtime passou (`2 passed`).

Limitacao desta execucao:

- o ambiente local desta sessao nao possui CLI `docker`, entao a validacao com `docker compose config` e uma execucao real de `docker compose run --rm migrate` nao puderam ser executadas aqui.

Observacao adicional:

- o editor ainda marca a referencia `secrets.OCEAN_APP_ENV_B64` no workflow como contexto potencialmente invalido, mas isso reflete a ausencia desse secret no ambiente atual do repositorio, nao um erro de sintaxe do YAML; o step continua protegido por `if: env.OCEAN_APP_ENV_B64 != ''`.

## Rollback

Para desfazer apenas esta execucao:

1. restaurar `sistema.app.http_runtime` para voltar a rodar `python -m alembic upgrade head` antes do `execv` do servidor;
2. remover o servico `migrate` de `docker-compose.yml` e `docker-compose.api.yml`;
3. remover as chamadas `docker compose run --rm --no-deps migrate` dos caminhos de deploy alterados;
4. restaurar o teste do runtime para o contrato anterior.

Rollback operacional recomendado:

- so usar esse rollback se o novo fluxo impedir a subida da stack;
- preservar logs do passo `migrate` antes de qualquer reversao;
- nao improvisar restart cego do host para mascarar falha de migracao.

## Proximo passo recomendado

Executar a proxima acao da Fase 9: endurecer o deploy completo com checkpoints explicitos de build, migracao, subida do runtime HTTP, validacao local de health e validacao publica antes da exposicao final do trafego.