# Baseline operacional da Fase 0 - incidente 504 de 2026-05-04

## 1. Status desta consolidacao

- Resultado atual: parcialmente consolidado.
- Estado da execucao: bloqueado para fechamento completo por ausencia de acesso SSH/host nesta execucao.
- Escopo deste arquivo: registrar, em um unico artefato versionado, os fatos ja conhecidos no repo e na investigacao previa desta demanda, as evidencias host-side preparadas para coleta e as lacunas que ainda dependem da execucao no droplet.
- Regra aplicada aqui: este documento nao propoe correcoes. Ele apenas registra fatos, sinais, evidencias esperadas e lacunas abertas.

## 2. Fontes usadas nesta consolidacao

Fontes versionadas no repo:

- `docs/temp_007.md`
- `docs/temp_007_todo_list.md`
- `docker-compose.yml`
- `deploy/nginx/checking-edge-routes.conf`
- `deploy/nginx/verify_checking_edge_cutover.sh`
- `deploy/maintenance/capture_phase0_baseline.sh`
- `deploy/maintenance/capture_phase0_docker_state.sh`
- `deploy/maintenance/capture_phase0_nginx_config.sh`
- `deploy/maintenance/capture_phase0_nginx_logs.sh`
- `deploy/maintenance/capture_phase0_edge_http_checks.sh`

Fontes nao coletadas nesta execucao:

- saida real de `nginx -T` no host;
- saida real de `docker ps`, `docker compose ps`, `docker inspect` e `docker logs` no host;
- saida real dos `curl -i` locais/publicos no host;
- logs reais atuais e rotacionados do Nginx no host.

## 3. Linha do tempo minima atualmente consolidada

1. Em `2026-05-04`, houve indisponibilidade publica com erro `504`.
2. A leitura de trabalho ja consolidada em `docs/temp_007.md` registra que o Nginx publicou sinal de `upstream timed out (110: Connection timed out) while reading response header from upstream`.
3. A mesma leitura registra que o upstream observado nos logs do incidente foi `http://127.0.0.1:8000`.
4. A mesma leitura registra que o container do app ficou `unhealthy`, sem evidencia previa de `OOMKilled`.
5. A mesma leitura registra que o banco permaneceu `healthy` durante a janela observada.
6. A mesma leitura registra que o reboot do droplet restaurou o servico.
7. O incidente ocorreu apos uma apresentacao para a equipe, quando muitos usuarios acessaram a superficie web de check via QR Code e executaram cadastro, login, consulta de estado, localizacao e check-in/check-out.

Observacao importante:

- Os itens acima registram o baseline investigativo ja assumido pelo programa e precisam ser reconciliados com as evidencias brutas da Fase 0 no host antes do fechamento definitivo desta fase.

## 4. Topologia ativa conhecida neste momento

### 4.1 Topologia conhecida no repo

- `docker-compose.yml` versiona pelo menos dois servicos principais: `app` e `db`.
- O servico `app` expoe `8000:8000` por padrao.
- O servico `db` expoe `5432:5432` por padrao.
- O healthcheck do `app` versionado consulta `http://127.0.0.1:8000/api/health`.
- O arquivo versionado `deploy/nginx/checking-edge-routes.conf` assume topologia separada por upstreams locais:
  - `/api/` -> `127.0.0.1:18080`
  - `/checking/admin` -> `127.0.0.1:18081`
  - `/checking/user` -> `127.0.0.1:18082`
  - `/checking/transport` -> `127.0.0.1:18083`

### 4.2 Topologia ativa real no host

- Nao verificada nesta execucao.
- Evidencia historica consolidada no programa indica que, no incidente observado, o upstream visto nos logs do Nginx foi `127.0.0.1:8000`.
- Confirmacao host-side ainda pendente via:
  - `deploy/maintenance/capture_phase0_docker_state.sh`
  - `deploy/maintenance/capture_phase0_nginx_config.sh`

## 5. Estado dos containers

### 5.1 Fato atualmente consolidado

- `docker-compose.yml` versiona `app` e `db` com `restart: unless-stopped`.
- O baseline investigativo consolidado em `docs/temp_007.md` registra que, durante a janela observada, o `app` ficou `unhealthy` e o `db` permaneceu `healthy`.

### 5.2 Confirmacao host-side pendente

Estado real atual ainda nao congelado nesta execucao para:

- `State.Status`
- `State.Health`
- `RestartCount`
- `StartedAt`
- `FinishedAt`
- `OOMKilled`
- `Health.Log`

Evidencias esperadas quando a coleta host-side rodar:

- `11_stack_directory.txt`
- `12_docker_ps_no_trunc.txt`
- `13_docker_inspect_checkcheck_app_1.txt`
- `14_docker_inspect_checkcheck_db_1.txt`
- `15_docker_logs_checkcheck_app_1_tail_500.txt`
- `16_docker_logs_checkcheck_db_1_tail_200.txt`
- `17_docker_compose_ps.txt`
- `18_checkcheck_app_1_state_summary.txt`
- `19_checkcheck_db_1_state_summary.txt`
- `99_docker_summary.txt`

## 6. Upstreams reais do Nginx

### 6.1 Upstreams esperados pelo repo

- `/api/` -> `127.0.0.1:18080/api/`
- `/checking/admin` -> `127.0.0.1:18081/`
- `/checking/user` -> `127.0.0.1:18082/`
- `/checking/transport` -> `127.0.0.1:18083/`

### 6.2 Upstreams reais conhecidos ate agora

- Indicacao historica do incidente: `127.0.0.1:8000` apareceu como upstream nos logs observados.
- Configuracao ativa real do host ainda nao foi congelada nesta execucao via `nginx -T`.

### 6.3 Evidencias host-side esperadas

- `20_nginx_T.txt`
- `21_active_tscode_server_blocks.txt`
- `22_active_relevant_location_blocks.txt`
- `23_active_location_targets.tsv`
- `24_repo_checking_edge_routes.conf`
- `25_repo_relevant_location_blocks.txt`
- `26_repo_location_targets.tsv`
- `27_nginx_relevant_diff.txt`
- `99_nginx_summary.txt`

## 7. Sinais locais e publicos de saude

### 7.1 Sinais previstos pela Fase 0

As verificacoes previstas para esta fase sao:

- `curl -i http://127.0.0.1:8000/api/health`
- `curl -i https://tscode.com.br/api/health`
- `curl -i https://tscode.com.br/checking/user`
- `curl -i https://tscode.com.br/checking/admin`

### 7.2 Estado atual desta consolidacao

- Nenhuma dessas quatro respostas foi congelada nesta execucao, porque nao houve acesso ao host.
- Ja existe, no repo, um coletor dedicado para esta parte da Fase 0: `deploy/maintenance/capture_phase0_edge_http_checks.sh`.

### 7.3 Evidencias host-side esperadas

- `50_local_api_health.txt`
- `51_public_api_health.txt`
- `52_public_checking_user.txt`
- `53_public_checking_admin.txt`
- `55_edge_http_checks_summary.txt`

### 7.4 Diferenca entre saude local do upstream e saude publica no edge

Nesta execucao, a diferenca nao pode ser afirmada como fato atual porque as respostas nao foram coletadas no host.

O que esta consolidado ate aqui e apenas:

- o repo assume health local em `127.0.0.1:8000/api/health` no compose atual;
- a validacao publica de producao ja foi tratada no programa como `https://tscode.com.br/api/health`;
- a comparacao objetiva entre upstream local e edge publico continua pendente de captura host-side.

## 8. Lista objetiva de drifts entre repo e host

### 8.1 Drift historico ou fortemente indicado pelo material atual

1. `critica` - o repo versiona edge separado em `18080/18081/18082/18083`, enquanto o baseline do incidente consolidado no programa aponta para upstream observado em `127.0.0.1:8000`.
2. `importante` - o repo hoje mistura duas leituras de topologia: `docker-compose.yml` e healthcheck local do `app` em `8000`, enquanto o edge versionado assume split por portas `18080-18083`. Sem a coleta no host, nao ha confirmacao de qual desenho esta efetivamente exposto ao publico neste instante.

### 8.2 Drifts que ainda nao podem ser marcados como confirmados nesta execucao

1. rotas publicas `/checking/user`, `/checking/admin` e `/checking/transport` ainda nao foram confirmadas no host como apontando para `8000`, `18081/18082/18083` ou mistura de ambos;
2. o estado atual do `app` como `healthy`, `unhealthy`, `reiniciando` ou apenas vivo sem responder utilmente ainda nao foi recongelado no host;
3. a diferenca atual entre `/api/health` local e `/api/health` publico ainda nao foi capturada;
4. o drift exato entre blocos `server/location` ativos do host e `deploy/nginx/checking-edge-routes.conf` ainda depende do `nginx -T` real.

## 9. Evidencias e artefatos preparados no repo para fechar a Fase 0

### 9.1 Baseline do host

- `deploy/maintenance/capture_phase0_baseline.sh`

### 9.2 Estado do Docker e dos containers

- `deploy/maintenance/capture_phase0_docker_state.sh`

### 9.3 Configuracao ativa do Nginx e comparacao com repo

- `deploy/maintenance/capture_phase0_nginx_config.sh`

### 9.4 Logs e sinais do incidente no edge

- `deploy/maintenance/capture_phase0_nginx_logs.sh`

### 9.5 Saude local e publica do upstream/edge

- `deploy/maintenance/capture_phase0_edge_http_checks.sh`

## 10. Lacunas abertas nesta consolidacao

1. Falta a execucao host-side dos cinco coletores preparados no repo.
2. Falta anexar as evidencias brutas geradas no droplet ao diretorio de incidente desta Fase 0.
3. Falta reconciliar fatos historicos do incidente com o estado atual real do host no momento da coleta.
4. Falta fechar a resposta objetiva e atual para estas perguntas:
   - qual e o diretorio real da stack no host;
   - qual e o estado atual de `checkcheck-app-1` e `checkcheck-db-1`;
   - quais upstreams o Nginx ativo realmente usa hoje para `tscode.com.br`;
   - se `/api/health` responde localmente e publicamente de forma coerente;
   - quais rotas concentraram `504` e `upstream timed out` na janela relevante dos logs.

## 11. Conclusao desta consolidacao

Esta consolidacao da Fase 0 ja existe como artefato versionado e registra o baseline tecnico assumido pelo programa, a topologia conhecida no repo, os sinais historicos relevantes do incidente e as lacunas que ainda dependem de coleta no host.

O fechamento completo da Fase 0 continua bloqueado ate que as evidencias brutas do droplet sejam efetivamente geradas e anexadas. Ate la, este arquivo deve ser lido como consolidacao parcial, sem inventar estado atual de producao e sem antecipar correcoes.