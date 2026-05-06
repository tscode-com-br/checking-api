# Fase 9 - Rollback de deploy para runtime, edge, worker e startup

## Objetivo executado

Foi consolidada uma matriz versionada de rollback de deploy para as quatro superficies que hoje podem ampliar blast radius operacional neste programa: runtime HTTP, edge Nginx, worker do Forms e startup/migracao. O foco desta execucao foi transformar rollback em procedimento reproduzivel por arquivo e por comando, sem depender de memoria da equipe nem de decisoes improvisadas no host.

## Hipotese ou risco atacado

O risco atacado nesta etapa era este: as mudancas ja entregues no repo possuem criterio de rollback parcial em relatorios separados, mas ainda nao existia um contrato unico que dissesse, para cada superficie de deploy, tres coisas ao mesmo tempo:

1. qual evidencia precisa ser preservada antes da reversao;
2. qual e o passo exato de reversao;
3. qual teste confirma que o rollback voltou a um estado operacional valido.

Sem essa consolidacao, uma falha de rollout poderia empurrar a equipe para rollback cego, especialmente nas superficies que combinam imagem versionada, `.env`, Nginx ativo no host, fila persistida e migracao Alembic.

## Arquivos alterados

- `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md`

## Comandos executados

Nenhum comando de producao foi executado nesta etapa. A execucao foi deliberadamente documental e versionada, baseada na leitura das superficies que hoje controlam deploy e rollback:

- `docker-compose.yml`
- `sistema/app/http_runtime.py`
- `deploy/maintenance/run_app_rollout.sh`
- `deploy/deploy_do_ssh.ps1`
- `.github/workflows/deploy-oceandrive.yml`
- `deploy/nginx/manage_checking_edge_cutover.sh`
- `deploy/nginx/verify_checking_edge_cutover.sh`
- `deploy/nginx/validate_checking_edge_final.sh`
- `docs/incidents/2026-05-04-504-phase2-forms-worker-separation.md`
- `docs/incidents/2026-05-04-504-phase3-runtime-http-implementation.md`
- `docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md`

## Evidencias geradas

- este relatorio versionado: `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md`

## Validacao executada

1. revisao cruzada das superficies atuais de deploy, runtime, worker e edge no repo;
2. checagem de consistencia com os relatorios ja versionados das Fases 2, 3 e 9;
3. diagnostico do editor para este novo arquivo;
4. `git diff --check` neste arquivo apos a edicao.

## Resultado

Aprovado em escopo de repo.

Esta etapa nao alterou host, workflow em execucao, Nginx ativo nem containers de producao. O entregavel desta execucao e o contrato versionado de rollback abaixo, com pre-condicoes explicitas, passos de reversao copiaveis, testes de confirmacao e bloqueios obrigatorios para evitar rollback cego.

## Regras globais desta matriz

1. Nao reiniciar host, Nginx, banco ou containers antes de capturar a evidencia minima da superficie afetada.
2. Nao executar rollback de imagem ou de codigo se o estado do schema estiver desconhecido.
3. Nao executar rollback de worker se o estado da fila `forms_submissions` nao tiver sido preservado.
4. Nao executar rollback de edge se o caminho do arquivo ativo do `server {}` ou o backup criado no apply nao estiverem identificados.
5. Quando o rollback depender de um SHA anterior, usar sempre o ultimo release bom registrado em `.deploy-release` ou em artefato equivalente versionado da onda anterior.

## Diretoria recomendada de evidencias antes de qualquer rollback

No host, criar um diretorio por tentativa antes de reverter qualquer superficie:

```bash
export EVIDENCE_DIR="/root/checkcheck_incidents/$(date -u +%Y-%m-%dT%H%M%SZ)-phase9-rollback"
mkdir -p "$EVIDENCE_DIR"
cd /root/checkcheck
```

Bundle minimo comum a qualquer rollback de deploy:

```bash
{
  echo "TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "DEPLOY_RELEASE=$(cat .deploy-release 2>/dev/null || echo unknown)"
  echo "DEPLOY_RELEASE_API=$(cat .deploy-release-api 2>/dev/null || echo unknown)"
  docker compose ps
} > "$EVIDENCE_DIR/00_rollout_state.txt" 2>&1

curl -i -sS http://127.0.0.1:8000/api/health > "$EVIDENCE_DIR/01_local_api_health.txt" 2>&1 || true
curl -i -sS https://tscode.com.br/api/health > "$EVIDENCE_DIR/02_public_api_health.txt" 2>&1 || true
docker compose logs --tail=200 app > "$EVIDENCE_DIR/03_app_logs_tail.txt" 2>&1 || true
docker compose logs --tail=200 forms-worker > "$EVIDENCE_DIR/04_forms_worker_logs_tail.txt" 2>&1 || true
docker compose logs --tail=200 migrate > "$EVIDENCE_DIR/05_migrate_logs_tail.txt" 2>&1 || true
```

Se esse bundle minimo nao puder ser gerado, o rollback deve ser tratado como bloqueado ate a superficie ficar observavel o suficiente para reversao segura.

## Inventario das superficies cobertas

| Superficie | Arquivos/controladores atuais | Tipo de rollback esperado |
| --- | --- | --- |
| Runtime HTTP | `sistema/app/http_runtime.py`, `Dockerfile`, `deploy/docker/Dockerfile.api`, `docker-compose.yml`, `docker-compose.api.yml` | rollback de imagem ou reducao para single-worker |
| Startup/migracao | `docker-compose.yml`, `docker-compose.api.yml`, `deploy/maintenance/run_app_rollout.sh`, `.github/workflows/deploy-oceandrive.yml`, `deploy/deploy_do_ssh.ps1`, `scripts/deploy_launcher.py` | rollback da orquestracao de rollout ou retorno ao release anterior |
| Worker do Forms | `Dockerfile`, `docker-compose.yml`, `sistema/app/forms_worker_main.py`, `sistema/app/main.py` | retorno do consumo ao processo HTTP anterior ou ao ultimo release bom |
| Edge Nginx | `deploy/nginx/checking-edge-routes.conf`, `deploy/nginx/checking-edge-http.conf`, `deploy/nginx/manage_checking_edge_cutover.sh` | restauracao do backup validado do bloco `server {}` e do include `http {}` |

## 1. Rollback de runtime HTTP

### 1.1 Quando este rollback e aceitavel

Use este rollback quando o problema estiver no runtime HTTP em si, por exemplo:

- regressao introduzida por `gunicorn`/`uvicorn.workers.UvicornWorker`;
- comportamento incorreto com `APP_WORKERS>1`;
- degradacao de health/readiness atribuida ao processo HTTP e nao ao edge ou ao worker do Forms.

Se o problema for apenas coerencia de realtime cross-worker, o rollback minimo e reduzir `APP_WORKERS` para `1` primeiro. Nao e necessario derrubar de imediato todo o runtime versionado.

### 1.2 Evidencia obrigatoria antes de reverter runtime

Preservar, no minimo:

```bash
cd /root/checkcheck
docker compose ps > "$EVIDENCE_DIR/runtime_01_compose_ps.txt" 2>&1
docker compose logs --tail=300 app > "$EVIDENCE_DIR/runtime_02_app_logs.txt" 2>&1 || true
docker inspect $(docker compose ps -q app) > "$EVIDENCE_DIR/runtime_03_app_inspect.json" 2>&1 || true
curl -i -sS http://127.0.0.1:8000/api/health/ready > "$EVIDENCE_DIR/runtime_04_local_ready.txt" 2>&1 || true
curl -i -sS https://tscode.com.br/api/health > "$EVIDENCE_DIR/runtime_05_public_health.txt" 2>&1 || true
```

Se o gatilho do rollback for SSE/realtime, preservar tambem pelo menos uma evidencia do sintoma, por exemplo um log do app mostrando perda/duplicacao de evento ou captura objetiva do cliente administrativo afetado.

### 1.3 Rollback minimo de runtime para single-worker

Quando o defeito for de multiworker/realtime e o release atual ainda precisar permanecer publicado:

1. editar o `.env` remoto e definir `APP_WORKERS=1`;
2. manter a mesma imagem atual;
3. reexecutar apenas a subida do runtime HTTP usando o rollout versionado.

Passo exato no host:

```bash
cd /root/checkcheck
export CHECKCHECK_APP_IMAGE="ghcr.io/tscode-com-br/checkcheck-app:$(cat .deploy-release)"
bash deploy/maintenance/run_app_rollout.sh \
  --phase start \
  --deploy-dir /root/checkcheck
```

### 1.4 Rollback completo de runtime para release anterior

Quando o defeito estiver no codigo/versionamento do runtime e nao apenas no numero de workers:

1. identificar o ultimo SHA bom antes da mudanca de runtime;
2. garantir que esse SHA ainda exista publicado em `ghcr.io/tscode-com-br/checkcheck-app:<sha>`;
3. preservar o schema atual e confirmar que o target anterior continua compativel com o banco atual;
4. publicar esse SHA no host pelo mesmo rollout versionado.

Passo exato no host:

```bash
cd /root/checkcheck
export CHECKCHECK_APP_IMAGE="ghcr.io/tscode-com-br/checkcheck-app:<sha_bom_anterior>"
bash deploy/maintenance/run_app_rollout.sh \
  --phase full \
  --deploy-dir /root/checkcheck \
  --release-id <sha_bom_anterior> \
  --public-health-url https://tscode.com.br/api/health
```

### 1.5 Teste que confirma rollback valido do runtime

Executar todos os itens abaixo:

```bash
cd /root/checkcheck
curl -fsS http://127.0.0.1:8000/api/health/ready
curl -fsS https://tscode.com.br/api/health
docker compose ps
docker compose logs --tail=100 app
```

Confirmacao adicional obrigatoria se o rollback foi motivado por multiworker/realtime:

1. abrir uma sessao de admin e outra de transport;
2. gerar um evento administrativo simples;
3. confirmar que o stream volta a ficar coerente no comportamento esperado apos a reducao para `APP_WORKERS=1` ou apos o release anterior.

### 1.6 Bloqueios obrigatorios do rollback de runtime

- bloquear se o estado do schema apos migracoes recentes nao for compativel com o SHA alvo;
- bloquear se `.deploy-release` estiver ausente e nao existir outro registro confiavel do ultimo release bom;
- bloquear se o problema real estiver no edge ou no worker, para evitar reverter a superficie errada.

## 2. Rollback de startup e migracao

### 2.1 Mudanca coberta por este rollback

Esta secao cobre a separacao do passo `migrate` do processo HTTP e a nova orquestracao de rollout com checkpoints em `deploy/maintenance/run_app_rollout.sh`, `.github/workflows/deploy-oceandrive.yml`, `deploy/deploy_do_ssh.ps1` e `scripts/deploy_launcher.py`.

### 2.2 Evidencia obrigatoria antes de reverter startup

Preservar, no minimo:

```bash
cd /root/checkcheck
docker compose run --rm --no-deps app python -m alembic current > "$EVIDENCE_DIR/startup_01_alembic_current.txt" 2>&1 || true
docker compose run --rm --no-deps app python -m alembic heads > "$EVIDENCE_DIR/startup_02_alembic_heads.txt" 2>&1 || true
docker compose logs --tail=300 migrate > "$EVIDENCE_DIR/startup_03_migrate_logs.txt" 2>&1 || true
docker compose logs --tail=300 app > "$EVIDENCE_DIR/startup_04_app_logs.txt" 2>&1 || true
cat .deploy-release > "$EVIDENCE_DIR/startup_05_release_marker.txt" 2>&1 || true
```

Se houve falha de health local ou publico no rollout, anexar tambem os artefatos do checkpoint falho:

```bash
curl -i -sS http://127.0.0.1:8000/api/health > "$EVIDENCE_DIR/startup_06_local_health.txt" 2>&1 || true
curl -i -sS https://tscode.com.br/api/health > "$EVIDENCE_DIR/startup_07_public_health.txt" 2>&1 || true
```

### 2.3 Rollback exato do startup para release anterior

O rollback recomendado desta superficie nao e reescrever arquivos no host manualmente. O procedimento correto e republicar o ultimo commit bom anterior ao hardening do startup.

Passos exatos no repo/local de operacao:

1. fazer checkout do SHA bom anterior ao hardening de startup/deploy;
2. confirmar que o repo nessa revisao contem a orquestracao desejada para o rollback;
3. usar o fluxo versionado do repo nessa revisao para sincronizar arquivos e republicar o release bom.

Exemplo com o deploy PowerShell versionado do proprio repo naquela revisao:

```powershell
$env:CHECKCHECK_DEPLOY_IMAGE_TAG = "<sha_bom_anterior>"
.\deploy\deploy_do_ssh.ps1 -ServerHost "157.230.35.21" -User "root" -KeyPath "C:\dev\projetos\checkcheck\deploy\keys\do_checkcheck" -RemoteDir "/root/checkcheck"
```

Se o rollback precisar ser feito diretamente no host com imagem ja publicada:

```bash
cd /root/checkcheck
export CHECKCHECK_APP_IMAGE="ghcr.io/tscode-com-br/checkcheck-app:<sha_bom_anterior>"
bash deploy/maintenance/run_app_rollout.sh \
  --phase full \
  --deploy-dir /root/checkcheck \
  --release-id <sha_bom_anterior> \
  --public-health-url https://tscode.com.br/api/health
```

### 2.4 Teste que confirma rollback valido do startup

Executar todos os itens abaixo:

```bash
cd /root/checkcheck
docker compose ps
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS https://tscode.com.br/api/health
cat .deploy-release
```

O rollback de startup so e considerado valido quando:

1. a migracao deixa de falhar no passo que estava bloqueando o rollout;
2. o runtime HTTP volta a subir e responder localmente;
3. o health publico volta a responder com sucesso;
4. o release marker passa a apontar para o SHA recuado.

### 2.5 Bloqueios obrigatorios do rollback de startup

- bloquear se o target anterior exigir downgrade de schema que nao esteja explicitamente versionado em Alembic;
- bloquear se nao houver evidencia do estado atual de `alembic current` e dos logs do passo `migrate`;
- bloquear se a falha estiver no edge e nao no startup, para evitar rollback na superficie errada.

## 3. Rollback do worker separado do Forms

### 3.1 Quando este rollback e aceitavel

Use este rollback quando o worker separado impedir operacao critica do Forms e nao houver correcao menor na propria superficie do worker. A fila persistida `forms_submissions` deve ser preservada antes de qualquer retorno do consumo ao processo HTTP.

### 3.2 Evidencia obrigatoria antes de reverter worker

Preservar, no minimo:

```bash
cd /root/checkcheck
docker compose ps forms-worker app > "$EVIDENCE_DIR/worker_01_compose_ps.txt" 2>&1 || true
docker compose logs --tail=300 forms-worker > "$EVIDENCE_DIR/worker_02_forms_worker_logs.txt" 2>&1 || true
docker compose logs --tail=300 app > "$EVIDENCE_DIR/worker_03_app_logs.txt" 2>&1 || true
docker compose exec -T db psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-checking}" -c "select status, count(*) from forms_submissions group by status order by status;" > "$EVIDENCE_DIR/worker_04_queue_counts.txt" 2>&1 || true
docker compose exec -T db psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-checking}" -c "select min(created_at) as oldest_created_at, min(processing_started_at) as oldest_processing_started_at from forms_submissions where status in ('pending','processing');" > "$EVIDENCE_DIR/worker_05_queue_age.txt" 2>&1 || true
```

Se os comandos SQL falharem, o rollback do worker fica bloqueado ate que a fila possa ser inspecionada de forma confiavel.

### 3.3 Rollback exato do worker

O rollback correto e republicar o ultimo release anterior a separacao do worker, preservando a tabela `forms_submissions` e deixando o consumo voltar ao `lifespan` do app dessa revisao.

Passos exatos:

1. identificar o SHA bom anterior a `sistema/app/forms_worker_main.py` e ao servico `forms-worker` em `docker-compose.yml`;
2. redeployar esse SHA pelo fluxo versionado do repo;
3. usar `--remove-orphans` no restart do `app` para remover o container `forms-worker` orfao do host.

Passo exato no host, caso a imagem ja esteja publicada:

```bash
cd /root/checkcheck
export CHECKCHECK_APP_IMAGE="ghcr.io/tscode-com-br/checkcheck-app:<sha_bom_anterior>"
bash deploy/maintenance/run_app_rollout.sh \
  --phase full \
  --deploy-dir /root/checkcheck \
  --release-id <sha_bom_anterior> \
  --public-health-url https://tscode.com.br/api/health
```

Se o rollback for conduzido pela revisao antiga do repo, o `docker-compose.yml` antigo deixa de declarar `forms-worker`, e o restart com `--remove-orphans` remove o container dedicado remanescente.

### 3.4 Teste que confirma rollback valido do worker

O rollback do worker so e valido quando todos os itens abaixo passarem:

```bash
cd /root/checkcheck
docker compose ps
curl -fsS http://127.0.0.1:8000/api/health/ready
curl -fsS https://tscode.com.br/api/health
```

E, adicionalmente:

1. o container `forms-worker` nao aparece mais como servico ativo depois do rollback para a revisao antiga;
2. a fila `forms_submissions` continua presente e inspecionavel;
3. pelo menos um item controlado da fila consegue voltar a ser consumido sem degradar o `health` da API.

### 3.5 Bloqueios obrigatorios do rollback do worker

- bloquear se a contagem por status da fila nao tiver sido preservada antes da reversao;
- bloquear se o rollback proposto implicar perda da tabela `forms_submissions` ou de seu backlog;
- bloquear se o problema do Forms puder ser corrigido no proprio worker sem recolocar Playwright/Chromium no blast radius do HTTP.

## 4. Rollback de edge Nginx

### 4.1 Quando este rollback e aceitavel

Use este rollback quando a mudanca ativa do Nginx introduzir roteamento errado, 4xx/5xx anormais, timeouts novos ou quebra de publicacao de `/api/`, `/checking/admin`, `/checking/user` ou `/checking/transport`.

### 4.2 Evidencia obrigatoria antes de reverter edge

Preservar, no minimo:

```bash
nginx -T > "$EVIDENCE_DIR/edge_01_nginx_T.txt" 2>&1
curl -i -sS https://tscode.com.br/api/health > "$EVIDENCE_DIR/edge_02_public_api_health.txt" 2>&1 || true
curl -i -sS https://tscode.com.br/checking/admin > "$EVIDENCE_DIR/edge_03_public_admin.txt" 2>&1 || true
curl -i -sS https://tscode.com.br/checking/user > "$EVIDENCE_DIR/edge_04_public_user.txt" 2>&1 || true
curl -i -sS https://tscode.com.br/checking/transport > "$EVIDENCE_DIR/edge_05_public_transport.txt" 2>&1 || true
```

Tambem e obrigatorio registrar:

1. o caminho do `server_config` real que contem o bloco HTTPS publico;
2. o `backup_file` criado no apply do cutover;
3. o `http_backup_file`, se o include `http {}` foi alterado.

Sem esses caminhos, o rollback de edge fica bloqueado.

### 4.3 Rollback exato do edge

O rollback desta superficie deve usar o helper versionado do repo, nunca edicao manual ad hoc do Nginx em producao.

Passo exato:

```bash
bash deploy/nginx/manage_checking_edge_cutover.sh rollback \
  --server-config <caminho_real_do_server_https> \
  --backup-file <backup_file_gerado_no_apply> \
  --http-config-target /etc/nginx/conf.d/checkcheck-edge-http.conf \
  --http-backup-file <http_backup_file_gerado_no_apply> \
  --reload
```

Se nao houve backup do include `http {}`, omitir `--http-backup-file`; o helper removera o include alvo quando apropriado.

### 4.4 Teste que confirma rollback valido do edge

Executar todos os itens abaixo:

```bash
nginx -t
curl -fsS https://tscode.com.br/api/health
curl -i -sS https://tscode.com.br/checking/admin
curl -i -sS https://tscode.com.br/checking/user
curl -i -sS https://tscode.com.br/checking/transport
```

Se o rollback for para a topologia final gerenciada pelo repo, rodar tambem o verificador versionado:

```bash
bash deploy/nginx/verify_checking_edge_cutover.sh --mode full --nginx-test
```

Se o rollback for para uma configuracao anterior ao cutover gerenciado, o teste valido continua sendo `nginx -t` mais os curls publicos da superficie que estava publicada antes da mudanca.

### 4.5 Bloqueios obrigatorios do rollback de edge

- bloquear se o `server_config` real do host nao tiver sido identificado com seguranca;
- bloquear se o arquivo de backup nao existir mais;
- bloquear se a falha real estiver no upstream local e nao no Nginx, para evitar rollback do edge com backend ja indisponivel.

## 5. Ordem recomendada de decisao em caso de incidente de deploy

1. Capturar o bundle comum de evidencia e identificar qual superficie falhou primeiro: startup, runtime, worker ou edge.
2. Se o problema for apenas de multiworker/realtime, tentar primeiro o rollback minimo do runtime para `APP_WORKERS=1`.
3. Se o problema estiver no rollout/migracao, preservar estado Alembic e recuar para o ultimo SHA bom sem executar downgrade cego de schema.
4. Se o problema estiver no Forms, preservar backlog e estado da fila antes de qualquer retorno ao consumo embutido no app.
5. Se o problema estiver no edge, usar apenas o helper versionado com backup identificado e `nginx -t` antes do reload.

## 6. Condicoes de parada obrigatoria

Parar e declarar rollback bloqueado quando ocorrer qualquer uma destas condicoes:

1. `.deploy-release` ausente e nenhum outro registro confiavel do release atual;
2. estado do schema desconhecido ou potencialmente incompativel com o SHA alvo;
3. fila `forms_submissions` sem contagem preservada por status;
4. backup do Nginx inexistente ou caminho ativo do `server {}` nao identificado;
5. health publico falhando sem que a saude local do upstream tenha sido capturada antes da reversao.

## 7. Rollback desta execucao

Para desfazer apenas esta execucao documental, basta remover este arquivo:

1. `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md`

Nenhuma alteracao de host, workflow, container, compose, Nginx ou banco foi feita nesta etapa.

## 8. Proximo passo recomendado

Seguir para a Fase 11 com base nesta matriz e consolidar o runbook operacional final, incorporando:

1. ordem de rollout por ondas;
2. verificacao de saude por host, API, worker, edge e banco;
3. alertas minimos e thresholds que devem disparar coleta de evidencia antes de qualquer rollback.