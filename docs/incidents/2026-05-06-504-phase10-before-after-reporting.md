# Fase 10 - Relatorio automatizado antes/depois para carga e superficies relacionadas

## Objetivo executado

Foi adicionado o pipeline de comparacao antes/depois da Fase 10 no proprio runner de carga. Cada corrida agora pode preservar, no mesmo diretorio de artefatos:

1. resumo agregado do Locust;
2. snapshot antes da carga;
3. snapshot depois da carga;
4. relatorio Markdown e JSON com decisao automatica de aprovacao ou bloqueio.

## Cobertura do relatorio

O comparativo automatizado usa o que ja existe no produto e o que pode ser capturado localmente sem depender de stack externa:

1. throughput, falhas e latencias p50/p95/p99 do Locust;
2. readiness antes e depois pela rota `/api/health/ready`;
3. backlog e falhas da fila do Forms por `/api/admin/forms/queue/diagnostics`;
4. pool, latencia recente e conexoes do banco por `/api/admin/diagnostics/database`;
5. CPU e memoria do host quando o alvo e local e `psutil` esta disponivel.

Para alvo remoto, o runner grava explicitamente que CPU e memoria nao foram capturados automaticamente. Nesse caso, a evidencia operacional precisa ser anexada separadamente ao bundle da corrida.

## Regra de bloqueio

O relatorio passa a marcar a corrida como `blocked` quando ocorrer qualquer uma das condicoes abaixo:

1. `locust` retorna codigo nao zero;
2. o agregado do Locust nao e produzido;
3. existe falha HTTP durante a carga;
4. a aplicacao fica `unready` antes ou depois da carga;
5. o worker do Forms fica `stale`, para de rodar, ou backlog e falhas crescem ao mesmo tempo;
6. o banco cruza thresholds de alerta de pool, p95 de query ou conexoes ativas;
7. CPU ou memoria locais chegam a 90% ou mais.

Quando uma dessas condicoes aparece, o relatorio tambem aponta o artefato anterior que precisa ser usado como referencia de bloqueio:

1. `docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md` para gates de readiness e degradacao de runtime HTTP;
2. `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md` para Forms worker, backlog, banco e bundle de reversao;
3. `docs/incidents/2026-05-06-504-phase10-load-harness.md` para falha do proprio harness;
4. `docs/incidents/2026-05-05-504-phase5-burst-measurement.md` para comparacao com a superficie web original quando o perfil web nao produz carga valida.

## Comando operacional

Exemplo com perfil integrado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/run_phase10_load.py --profile integrated --base-url http://127.0.0.1:8000 --config scripts/load/phase10_integrated.example.json --users 24 --spawn-rate 6 --run-time 3m
```

Ao final, o diretorio da corrida passa a conter tambem:

1. `phase10_integrated_before_snapshot.json`
2. `phase10_integrated_after_snapshot.json`
3. `phase10_integrated_before_after.json`
4. `phase10_integrated_before_after.md`

## Validacao executada

Foi executada validacao automatizada do parser de CSV agregado e da decisao de bloqueio com fixtures locais em `tests/test_phase10_load_reporting.py`.

## Resultado

Aprovado para uso nas proximas corridas de homologacao.

## Limite conhecido

Sem um alvo HTTP real ativo, esta etapa valida a pipeline de comparacao e a logica de bloqueio, mas nao preenche um relatorio real de before/after da aplicacao. A primeira corrida de homologacao usando os perfis novos deve ser preservada como evidencia base desta fase.