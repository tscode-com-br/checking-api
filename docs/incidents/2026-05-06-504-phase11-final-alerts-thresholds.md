# Alertas e thresholds finais - Fase 11 - incidente 504 de 2026-05-06

## Objetivo executado

Foi consolidada a lista operacional final de alertas obrigatorios para o rollout e para a operacao recorrente do incidente `504`, transformando os sinais entregues nas fases anteriores em thresholds, janelas e acoes esperadas.

## Hipotese ou risco atacado

O risco atacado nesta etapa era este: os sinais tecnicos ja existem no repo, mas sem um conjunto final de alertas obrigatorios a operacao continuaria reagindo tarde demais, especialmente em cenarios de `5xx` sustentado, backlog do Forms, saturacao de banco, `unhealthy` do app, pressao de CPU/memoria e drift silencioso do edge.

## Arquivos alterados

- `docs/incidents/2026-05-06-504-phase11-final-alerts-thresholds.md`

## Comandos executados

Nenhum comando de producao foi executado nesta etapa. Os thresholds abaixo foram consolidados a partir dos diagnosticos e criterios de bloqueio ja versionados.

## Evidencias geradas

- este relatorio versionado: `docs/incidents/2026-05-06-504-phase11-final-alerts-thresholds.md`

## Validacao executada

1. revisao do pacote minimo da Fase 1;
2. revisao da politica de auto-recuperacao da Fase 4;
3. revisao do bloco de decisao `blocked` do before/after da Fase 10.

## Resultado

Aprovado em escopo de repo como pacote final de rollout.

## Regra de leitura deste pacote

1. Estes sao os thresholds finais obrigatorios para o programa atual.
2. Onde a stack central de monitoracao ainda nao estiver pronta, usar o fallback operacional do runbook da Fase 11.
3. Qualquer alerta `critical` aberto durante rollout congela a onda atual ate evidencia e decisao manual.

## 1. Alertas `critical` imediatos

| Sinal | Fonte | Janela | Threshold | Acao esperada |
| --- | --- | --- | --- | --- |
| App `unhealthy` | `docker inspect` / `docker compose ps` | imediata | qualquer `Health.Status=unhealthy` no `app` | congelar rollout, comparar saude local/publica, coletar bundle e decidir restart de API apenas se banco estiver saudavel |
| Banco `unhealthy` | `docker inspect` / `docker compose ps` | imediata | qualquer `Health.Status=unhealthy` no `db` | parar em modo evidencia; nao reiniciar stack inteira sem bundle minimo |
| `5xx` em `/api/health` | `checking.http` ou access log | 2 min | qualquer `5xx` ou 2 falhas consecutivas de health publico | abrir incidente, congelar rollout e diferenciar upstream vs edge |
| Forms worker parado com backlog | `/api/admin/forms/queue/diagnostics` | imediata | `worker.running=false` e `backlog_count > 0` | congelar rollout; se API e banco estiverem verdes, reiniciar apenas `forms-worker` apos bundle |
| Pool esgotado | `/api/admin/diagnostics/database` | imediata | `pool.usage_ratio >= 1.0` | congelar rollout e abrir incidente de banco; nao seguir para outra onda |
| Espera de conexao elevada | `/api/admin/diagnostics/database` | 1 min | `waiting_database_connections >= 3` | tratar como incidente de banco/pool; parar mutacoes e capturar evidencia |
| CPU alta sustentada | monitoracao ou fallback local | 5 min | CPU `> 90%` do host ou container da app | congelar rollout, comparar com backlog/forms e burst de cliente |
| Memoria alta sustentada | monitoracao ou fallback local | 5 min | memoria `> 90%` ou memoria livre `< 200 MB` | congelar rollout; verificar risco de OOM e backlog pesado |

## 2. Alertas `warning` obrigatorios

| Sinal | Fonte | Janela | Threshold | Acao esperada |
| --- | --- | --- | --- | --- |
| Shell publica indisponivel | smoke local/publico, Nginx access log, monitor sintatico | 2 min | qualquer `404/5xx` ou ausencia do marcador esperado em `/checking/user`, `/checking/admin` ou `/checking/transport` | congelar rollout, tratar como regressao de edge/publicacao estatica e nao prosseguir para carga |
| `5xx` em rotas criticas request/response | `checking.http` ou access log | 5 min | `>= 5` respostas `5xx` ou taxa `> 2%` em `/api/web/check/state`, `/api/mobile/state`, `/api/admin/checkin`, `/api/admin/checkout`, `/api/admin/projects` | investigar degradacao e segurar a proxima onda ate confirmar causa |
| `5xx` critico em rotas criticas | `checking.http` ou access log | 5 min | `>= 10` respostas `5xx` ou taxa `> 5%` nas mesmas rotas | promover para incidente critico e considerar rollback da onda atual |
| Erro ou churn de stream | `checking.http` / logs de edge | 5 min | `>= 3` falhas ou reconexoes anormais em `/api/admin/stream` ou `/api/transport/stream` | verificar edge, runtime HTTP e coerencia de SSE antes de seguir |
| Stream critico | `checking.http` / logs de edge | 5 min | `>= 6` falhas ou reconexoes anormais em streams | congelar rollout e revalidar runtime/edge |
| Backlog do Forms | `/api/admin/forms/queue/diagnostics` | 5 min | `backlog_count >= 10` ou `oldest_backlog_age_seconds > 120` | acompanhar worker, verificar se API segue pronta e impedir proxima onda sem alivio |
| Backlog critico do Forms | `/api/admin/forms/queue/diagnostics` | 5 min | `backlog_count >= 25` ou `oldest_backlog_age_seconds > 300` | tratar como gatilho de incidente; avaliar restart isolado do worker |
| Latencia alta em `/api/health` | `checking.http` | 10 min warning / 5 min critical | warning `p95 > 300 ms` ou `p99 > 800 ms`; critical `p95 > 800 ms` ou `p99 > 1500 ms` | investigar runtime HTTP e banco |
| Latencia alta em `state` | `checking.http` | 10 min warning / 5 min critical | warning `p95 > 750 ms` ou `p99 > 1500 ms`; critical `p95 > 1500 ms` ou `p99 > 3000 ms` em `/api/web/check/state` e `/api/mobile/state` | segurar rollout e reabrir analise de burst/hot path |
| Latencia alta em presenca admin | `checking.http` | 10 min warning / 5 min critical | warning `p95 > 1000 ms` ou `p99 > 2000 ms`; critical `p95 > 2000 ms` ou `p99 > 4000 ms` em `/api/admin/checkin` e `/api/admin/checkout` | rever banco, edge e concorrencia |
| Latencia alta em `/api/admin/projects` | `checking.http` | 10 min warning / 5 min critical | warning `p95 > 1200 ms` ou `p99 > 2500 ms`; critical `p95 > 2500 ms` ou `p99 > 5000 ms` | verificar serializacao e query plan |
| Conexoes ativas elevadas | `/api/admin/diagnostics/database` | 5 min | warning `active_database_connections >= 24`; critical `active_database_connections >= 32` | segurar rollout e investigar pool/rotas quentes |
| Espera leve no banco | `/api/admin/diagnostics/database` | 2 min | `waiting_database_connections >= 1` | tratar como precoce de saturacao, antes de virar critico |
| `idle in transaction` | `/api/admin/diagnostics/database` | 5 min | `idle_in_transaction_connections >= 1` | investigar leak transacional ou fluxo administrativo preso |
| p95 de query alto | `/api/admin/diagnostics/database` | 10 min warning / 5 min critical | warning `recent_p95_query_ms > 150`; critical `recent_p95_query_ms > 300` | reabrir Fase 6 antes de avancar |
| `RestartCount` anormal | `docker inspect` | 30 min | warning `+1`; critical `>= 2` | coletar bundle e verificar se a causa esta em runtime, worker ou edge |
| Memoria alta sustentada | monitoracao ou fallback local | 10 min | warning memoria `> 80%` ou memoria livre `< 400 MB` | investigar headroom, Playwright e crescimento de backlog |
| CPU alta sustentada | monitoracao ou fallback local | 10 min | warning CPU `> 80%` | investigar burst de cliente, forms ou carga administrativa |

## 3. Alertas adicionais recomendados

| Sinal | Fonte | Janela | Threshold | Acao esperada |
| --- | --- | --- | --- | --- |
| Drift de edge | `deploy/nginx/validate_checking_edge_final.sh` | por deploy e diario | qualquer diferenca critica entre `nginx -T` e arquivos versionados | bloquear deploy seguinte e reconciliar edge antes da proxima onda |
| IA de transporte habilitada fora de gate | `.env`, deploy script e health operacional | imediata | `TRANSPORT_AI_ENABLED=true` sem `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE` ou sem validacao dedicada | tratar como desvio operacional; desfazer e abrir incidente |

## 4. Fallback operacional se a monitoracao central nao estiver pronta

1. `docker inspect checkcheck-app-1 --format '{{json .State}}'`
2. `docker inspect checkcheck-db-1 --format '{{json .State}}'`
3. `docker inspect checkcheck-forms-worker-1 --format '{{json .State}}'`
4. `docker logs --since 10m checkcheck-app-1 | rg 'checking.http|checking.forms_queue|checking.db'`
5. `curl -sS -b /tmp/checkcheck_admin.cookies http://127.0.0.1:8000/api/admin/forms/queue/diagnostics`
6. `curl -sS -b /tmp/checkcheck_admin.cookies http://127.0.0.1:8000/api/admin/diagnostics/database`
7. `grep ' 5[0-9][0-9] ' /var/log/nginx/access.log | tail -n 200`
8. `grep 'upstream timed out' /var/log/nginx/error.log | tail -n 100`
9. `curl -fsS https://tscode.com.br/checking/user | grep -F 'checkForm'`
10. `curl -fsS https://tscode.com.br/checking/admin | grep -F 'Checking Admin'`
11. `curl -fsS https://tscode.com.br/checking/transport | grep -F 'Checking Transport'`

## Rollback

Rollback desta etapa documental:

1. remover `docs/incidents/2026-05-06-504-phase11-final-alerts-thresholds.md`;
2. voltar temporariamente para `docs/incidents/2026-05-04-504-phase1-minimum-alert-package.md` como pacote base.

## Proximo passo recomendado

Configurar estes thresholds na stack de monitoracao real ou, na ausencia dela, formalizar o fallback operacional do runbook como checklist diaria de janela e pos-deploy.