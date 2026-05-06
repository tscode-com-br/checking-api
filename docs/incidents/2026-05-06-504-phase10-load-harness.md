# Fase 10 - Harness de carga para a superficie web de check e cenarios complementares

## Objetivo executado

Foi criado o harness de carga da Fase 10, iniciado pela superficie web de check e depois ampliado para cenarios isolados de admin, dashboard Transport, backlog do Forms e um perfil integrado. A implementacao entrega jornadas stateful repetiveis com `Locust`, parametrizadas por JSON e empacotadas com um runner versionado para execucao headless.

O fluxo coberto por esta primeira fatia replica a sequencia central do incidente:

1. abrir a shell publica em `/checking/user`;
2. consultar o status de autenticacao da chave;
3. registrar ou autenticar usuario quando necessario;
4. consultar estado e catalogo de projetos;
5. resolver localizacao;
6. enviar `checkin` e `checkout` em janelas curtas.

## Hipotese ou risco atacado

O risco local atacado nesta etapa e este: sem um harness de carga stateful e versionado, a Fase 10 ficaria dependente de curls soltos, browser manual ou scripts ad hoc que nao reproduzem a combinacao de page open, auth, state, location e submit que mais pressiona a superficie `/checking/user`.

Com este slice ampliado, a equipe ganha uma base repetivel para executar cada superficie de forma isolada e tambem em corrida integrada, sem perder a separacao operacional entre os cenarios.

Atualizacao desta mesma execucao para a Acao 2:

- foram adicionados perfis isolados para `admin`, `transport` e `forms-backlog`;
- foi adicionado um perfil `integrated` para combinar as quatro superficies no mesmo runner;
- cada perfil continua executavel de forma independente para evitar teste cego unico.

## Arquivos alterados

- `requirements-dev.txt`
- `scripts/load/phase10_support.py`
- `scripts/load/phase10_locustfile.py`
- `scripts/load/phase10_web_check.example.json`
- `scripts/load/phase10_admin.example.json`
- `scripts/load/phase10_transport.example.json`
- `scripts/load/phase10_forms_backlog.example.json`
- `scripts/load/phase10_integrated.example.json`
- `scripts/load/phase10_reporting.py`
- `scripts/run_phase10_load.py`
- `tests/test_phase10_load_harness.py`
- `tests/test_phase10_load_reporting.py`
- `docs/incidents/2026-05-06-504-phase10-load-harness.md`
- `docs/incidents/2026-05-06-504-phase10-before-after-reporting.md`

## Comandos previstos para uso do harness

Execucao tipica local ou em homologacao:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/run_phase10_load.py --profile web-check --base-url http://127.0.0.1:8000 --config scripts/load/phase10_web_check.example.json --users 20 --spawn-rate 5 --run-time 2m
```

Perfis adicionais:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/run_phase10_load.py --profile admin --base-url http://127.0.0.1:8000 --config scripts/load/phase10_admin.example.json --users 4 --spawn-rate 2 --run-time 2m
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/run_phase10_load.py --profile transport --base-url http://127.0.0.1:8000 --config scripts/load/phase10_transport.example.json --users 4 --spawn-rate 2 --run-time 2m
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/run_phase10_load.py --profile forms-backlog --base-url http://127.0.0.1:8000 --config scripts/load/phase10_forms_backlog.example.json --users 16 --spawn-rate 8 --run-time 2m
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/run_phase10_load.py --profile integrated --base-url http://127.0.0.1:8000 --config scripts/load/phase10_integrated.example.json --users 24 --spawn-rate 6 --run-time 3m
```

Artefatos produzidos por corrida:

1. CSVs do Locust;
2. HTML report;
3. stdout/stderr da execucao;
4. comando exato usado para a corrida;
5. snapshot antes da carga;
6. snapshot depois da carga;
7. relatorio comparativo Markdown e JSON.

## Evidencias geradas

- este relatorio: `docs/incidents/2026-05-06-504-phase10-load-harness.md`
- pipeline de before/after: `docs/incidents/2026-05-06-504-phase10-before-after-reporting.md`

## Validacao executada

Foi validado de forma focada:

1. `tests/test_phase10_load_harness.py` com `6 passed`;
2. `tests/test_phase10_load_reporting.py` com fixtures locais para parser e decisao de bloqueio;
3. `scripts/run_phase10_load.py --profile integrated --base-url http://127.0.0.1:8000 --help`;
4. `get_errors` sem problemas nos arquivos alterados.

## Resultado

Aprovado para a fase de homologacao com alvo HTTP real.

## Rollback

Para desfazer apenas esta execucao:

1. remover `locust` de `requirements-dev.txt`;
2. remover os arquivos `scripts/load/phase10_support.py`, `scripts/load/phase10_locustfile.py`, `scripts/load/phase10_web_check.example.json` e `scripts/run_phase10_load.py`;
3. remover `tests/test_phase10_load_harness.py`;
4. remover `scripts/load/phase10_reporting.py` e `tests/test_phase10_load_reporting.py`;
5. remover `docs/incidents/2026-05-06-504-phase10-before-after-reporting.md`;
6. remover este relatorio.

## Proximo passo recomendado

Executar a primeira corrida de homologacao com alvo HTTP real e preservar o bundle completo de evidencia para servir como baseline antes/depois desta fase.