# Ordem final de rollout por ondas - Fase 11 - incidente 504 de 2026-05-06

## Objetivo executado

Foi consolidada a ordem final de rollout por ondas pequenas e seguras para o programa de mitigacao do incidente `504`, partindo das issues priorizadas `P0`, `P0A`, `P1`, `P2`, `P3`, `P4`, `P5`, `P6`, `P7`, `P8`, `P9` e `P10`.

## Hipotese ou risco atacado

O risco atacado nesta etapa era este: mesmo com o trabalho tecnico versionado no repo ate a Fase 10, ainda faltava uma ordem operacional unica que dissesse quando cada grupo de mudancas pode entrar, quais gates precisam ficar verdes antes de avancar e em que ponto a equipe deve abortar ou reverter sem improvisar reboot amplo.

## Arquivos alterados

- `docs/incidents/2026-05-06-504-phase11-rollout-waves.md`

## Comandos executados

Nenhum comando de host ou de producao foi executado nesta etapa. A consolidacao foi documental, baseada nas evidencias e scripts ja versionados no repo.

## Evidencias geradas

- este relatorio versionado: `docs/incidents/2026-05-06-504-phase11-rollout-waves.md`

## Validacao executada

1. revisao cruzada dos relatorios das Fases 0A a 10;
2. revisao dos scripts de rollout e validacao de edge ja versionados em `deploy/maintenance/` e `deploy/nginx/`;
3. checagem do workflow `.github/workflows/deploy-oceandrive.yml` para alinhar a ordem de publicacao ao fluxo atual do repo.

## Resultado

Aprovado em escopo de repo.

Esta etapa nao executa o rollout no host. Ela define a ordem final e os gates obrigatorios para a janela real de producao.

## Regras gerais desta ordem de rollout

1. Executar uma onda por vez.
2. So avancar quando a onda anterior estiver verde e com evidencia salva.
3. Manter `TRANSPORT_AI_ENABLED=false` durante todas as ondas deste programa.
4. Manter `APP_WORKERS=1` no rollout produtivo ate que `tests/test_multiworker_realtime_postgres.py` passe em ambiente com PostgreSQL real acessivel.
5. Preferir janela controlada com `workflow_dispatch` ou execucao versionada via `deploy/deploy_do_ssh.ps1` ou `deploy/maintenance/run_app_rollout.sh`, mesmo que `.github/workflows/deploy-oceandrive.yml` tambem aceite `push` em `main`.
6. Nao continuar se a saude local do upstream divergir da saude publica no edge.
7. Nao continuar se existir drift critico entre `nginx -T` e `deploy/nginx/checking-edge-routes.conf` mais `deploy/nginx/checking-edge-http.conf`.

## Onda 0 - P0 - baseline forense do host

- Objetivo: congelar o estado real do host, Docker, Nginx, saude local/publica e logs do incidente antes de qualquer mudanca invasiva.
- Pre-requisitos: acesso SSH valido ao droplet, caminho real da stack confirmado, diretorio de evidencia disponivel.
- Metricas que devem ficar verdes: bundle bruto completo salvo em diretorio versionado; `docker compose ps`, `nginx -T`, logs do edge e `curl` local/publico capturados sem lacunas criticas; topologia ativa identificada sem ambiguidade.
- Critrio de abortar ou reverter: abortar a janela se nao houver acesso SSH, se o estado do host for diferente do repo de forma nao reconciliada, ou se a evidencia minima nao puder ser congelada antes das mudancas. Nao ha rollback funcional nesta onda.

## Onda 0A - P0A - headroom imediato do droplet

- Objetivo: confirmar ou executar resize para `2 GB RAM / 2 vCPU` como mitigacao de capacidade antes do rollout estrutural.
- Pre-requisitos: decisao tecnica registrada, autorizacao operacional para resize, snapshot ou evidencia previa conforme procedimento da Fase 0A.
- Metricas que devem ficar verdes: `free -m`, `nproc` e `lscpu` refletem a capacidade alvo ou comprovam que ela ja existe; `docker compose ps` permanece saudavel; `curl` local e publico para `/api/health` continuam `200`.
- Critrio de abortar ou reverter: abortar se o resize degradar Docker, network, mounts ou healthchecks. Reverter apenas apos estabilizacao posterior comprovada, nunca no calor do incidente sem evidencia antes/depois.

## Onda 1 - P1 - observabilidade minima

- Objetivo: colocar em producao logs estruturados de request, diagnostico da fila do Forms e diagnostico de banco/pool.
- Pre-requisitos: Onda 0 concluida; caminho de logs conhecido; credenciais administrativas disponiveis para consultar `/api/admin/forms/queue/diagnostics` e `/api/admin/diagnostics/database`.
- Metricas que devem ficar verdes: `checking.http`, `checking.forms_queue` e `checking.db` aparecendo no log da app; endpoints de diagnostico respondendo; `/api/health` e `/api/health/ready` sem regressao de latencia; `app` e `db` saudaveis.
- Critrio de abortar ou reverter: abortar se a instrumentacao introduzir `5xx`, latencia relevante em rota critica ou erro de boot. Reverter apenas os trechos de observabilidade que causarem regressao comprovada.

## Onda 2 - P2 - desacoplamento do Forms

- Objetivo: publicar `forms-worker` separado da API, preservando fila persistida e reduzindo blast radius do Playwright/Chromium.
- Pre-requisitos: Onda 1 verde; observabilidade da fila funcionando; rollback da Fase 9 disponivel; fila `forms_submissions` conhecida e preservada.
- Metricas que devem ficar verdes: `forms-worker` sobe `healthy`; backlog pode crescer sem derrubar `/api/health`, login, `/api/web/check/state` e `/api/mobile/state`; `app` continua `ready`; `db` continua `healthy`.
- Critrio de abortar ou reverter: abortar se a API e o worker falharem juntos, se backlog crescer com `worker.running=false`, ou se rotas quentes degradarem comparadas ao baseline. Reverter pelo caminho de worker da matriz `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md`.

## Onda 3 - P3 - runtime HTTP endurecido com gate de multiworker fechado

- Objetivo: publicar o runtime HTTP endurecido, mas mantendo rollout produtivo em `1` worker ate a prova real de cross-worker.
- Pre-requisitos: Onda 2 verde; readiness e healthchecks fiaveis; decisao explicita de nao abrir multiworker sem harness PostgreSQL real aprovado.
- Metricas que devem ficar verdes: `/api/health` e `/api/health/ready` estaveis; `app` `healthy`; admin e transport continuam coerentes com `APP_WORKERS=1`; nenhum `5xx` novo em `/api/admin/stream` e `/api/transport/stream`.
- Critrio de abortar ou reverter: abortar se a readiness falhar, se streams perderem coerencia ou se a API entrar em loop de restart. Reverter para o ultimo release bom ou reduzir explicitamente para `APP_WORKERS=1` se a regressao estiver so no paralelismo.

## Onda 4 - P4 - reducao de burst da SPA de check

- Objetivo: publicar a deduplicacao e os cooldowns da SPA de check para derrubar o volume de requests redundantes em bootstrap, auth, lifecycle e localizacao.
- Pre-requisitos: Onda 3 verde; request logging da Onda 1 funcionando; bundle de medicao antes/depois preparado.
- Metricas que devem ficar verdes: queda mensuravel de requests por usuario nos cenarios da Fase 5; UX funcional de abrir QR Code, autenticar, voltar da tela bloqueada, alternar abas, conceder localizacao e registrar check-in/check-out; ausencia de novos erros em `/api/web/auth/login`, `/api/web/check/state` e `/api/web/check/location`.
- Critrio de abortar ou reverter: abortar se a reducao de burst quebrar login legitimo, restauracao de sessao ou submit manual. Reverter apenas o trecho de UX que causar a regressao, preservando telemetria e evidencias de contagem de requests.

## Onda 5 - P5 - hot paths, pool e firewall do Postgres

- Objetivo: publicar ajustes de rotas quentes, pool e restricao de exposicao do Postgres.
- Pre-requisitos: Onda 4 verde; endpoints de diagnostico do banco funcionando; comparativo de latencia e conexoes antes/depois preparado.
- Metricas que devem ficar verdes: `p50/p95/p99` das rotas quentes iguais ou melhores que o baseline; `pool.usage_ratio < 0.8`; `active_database_connections < 24`; `waiting_database_connections = 0`; PostgreSQL sem acesso externo indevido.
- Critrio de abortar ou reverter: abortar se qualquer rota quente piorar materialmente, se surgirem conexoes em espera, ou se a mudanca de firewall cortar o app interno do banco. Reverter individualmente query plan, pool ou controle de exposicao que tiver piorado.

## Onda 6 - P6 - reconciliacao final do edge

- Objetivo: aplicar o edge versionado, sem drift entre host e repo, com timeouts e protecoes coerentes por superficie.
- Pre-requisitos: Ondas 1 a 5 verdes; backup da configuracao ativa do Nginx; scripts `deploy/nginx/manage_checking_edge_cutover.sh`, `deploy/nginx/verify_checking_edge_cutover.sh` e `deploy/nginx/validate_checking_edge_final.sh` disponiveis no host.
- Metricas que devem ficar verdes: `nginx -t` passa; verificacao local e publica de `/api/health`, `/checking/user`, `/checking/admin` e `/checking/transport` passa; `nginx -T` reconciliado com `deploy/nginx/checking-edge-routes.conf` e `deploy/nginx/checking-edge-http.conf`; nenhum aumento anormal de `4xx/5xx`.
- Critrio de abortar ou reverter: abortar se houver drift critico remanescente, falha de sintaxe do Nginx ou quebra de roteamento local/publico. Reverter pelo backup validado antes do reload.

## Onda 7 - P7 - hardening preventivo do dashboard Transport

- Objetivo: publicar dedupe de dashboard, auth menos agressiva, pausa em background e backoff de SSE/polling no `/transport`.
- Pre-requisitos: Onda 6 verde; dashboard autenticado disponivel; `TRANSPORT_AI_ENABLED=false` confirmado no `.env` produtivo.
- Metricas que devem ficar verdes: `GET /api/transport/dashboard`, `GET /api/transport/auth/session`, `GET /api/transport/settings` e `GET /api/transport/stream` sem rajadas paralelas; multiplas abas do transport sem churn anormal; nenhuma chamada acidental a rotas `/api/transport/ai/*` enquanto a IA estiver desabilitada.
- Critrio de abortar ou reverter: abortar se o dashboard perder operabilidade, se auth ficar instavel ou se o dashboard passar a depender da IA habilitada. Reverter apenas a UI do transport que introduzir regressao.

## Onda 8 - P8 - startup, migracao e deploy endurecidos

- Objetivo: usar o fluxo versionado com `migrate`, `start`, `validate-local`, `validate-public` e `mark-release`, removendo a janela fragil de `alembic` dentro do boot HTTP.
- Pre-requisitos: Ondas anteriores verdes; `deploy/maintenance/run_app_rollout.sh` presente no host; ultima release boa identificada em `.deploy-release`.
- Metricas que devem ficar verdes: fase `migrate` concluida; `app` sobe depois em separado; validacao local e publica passa; `mark-release` registra a release alvo; nenhum bootstrap parcial exposto ao edge.
- Critrio de abortar ou reverter: abortar se migracao falhar, se readiness local falhar apos `start`, ou se o publico divergir do local apos validacao. Reverter pelo fluxo documentado em `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md`.

## Onda 9 - P9 - harness e carga controlada

- Objetivo: executar o harness real de before/after em alvo homologado ou produtivo controlado e provar que a stack corrigida nao voltou a saturar.
- Pre-requisitos: Ondas 0 a 8 verdes; ambiente alvo acessivel; credenciais administrativas para snapshots de fila e banco; parametros do perfil de carga aprovados; `GET /checking/user`, `GET /checking/admin` e `GET /checking/transport` respondendo `200` com a shell HTML esperada antes de iniciar o Locust.
- Metricas que devem ficar verdes: relatorio `before_after` com status `approved`; sem falhas HTTP no Locust; `ready` antes e depois; worker do Forms nao `stale`; backlog, CPU, memoria e banco abaixo dos thresholds finais; shells publicas respondendo de forma consistente durante toda a corrida.
- Critrio de abortar ou reverter: abortar se o relatorio marcar `blocked`, se houver falha HTTP, se o banco cruzar thresholds, se backlog e falhas do Forms crescerem juntos, ou se as shells publicas responderem `404/5xx`. Recuar para a ultima onda estavel e retomar a fase bloqueadora correspondente.

## Onda 10 - P10 - operacionalizacao final

- Objetivo: fechar a janela com runbook, alertas, aceite tecnico e matriz final de rollback em uso operacional.
- Pre-requisitos: Onda 9 aprovada; runbook final publicado; alertas configurados ou fallback operacional formalizado; aceite tecnico revisado.
- Metricas que devem ficar verdes: time operacional sabe consultar host, API, worker, Nginx, banco e dashboard Transport; thresholds finais ativos; bundle de evidencia e rollback conhecidos; nenhuma dependencia critica ainda fora do runbook.
- Critrio de abortar ou reverter: abortar se a operacao ainda depender de memoria informal, se faltarem credenciais ou scripts de verificacao, ou se a equipe nao conseguir decidir entre restart de worker, restart de API e coleta de evidencia. Recuar para a lacuna documental correspondente antes de declarar o programa encerrado.

## Nota final desta sessao

O bundle local mais recente da Fase 10 em `docs/artifacts/phase10/first-local-web-check-report-fixed/` validou o gate documental do before/after, mas nao aprovou a onda de carga: o alvo local respondeu `404` nas shells publicas e o snapshot mostrou `forms-worker` `enabled=true` e `running=false`. Portanto, a Onda 9 continua aberta ate uma corrida homologada ou produtiva controlada passar com status `approved`.

## Rollback

O rollback desta etapa documental e simples:

1. remover `docs/incidents/2026-05-06-504-phase11-rollout-waves.md`;
2. manter a matriz operacional ja existente em `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md` como unica fonte de rollback funcional enquanto este documento nao for adotado.

## Proximo passo recomendado

Executar a Onda 0 no host real, salvar o bundle bruto de evidencias e so entao abrir a janela de Onda 0A.