# Reconciliacao do edge Nginx - Fase 7 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: parcialmente aprovado para decisao de topologia e reconcilicacao versionada; bloqueado para confirmacao final do host por ausencia do artefato bruto `nginx -T` da Fase 0 no workspace.
- Objetivo desta etapa: comparar o edge real capturado na Fase 0 com o arquivo versionado `deploy/nginx/checking-edge-routes.conf`, definir a topologia final de upstreams e recusar drift manual como estado final.
- Escopo efetivamente usado nesta execucao:
  - `docs/incidents/2026-05-04-504-phase0-baseline.md`
  - `deploy/nginx/checking-edge-routes.conf`
  - `deploy/maintenance/capture_phase0_nginx_config.sh`
  - `deploy/nginx/verify_checking_edge_cutover.sh`
  - `docs/context/proxy_rotas_deploy_separado.md`
  - `docker-compose.api.yml`
  - `docker-compose.websites.yml`

## 2. Limite de evidencia desta execucao

O prompt pede uso do `nginx -T` capturado na Fase 0. Esse artefato bruto nao esta anexado no workspace atual.

O que existe hoje no repo e:

1. uma consolidacao parcial da Fase 0 registrando que o artefato ainda nao foi anexado;
2. evidencia historica do incidente apontando upstream observado em `127.0.0.1:8000`;
3. o template versionado do edge apontando para a topologia split `18080/18081/18082/18083`;
4. um coletor versionado da Fase 0 que ja trata mistura entre `8000` e `1808x` como drift critico.

Portanto, esta execucao consegue fechar a decisao de topologia versionada e o criterio de drift, mas nao consegue afirmar o estado atual do host como fato novo sem o anexo bruto da Fase 0.

## 3. Comparacao objetiva entre repo e baseline do incidente

### 3.1 O que o repo versiona como edge alvo

O arquivo `deploy/nginx/checking-edge-routes.conf` versiona o seguinte roteamento publico:

- `/api` e `/api/*` -> `127.0.0.1:18080`
- `/assets` e `/assets/*` -> `127.0.0.1:18080`
- `/checking/admin` e `/checking/admin/*` -> `127.0.0.1:18081`
- `/checking/user` e `/checking/user/*` -> `127.0.0.1:18082`
- `/checking/transport` e `/checking/transport/*` -> `127.0.0.1:18083`

Esse desenho tambem e consistente com os alvos publicados no repo:

- `docker-compose.api.yml` publica a API em `18080 -> 8000`;
- `docker-compose.websites.yml` publica `admin-web` em `18081`, `user-web` em `18082` e `transport-web` em `18083`.

### 3.2 O que o baseline da Fase 0 consolidou sobre o host

Sem o artefato bruto do `nginx -T`, a consolidacao versionada da Fase 0 ainda registra apenas estes fatos fortes:

1. o incidente observado passou por upstream `127.0.0.1:8000`;
2. o repo ja estava versionando edge split em `18080/18081/18082/18083`;
3. isso ja foi classificado como drift `critica`;
4. o estado exato do host ficou pendente de anexar `20_nginx_T.txt`, `21_active_tscode_server_blocks.txt`, `22_active_relevant_location_blocks.txt` e `23_active_location_targets.tsv`.

### 3.3 Criterio de drift ja versionado para o host

O coletor `deploy/maintenance/capture_phase0_nginx_config.sh` explicita o criterio correto para interpretar o `nginx -T` real:

1. se aparecer apenas `127.0.0.1:8000`, a resposta objetiva e `127.0.0.1:8000`;
2. se aparecerem apenas `18080/18081/18082/18083`, a resposta objetiva e `18080/18081/18082/18083`;
3. se aparecer `127.0.0.1:8000` ao lado de qualquer `1808x`, a resposta objetiva e `ambos em configuracoes diferentes`;
4. a existencia de `location /checking/` apontando para `127.0.0.1:8000` e tratada como drift `critica` porque pode conflitar com o cutover split.

## 4. Decisao de topologia final

### 4.1 Decisao objetiva

A producao nao deve continuar com o edge publico em `127.0.0.1:8000`.

A topologia final correta e versionada para o edge publico deve migrar para:

- `/api` e `/assets` -> `127.0.0.1:18080`
- `/checking/admin` -> `127.0.0.1:18081`
- `/checking/user` -> `127.0.0.1:18082`
- `/checking/transport` -> `127.0.0.1:18083`

### 4.2 O que `127.0.0.1:8000` ainda pode significar sem conflitar com essa decisao

`127.0.0.1:8000` continua aceitavel apenas como detalhe interno do processo HTTP da API, por exemplo:

1. porta interna do container `api` ou `app`;
2. healthcheck local dentro do proprio container HTTP;
3. compatibilidade temporaria de runtime enquanto o edge publico ainda nao foi cortado.

`127.0.0.1:8000` nao deve permanecer como destino do edge publico final para `/api`, `/checking/admin`, `/checking/user` ou `/checking/transport`.

### 4.3 Topologia que fica explicitamente proibida como estado final

Nao aceitar como estado final:

1. Nginx publico inteiro apontando para `127.0.0.1:8000`;
2. mistura de `/api` em `18080` com qualquer `/checking/*` ainda caindo em `127.0.0.1:8000` sem justificativa versionada;
3. coexistencia de rotas especificas split com uma `location /checking/` generica apontando para `127.0.0.1:8000` no mesmo `server` block publico.

## 5. Matriz de comparacao e classificacao de drift

| Superficie | Topologia final versionada | Sinal historico do host/incidente | Classificacao se divergir |
| --- | --- | --- | --- |
| `/api` | `127.0.0.1:18080/api/` | incidente observou `127.0.0.1:8000` como upstream | `critica` |
| `/checking/admin` | `127.0.0.1:18081/` | host atual nao confirmado no workspace | `critica` |
| `/checking/user` | `127.0.0.1:18082/` | host atual nao confirmado no workspace | `critica` |
| `/checking/transport` | `127.0.0.1:18083/` | host atual nao confirmado no workspace | `critica` |
| `location /checking/` generica | nao deve existir apontando para `127.0.0.1:8000` no edge final | o parser da Fase 0 trata isso como conflito estrutural | `critica` |

Observacao:

- A ausencia do `nginx -T` bruto impede preencher os destinos ativos atuais dessas quatro superficies como fato novo nesta execucao.

## 6. Conclusao operacional desta fase

Conclusao objetiva desta reconciliacao:

1. o estado final aceito e o edge split `18080/18081/18082/18083` ja versionado no repo;
2. `127.0.0.1:8000` pertence ao runtime interno da API, nao ao desenho final de proxy publico;
3. qualquer host ainda apontando para `127.0.0.1:8000` no edge, ou misturando `8000` com `1808x`, permanece em drift e nao deve ser tratado como configuracao valida final;
4. a confirmacao final do host continua bloqueada ate anexar o `nginx -T` bruto da Fase 0 ou rerodar o coletor host-side equivalente.

## 7. Evidencia faltante para fechamento total do host

Para fechar a comparacao host-versus-repo sem lacuna, ainda e necessario anexar ao workspace pelo menos:

- `20_nginx_T.txt`
- `21_active_tscode_server_blocks.txt`
- `22_active_relevant_location_blocks.txt`
- `23_active_location_targets.tsv`
- `27_nginx_relevant_diff.txt`

Se esses artefatos ainda nao existirem no droplet, o caminho versionado para gera-los continua sendo:

```bash
bash deploy/maintenance/capture_phase0_nginx_config.sh <diretorio-de-evidencias> <repo-root>
```

## 8. Resultado desta execucao

- Reconciliacao versionada: concluida.
- Decisao de topologia final: concluida.
- Confirmacao do host com `nginx -T` bruto: bloqueada por ausencia do artefato no workspace.