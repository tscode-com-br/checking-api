# Runbook operacional final - Fase 11 - incidente 504 de 2026-05-06

## Objetivo executado

Foi consolidado o runbook operacional final para verificar saude do host, API, worker do Forms, Nginx, banco e dashboard Transport, alem de registrar quando reiniciar apenas o worker, quando reiniciar apenas a API, quando parar para coleta de evidencias e como validar drift no edge.

## Hipotese ou risco atacado

O risco atacado nesta etapa era este: sem um runbook unico e objetivo, a equipe continuaria dependente de intuicao, reboot amplo e lembranca informal para diferenciar falha isolada de worker, falha do runtime HTTP, drift do edge, pressao de banco ou regressao do dashboard Transport.

## Arquivos alterados

- `docs/incidents/2026-05-06-504-phase11-operational-runbook.md`

## Comandos executados

Nenhum comando de host foi executado nesta etapa. Os comandos abaixo foram consolidados a partir dos scripts e relatorios ja versionados no repo.

## Evidencias geradas

- este runbook versionado: `docs/incidents/2026-05-06-504-phase11-operational-runbook.md`

## Validacao executada

1. revisao cruzada de `docker-compose.yml`, `deploy/maintenance/run_app_rollout.sh` e `deploy/nginx/verify_checking_edge_cutover.sh`;
2. revisao dos relatorios de auto-recuperacao, rollback de deploy, edge e observabilidade;
3. revisao dos routers `admin.py` e `transport.py` para confirmar os endpoints operacionais usados neste runbook.

## Resultado

Aprovado em escopo de repo.

## 1. Regras de seguranca antes de agir

1. Se nao houver acesso SSH, cookie administrativo valido ou credenciais de Transport, parar e registrar bloqueio. Nao inventar saude remota.
2. Nao reiniciar host, Nginx, banco ou stack inteira antes de congelar evidencia minima.
3. Se o banco estiver `unhealthy`, se houver `OOMKilled` ou se API e worker falharem juntos, parar em modo coleta de evidencia. Nao tratar isso como falha isolada.
4. Se a saude local do upstream estiver verde e a publica estiver vermelha, tratar primeiro como suspeita de edge/drift, nao de API.
5. Durante este programa, manter `TRANSPORT_AI_ENABLED=false` e `APP_WORKERS=1` em producao, salvo nova evidencia explicita aprovando mudanca.

## 2. Varredura rapida em 5 minutos

No host da stack principal:

```bash
export STACK_DIR="/root/checkcheck"
cd "$STACK_DIR"

date -u
uptime
free -m
df -h /
docker compose ps
curl -i http://127.0.0.1:8000/api/health
curl -i http://127.0.0.1:8000/api/health/ready
curl -i https://tscode.com.br/api/health
```

Interpretacao minima:

1. `app`, `db` e `forms-worker` precisam aparecer `Up` e, quando houver healthcheck, `healthy`.
2. `GET /api/health` responde saude geral; `GET /api/health/ready` responde gate binario de entrada de trafego.
3. Se o local estiver `200` e o publico nao, tratar como problema de edge, Nginx ou roteamento.

## 3. Como verificar cada superficie

## 3.1 Host

Comandos:

```bash
date -u
uptime
hostnamectl
free -m
df -h /
nproc
docker compose ps
docker stats --no-stream app db forms-worker
```

O que procurar:

1. CPU sustentada acima de `80%` ou memoria livre abaixo do piso operacional.
2. Disco perto do limite ou comportamento anormal em `/var/lib/containerd`.
3. `RestartCount` subindo sem rollout em curso.

## 3.2 API HTTP

Comandos:

```bash
curl -i http://127.0.0.1:8000/api/health
curl -i http://127.0.0.1:8000/api/health/ready
curl -i https://tscode.com.br/api/health
curl -i http://127.0.0.1:8000/checking/user
curl -i http://127.0.0.1:8000/checking/admin
curl -i http://127.0.0.1:8000/checking/transport
docker inspect checkcheck-app-1 --format '{{json .State}}'
docker compose logs --tail=200 app
```

O que procurar:

1. `ready` precisa estar verde antes de aceitar trafego novo.
2. `Status=running` sem `Health.Status=healthy` nao basta.
3. Logs `checking.http` com `5xx`, latencia alta ou falha concentrada em rota critica.
4. `static_sites` verde em `/api/health/ready` nao substitui a prova funcional das shells publicas; se `/checking/user`, `/checking/admin` ou `/checking/transport` responderem `404`, tratar como regressao real de edge ou publish estatico.

## 3.3 Worker do Forms

Comandos:

```bash
docker inspect checkcheck-forms-worker-1 --format '{{json .State}}'
docker compose logs --tail=200 forms-worker
docker compose exec forms-worker python -m sistema.app.forms_worker_healthcheck
```

Consulta autenticada da fila:

```bash
curl -sS -c /tmp/checkcheck_admin.cookies \
  -H 'Content-Type: application/json' \
  -d '{"chave":"'$CHECKCHECK_ADMIN_KEY'","senha":"'$CHECKCHECK_ADMIN_PASSWORD'"}' \
  http://127.0.0.1:8000/api/admin/auth/login

curl -sS -b /tmp/checkcheck_admin.cookies \
  http://127.0.0.1:8000/api/admin/forms/queue/diagnostics
```

O que procurar:

1. `worker.running=true` quando `FORMS_QUEUE_ENABLED=true`.
2. `backlog_count`, `oldest_backlog_age_seconds`, `failed_count` e `worker.last_error`.
3. `stale=true` ou backlog crescendo junto com falhas indicam que nao e so problema cosmetico do worker.

## 3.4 Nginx e edge

Comandos:

```bash
nginx -t
tail -n 200 /var/log/nginx/error.log
tail -n 200 /var/log/nginx/access.log
grep ' 5[0-9][0-9] ' /var/log/nginx/access.log | tail -n 200
grep 'upstream timed out' /var/log/nginx/error.log | tail -n 100
```

Validacao versionada do edge:

```bash
bash deploy/nginx/verify_checking_edge_cutover.sh --mode full --nginx-test
```

Smoke adicional obrigatorio das shells publicas:

```bash
curl -fsS https://tscode.com.br/checking/user | grep -F 'checkForm'
curl -fsS https://tscode.com.br/checking/admin | grep -F 'Checking Admin'
curl -fsS https://tscode.com.br/checking/transport | grep -F 'Checking Transport'
```

O que procurar:

1. `upstream timed out`, `5xx` recorrente e diferenca entre saude local/publica.
2. HTML esperado nas superficies `/checking/admin`, `/checking/user` e `/checking/transport`.
3. Falha de `nginx -t` ou zonas `limit_req_zone` ausentes significam edge inconsistente.

## 3.5 Banco e pool

Comandos:

```bash
docker inspect checkcheck-db-1 --format '{{json .State}}'
docker compose exec db pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-checking}
docker compose logs --tail=200 db
```

Consulta autenticada de diagnostico:

```bash
curl -sS -b /tmp/checkcheck_admin.cookies \
  http://127.0.0.1:8000/api/admin/diagnostics/database
```

O que procurar:

1. `pool.usage_ratio`, `pool.checked_out`, `latency.recent_p95_query_ms`.
2. `active_database_connections`, `waiting_database_connections` e `idle_in_transaction_connections`.
3. Banco `healthy` nao compensa pool saturado ou query lenta sustentada.

## 3.6 Dashboard Transport

Verificacao publica minima:

```bash
curl -fsS https://tscode.com.br/checking/transport | grep -F 'Checking Transport'
```

Verificacao autenticada local:

```bash
curl -sS -c /tmp/checkcheck_transport.cookies \
  -H 'Content-Type: application/json' \
  -d '{"chave":"'$TRANSPORT_KEY'","senha":"'$TRANSPORT_PASSWORD'"}' \
  http://127.0.0.1:8000/api/transport/auth/verify

curl -sS -b /tmp/checkcheck_transport.cookies \
  http://127.0.0.1:8000/api/transport/auth/session

curl -sS -b /tmp/checkcheck_transport.cookies \
  "http://127.0.0.1:8000/api/transport/dashboard?service_date=$(date +%F)&route_kind=home_to_work"

curl -N -b /tmp/checkcheck_transport.cookies --max-time 20 \
  http://127.0.0.1:8000/api/transport/stream
```

O que procurar:

1. Sessao autenticada com `authenticated=true`.
2. Dashboard carregando sem rajadas repetidas de refresh.
3. Stream entregando `data: {"reason": "connected"}` seguido apenas dos eventos esperados.

## 4. Quando reiniciar apenas o worker do Forms

Reiniciar apenas `forms-worker` quando todos os pontos abaixo forem verdadeiros:

1. `forms-worker` esta `unhealthy` ou `stale` de forma sustentada;
2. a API continua `ready` localmente;
3. o banco continua `healthy`;
4. nao houve `OOMKilled` do worker;
5. o worker nao entrou em loop de restart;
6. o problema esta isolado ao consumo da fila.

Comando operacional minimo, depois da coleta de evidencia:

```bash
cd /root/checkcheck
docker compose restart forms-worker
```

Preferencia operacional quando o remediador estiver instalado:

```bash
python3 deploy/maintenance/checkcheck_auto_recovery.py \
  --stack-dir /root/checkcheck \
  --compose-file docker-compose.yml
```

## 5. Quando reiniciar apenas a API

Reiniciar apenas a API quando todos os pontos abaixo forem verdadeiros:

1. `GET /api/health/ready` falha de forma sustentada ou o container HTTP ficou `unhealthy`;
2. o banco continua `healthy`;
3. o worker do Forms nao esta falhando ao mesmo tempo;
4. nao houve `OOMKilled` da API;
5. nao existe suspeita de drift do edge como causa primaria.

Reinicio simples do mesmo release:

```bash
cd /root/checkcheck
docker compose restart app
```

Recriacao segura do runtime com o fluxo versionado:

```bash
cd /root/checkcheck
export CHECKCHECK_APP_IMAGE="ghcr.io/tscode-com-br/checkcheck-app:$(cat .deploy-release)"
bash deploy/maintenance/run_app_rollout.sh \
  --phase start \
  --deploy-dir /root/checkcheck
```

## 6. Quando parar para coleta de evidencia antes de qualquer reboot maior

Parar em modo coleta de evidencia se ocorrer qualquer uma destas condicoes:

1. banco `unhealthy`;
2. `OOMKilled` da API ou do worker do Forms;
3. API e worker falhando juntos;
4. `RestartCount` ou budget de restart automatico ja esgotado;
5. health local verde e health publico vermelho;
6. falha de migracao, boot ou Nginx com drift evidente;
7. backlog do Forms e falhas crescendo juntos;
8. conexoes de banco em espera ou latencia de query acima do threshold critico.

Bundle minimo antes de qualquer reboot maior:

```bash
export EVIDENCE_DIR="/root/checkcheck_incidents/$(date -u +%Y-%m-%dT%H%M%SZ)-phase11"
mkdir -p "$EVIDENCE_DIR"
cd /root/checkcheck

docker compose ps > "$EVIDENCE_DIR/00_compose_ps.txt" 2>&1
docker compose logs --tail=200 app > "$EVIDENCE_DIR/01_app_logs.txt" 2>&1 || true
docker compose logs --tail=200 forms-worker > "$EVIDENCE_DIR/02_forms_worker_logs.txt" 2>&1 || true
docker compose logs --tail=200 db > "$EVIDENCE_DIR/03_db_logs.txt" 2>&1 || true
curl -i -sS http://127.0.0.1:8000/api/health > "$EVIDENCE_DIR/04_local_health.txt" 2>&1 || true
curl -i -sS http://127.0.0.1:8000/api/health/ready > "$EVIDENCE_DIR/05_local_ready.txt" 2>&1 || true
curl -i -sS https://tscode.com.br/api/health > "$EVIDENCE_DIR/06_public_health.txt" 2>&1 || true
nginx -T > "$EVIDENCE_DIR/07_nginx_T.txt" 2>&1 || true
```

## 7. Como validar drift do edge

Validacao curta:

```bash
nginx -T > /tmp/checkcheck_nginx_active.txt
bash deploy/nginx/validate_checking_edge_final.sh \
  --evidence-dir /root/checkcheck_incidents/$(date -u +%Y-%m-%dT%H%M%SZ)-phase11-edge \
  --server-config /etc/nginx/sites-enabled/tscode.com.br.conf \
  --http-config-target /etc/nginx/conf.d/checkcheck-edge-http.conf
```

Drift critico existe quando qualquer um destes pontos acontece:

1. o bloco `server` ativo nao bate com `deploy/nginx/checking-edge-routes.conf`;
2. o include `http` nao bate com `deploy/nginx/checking-edge-http.conf`;
3. o host roteia simultaneamente para topologias diferentes sem isso estar versionado;
4. as URLs locais/publicas do runner deixam de responder com o texto esperado.

## 8. Onde consultar metricas, logs e artefatos ja introduzidos

1. Logs estruturados da API: `docker logs checkcheck-app-1 | rg 'checking.http|checking.forms_queue|checking.db'`.
2. Diagnostico da fila do Forms: `GET /api/admin/forms/queue/diagnostics`.
3. Diagnostico do banco e pool: `GET /api/admin/diagnostics/database`.
4. Bundle do auto-recovery: `auto_recovery_evidence/<compose>/...`.
5. Rollout versionado: `deploy/maintenance/run_app_rollout.sh`.
6. Rollback por superficie: `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md`.
7. Validacao final do edge: `deploy/nginx/validate_checking_edge_final.sh` e `deploy/nginx/verify_checking_edge_cutover.sh`.
8. Harness de carga e before/after: `scripts/run_phase10_load.py`, `docs/incidents/2026-05-06-504-phase10-load-harness.md` e `docs/incidents/2026-05-06-504-phase10-before-after-reporting.md`.
9. Ultima evidencia local bloqueada da Fase 10: `docs/artifacts/phase10/first-local-web-check-report-fixed/phase10_web_check_before_after.md` e `docs/artifacts/phase10/first-local-web-check-report-fixed/phase10_web_check.stderr.log`.

## Rollback

Rollback desta etapa documental:

1. remover `docs/incidents/2026-05-06-504-phase11-operational-runbook.md`;
2. voltar a usar os relatorios das Fases 1, 4, 7, 9 e 10 de forma separada.

## Proximo passo recomendado

Usar este runbook como referencia da Onda 0 em diante e anexar o primeiro bundle real de producao a partir dele.