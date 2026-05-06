# Hardening do edge por classe de superficie - Fase 7 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado no repo para politica versionada do edge; validacao host-side ainda pendente.
- Objetivo desta etapa: endurecer o proxy por classe de superficie, revisando `proxy_read_timeout`, `proxy_connect_timeout`, buffering, keepalive e protecao de burst sem quebrar uso legitimo.
- Arquivos principais desta entrega:
  - `deploy/nginx/checking-edge-routes.conf`
  - `deploy/nginx/checking-edge-http.conf`
  - `deploy/nginx/manage_checking_edge_cutover.sh`
  - `docs/context/proxy_rotas_deploy_separado.md`
  - `docs/context/operacao_rollback_deploy_separado.md`

## 2. Hipotese local atacada

O template anterior tratava praticamente todo `/api/*` como se fosse stream de longa duracao, com `proxy_buffering off` e `proxy_read_timeout 3600s` para qualquer rota da API.

Isso ampliava blast radius no edge por dois motivos:

1. mascarava stalls ou respostas lentas em rotas HTTP comuns que deveriam falhar mais cedo;
2. deixava auth, bootstrap e reads curtas sem politica propria de burst, mesmo sendo superficies mais sensiveis a loops de frontend e reconexao agressiva.

## 3. Politicas versionadas por classe de superficie

### 3.1 Politica de conexao do server publico

Aplicada no `server` block:

- `keepalive_timeout 15s`
- `keepalive_requests 100`
- `send_timeout 30s`

Justificativa:

- manter conexao de cliente viva tempo suficiente para navegacao normal;
- evitar sockets ociosos retidos por tempo excessivo no edge;
- limitar conexoes travadas na borda antes de virarem ruido operacional.

### 3.2 Health HTTP curto e deterministico

Aplicada em `= /api/health` e `= /api/health/ready`:

- `proxy_buffering on`
- `proxy_request_buffering on`
- `proxy_connect_timeout 3s`
- `proxy_read_timeout 15s`
- `proxy_send_timeout 15s`
- `proxy_socket_keepalive on`

Justificativa:

- health nao e stream nem workload pesado;
- se o upstream local em loopback nao conecta rapidamente, o problema e real e deve aparecer cedo;
- buffering ligado reduz custo por resposta curta e previsivel.

### 3.3 API comum e assets com timeout moderado

Aplicada em `/api/` generico e `/assets/`:

- `proxy_buffering on`
- `proxy_request_buffering on` em `/api/`
- `proxy_connect_timeout 3s`
- `proxy_read_timeout 60s` para API comum
- `proxy_read_timeout 30s` para assets
- `proxy_send_timeout 60s` para API comum
- `proxy_send_timeout 30s` para assets
- `proxy_socket_keepalive on`

Justificativa:

- a API normal deve continuar tolerante a operacoes legitimas, mas nao merece janela de uma hora;
- assets e HTML devem ser curtos e totalmente bufferizados;
- loopback local torna `proxy_connect_timeout 3s` suficiente para detectar upstream ruim cedo.

### 3.4 Streams e SSE com politica dedicada

Aplicada em:

- `/api/admin/stream`
- `/api/transport/stream`
- `/api/web/transport/stream`

Politica:

- `proxy_buffering off`
- `proxy_request_buffering off`
- `proxy_set_header Connection ""`
- `proxy_socket_keepalive on`
- `proxy_connect_timeout 3s`
- `proxy_read_timeout 3600s`
- `proxy_send_timeout 3600s`
- `add_header X-Accel-Buffering no always`
- `limit_req zone=checkcheck_edge_stream burst=15 nodelay`

Justificativa:

- SSE precisa continuar sem buffering;
- o timeout longo fica restrito apenas ao que realmente e stream;
- o rate limit do stream nao limita a conexao estabelecida, mas suaviza tempestades de reconexao por aba ou cliente em loop.

### 3.5 Auth com timeout curto e rate limit generoso

Aplicada em todos os prefixos:

- `/api/admin/auth/`
- `/api/transport/auth/`
- `/api/web/auth/`

Politica:

- `proxy_buffering on`
- `proxy_request_buffering on`
- `proxy_socket_keepalive on`
- `proxy_connect_timeout 3s`
- `proxy_read_timeout 20s`
- `proxy_send_timeout 20s`
- `limit_req zone=checkcheck_edge_auth burst=40 nodelay`
- `limit_req_status 429`

Zonas globais em `deploy/nginx/checking-edge-http.conf`:

- `checkcheck_edge_auth`: `15r/s`
- `checkcheck_edge_stream`: `5r/s`

Justificativa:

- auth e a superficie mais sensivel a burst causado por loops de verify/login/session;
- o limite foi mantido deliberadamente generoso para nao punir NAT compartilhado ou equipe operando no mesmo IP;
- a protecao mira reconexao/aceleracao anormal, nao uso normal.

## 4. O que deliberadamente nao foi rate-limited nesta etapa

Nao foi aplicado rate limit generico em:

- `/checking/user`
- `/checking/admin`
- `/checking/transport`
- `/api/web/check/state`
- `/api/mobile/state`
- `/api/admin/checkin`
- `/api/admin/checkout`
- `/api/admin/projects`

Justificativa:

- essas superficies tem trafego legitimo concentrado e podem sofrer acesso compartilhado por NAT em momentos operacionais intensos;
- aplicar corte por IP aqui, sem mediacao adicional, tem risco maior de falso positivo do que ganho imediato;
- o endurecimento desta fase ficou focado em auth e stream, que sao as superfices com melhor relacao entre protecao e risco de quebra.

## 5. Aplicacao versionada no host

O endurecimento agora depende de duas pecas distintas:

1. `deploy/nginx/checking-edge-http.conf` no contexto `http {}` do Nginx;
2. `deploy/nginx/checking-edge-routes.conf` dentro do `server` block publico.

O helper `deploy/nginx/manage_checking_edge_cutover.sh` foi atualizado para:

- instalar opcionalmente o include `http` por `--http-config-target`;
- criar backup do include `http` quando ele ja existir;
- restaurar automaticamente os backups se `nginx -t` falhar durante o apply;
- remover ou restaurar o include `http` no rollback.

## 6. Plano de validacao

### 6.1 Validacao sintatica obrigatoria no host

```bash
bash deploy/nginx/manage_checking_edge_cutover.sh apply \
  --server-config /etc/nginx/sites-enabled/tscode.com.br.conf \
  --http-config-target /etc/nginx/conf.d/checkcheck-edge-http.conf \
  --reload
```

Resultado esperado:

- `nginx -t` passa antes do reload;
- o helper informa os backups criados;
- se `nginx -t` falhar, o helper restaura os arquivos alterados e aborta sem reload.

### 6.2 Smoke local e publico minimo

```bash
bash deploy/nginx/verify_checking_edge_cutover.sh --mode local --nginx-test
bash deploy/nginx/verify_checking_edge_cutover.sh --mode full
```

Resultado esperado:

- `https://tscode.com.br/api/health` continua saudavel;
- `/checking/admin`, `/checking/user` e `/checking/transport` continuam servindo o HTML esperado;
- nenhum caminho publico critico regressa para `404` ou `502`.

### 6.3 Validacao funcional de auth sem falso positivo

Validar no host ou a partir de uma estacao autorizada:

1. fluxo normal de login admin em `/checking/admin`;
2. fluxo normal de verify/login/logout em `/checking/transport`;
3. fluxo normal de auth status/login/register no web check.

Resultado esperado:

- uso normal nao recebe `429`;
- autenticao continua funcional na mesma origem.

### 6.4 Validacao controlada de burst em auth

Executar um burst controlado do mesmo IP contra uma rota de auth barata, por exemplo `/api/web/auth/status`, apenas em janela controlada:

```bash
for i in $(seq 1 80); do
  curl -s -o /dev/null -w "%{http_code}\n" https://tscode.com.br/api/web/auth/status &
done
wait
```

Resultado esperado:

- requests normais isoladas continuam abaixo do limite;
- parte do burst agressivo passa a receber `429`, comprovando que o edge esta amortecendo loops anormais.

### 6.5 Validacao funcional de SSE

Validar com sessao autenticada real do admin e do transport:

1. abrir `/checking/admin` e confirmar que o stream continua vivo e recebe atualizacoes;
2. abrir `/checking/transport` e confirmar comportamento equivalente;
3. conferir que a resposta do stream inclui `X-Accel-Buffering: no`.

Resultado esperado:

- sem buffering no stream;
- sem reconexao em loop em uso normal;
- sem regressao funcional na experiencia de realtime.

## 7. Resultado desta execucao

- Politica versionada por classe de superficie: concluida.
- Justificativa tecnica por politica: documentada.
- Plano de validacao: documentado.
- Validacao host-side real com `nginx -t`, reload e curls publicos: pendente de execucao no droplet.