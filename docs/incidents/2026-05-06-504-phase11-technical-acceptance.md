# Aceite tecnico final - Fase 11 - incidente 504 de 2026-05-06

## Objetivo executado

Foi emitido o aceite tecnico final do programa de mitigacao do incidente `504`, consolidando o que mudou, quais evidencias sustentam a resolucao tecnica, quais riscos residuais permanecem, qual foi o ganho esperado do upgrade do droplet, por que a IA de transporte permanece desabilitada e quais gatilhos tecnicos reabririam o programa.

## Hipotese ou risco atacado

O risco atacado nesta etapa era este: sem um aceite tecnico unico, a equipe poderia confundir `repo pronto para rollout controlado` com `incidente encerrado em producao`, ignorando gates ainda abertos como multiworker sem prova em PostgreSQL real, carga real da Fase 10 ainda pendente e evidencias host-side ainda necessarias em algumas ondas.

## Arquivos alterados

- `docs/incidents/2026-05-06-504-phase11-technical-acceptance.md`

## Comandos executados

Nenhum comando de producao foi executado nesta etapa. O aceite abaixo foi consolidado a partir das evidencias ja versionadas no repo.

## Evidencias geradas

- este aceite versionado: `docs/incidents/2026-05-06-504-phase11-technical-acceptance.md`

## Validacao executada

1. revisao dos relatorios das Fases 0A, 1, 2, 3, 4, 5, 6, 7, 9 e 10;
2. revisao do estado atual do workflow de deploy, do compose e dos gates do runtime;
3. revisao do status operacional da IA de transporte no compose, no deploy e na documentacao de acesso ao host.

## Resultado

Parcialmente aprovado.

Decisao tecnica final desta sessao:

1. o repo esta tecnicamente pronto para rollout controlado por ondas;
2. o incidente ainda nao deve ser declarado encerrado de forma irrestrita ate a execucao host-side das ondas finais e da primeira corrida real da Fase 10;
3. o programa pode seguir para producao somente pelo rollout ordenado da Fase 11.

## 1. O que mudou

O programa entregou, no repo, os blocos tecnicos abaixo:

1. observabilidade minima da API, fila do Forms e banco, com logs estruturados e endpoints de diagnostico;
2. desacoplamento do `forms-worker` do runtime HTTP;
3. runtime HTTP endurecido e pronto para mais concorrencia, mas ainda sob gate de multiworker;
4. healthcheck, readiness e auto-recuperacao limitada por componente;
5. reducao de burst da SPA de check e hardening preventivo do dashboard Transport;
6. ajustes de hot paths, pool e exposicao do Postgres;
7. reconciliacao e validacao versionada do edge Nginx;
8. startup, migracao e deploy com checkpoints e rollback versionado;
9. harness de carga e relatorio before/after para gate operacional.

## 2. Evidencias que sustentam a resolucao tecnica

As evidencias principais desta trilha sao:

1. `docs/incidents/2026-05-04-504-phase0a-droplet-resize-decision.md` para a mitigacao de headroom;
2. `docs/incidents/2026-05-04-504-phase1-minimum-alert-package.md` para o pacote minimo de sinais obrigatorios;
3. `docs/incidents/2026-05-04-504-phase2-forms-worker-separation.md`, `docs/incidents/2026-05-04-504-phase2-forms-worker-robustness.md` e `docs/incidents/2026-05-04-504-phase2-forms-isolation-validation.md` para o desacoplamento do Forms;
4. `docs/incidents/2026-05-04-504-phase3-runtime-http-implementation.md` e `docs/incidents/2026-05-04-504-phase3-realtime-cross-worker.md` para o runtime e o barramento cross-worker;
5. `docs/incidents/2026-05-04-504-phase4-health-implementation.md` e `docs/incidents/2026-05-05-504-phase4-auto-recovery.md` para saude real e remediacao limitada;
6. `docs/incidents/2026-05-05-504-phase5-auth-burst-reduction.md`, `docs/incidents/2026-05-05-504-phase5-lifecycle-location-burst-reduction.md` e `docs/incidents/2026-05-05-504-phase5-burst-measurement.md` para alivio de burst no web check;
7. `docs/incidents/2026-05-05-504-phase6-backend-hot-paths-pass1.md`, `docs/incidents/2026-05-05-504-phase6-database-pool-hardening.md`, `docs/incidents/2026-05-05-504-phase6-postgres-exposure-hardening.md` e `docs/temp_011_phase6_backend_db_validation.md` para backend e banco;
8. `docs/incidents/2026-05-05-504-phase7-edge-reconciliation.md` e `docs/incidents/2026-05-05-504-phase7-edge-final-validation.md` para o edge;
9. `docs/temp_007_phase8_transport_network_audit.md` para o hardening do dashboard Transport;
10. `docs/incidents/2026-05-05-504-phase9-startup-migration-deploy-hardening.md` e `docs/incidents/2026-05-05-504-phase9-deploy-rollback.md` para rollout e rollback versionados;
11. `docs/incidents/2026-05-06-504-phase10-load-harness.md` e `docs/incidents/2026-05-06-504-phase10-before-after-reporting.md` para o gate de carga.
12. `docs/artifacts/phase10/first-local-web-check-report-fixed/phase10_web_check_before_after.md`, `docs/artifacts/phase10/first-local-web-check-report-fixed/phase10_web_check_before_after.json` e `docs/artifacts/phase10/first-local-web-check-report-fixed/phase10_web_check.stderr.log` para a ultima prova local do gate de carga e do bloqueio atual do preview.

## 3. Riscos residuais que permanecem abertos

1. o rollout multiworker continua bloqueado, porque `tests/test_multiworker_realtime_postgres.py` ainda nao foi executado com sucesso em ambiente com PostgreSQL real acessivel;
2. a primeira corrida real do harness before/after da Fase 10 ainda precisa ser preservada como evidencia de homologacao ou producao controlada; a ultima corrida local continuou bloqueada porque o preview respondeu `404` nas shells publicas e o snapshot mostrou `forms-worker` parado;
3. parte do baseline host-side da Fase 0 e da validacao final do edge depende de execucao no droplet com acesso SSH operacional no momento da janela;
4. o resize do droplet continua sendo mitigacao de capacidade e nao prova, sozinho, a eliminacao da causa raiz;
5. o edge ainda precisa permanecer reconciliado com o repo em toda janela futura, porque drift manual continua sendo um vetor real de regressao.

## 4. Qual foi o ganho do upgrade do droplet

O ganho tecnico esperado do resize para `2 GB / 2 vCPU` e este:

1. mais headroom de CPU para absorver burst legitimo do web check, do dashboard Transport e do proprio runtime Python;
2. mais margem de memoria para coexistencia de Nginx, Postgres, API, Playwright e Chromium sem trabalhar tao perto do limite;
3. reducao do risco imediato de nova saturacao enquanto as correcoes estruturais entram em producao.

Limite declarado do ganho:

1. isso nao substitui o desacoplamento do Forms, o endurecimento do runtime HTTP, a reducao de burst do cliente e o controle de banco;
2. se a IA de transporte vier a ser habilitada no futuro, `2 GB / 2 vCPU` continua sendo baseline minimo prudente, nao garantia de folga definitiva.

## 5. Por que a IA de transporte continua desabilitada ou em gate

Ela continua desabilitada ou em gate porque o programa explicitamente proibiu habilitacao prematura e o stack atual ainda depende destes gates:

1. `docker-compose.yml` mantem `TRANSPORT_AI_ENABLED=false` por default;
2. `deploy/deploy_do_ssh.ps1` bloqueia deploy com IA habilitada sem `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE` e `TRANSPORT_AI_MAX_CONCURRENT_RUNS` validos;
3. `docs/acesso_Digital_Ocean.md` registra que o host foi reconciliado para continuar operando com a IA desabilitada;
4. a IA ainda exige validacao dedicada de carga e de readiness na superficie `/api/transport/ai/*` antes de qualquer abertura;
5. o proprio programa separa a readiness da IA do fix principal do incidente do web check.

## 6. Gatilhos tecnicos para reabrir este programa

Este programa deve ser reaberto imediatamente se ocorrer qualquer um dos eventos abaixo:

1. reaparecimento de `504`, `5xx` sustentado ou `upstream timed out` nas rotas criticas do web check, admin ou transport;
2. health local verde e health publico vermelho em `/api/health`;
3. `forms-worker` `stale` com backlog crescente ou fila envelhecendo acima do threshold critico;
4. banco cruzando thresholds criticos de conexao, espera ou p95 de query;
5. drift critico entre `nginx -T` ativo e os arquivos versionados do edge;
6. tentativa de abrir multiworker sem nova prova executavel em PostgreSQL real;
7. habilitacao da IA de transporte sem os gates operacionais e sem validacao dedicada;
8. degradacao regressiva observada no harness da Fase 10 ou no before/after de producao controlada.

## 7. Decisao final de aceite

Aceite tecnico desta sessao:

1. aprovado para rollout controlado por ondas;
2. nao aprovado para encerramento irrestrito do incidente antes da execucao host-side das ondas finais e da evidencia real da Fase 10 em alvo que sirva corretamente `/checking/user`, `/checking/admin` e `/checking/transport`;
3. qualquer declaracao de resolucao definitiva deve citar tambem a execucao real das ondas 0, 0A, 6, 8, 9 e 10 em producao ou homologacao operacional equivalente.

## Rollback

Rollback desta etapa documental:

1. remover `docs/incidents/2026-05-06-504-phase11-technical-acceptance.md`;
2. manter os relatorios tecnicos anteriores como fonte primaria de aceite parcial por fase.

## Proximo passo recomendado

Executar a Onda 0 no host, abrir a janela controlada de Onda 0A em seguida, e reservar a primeira corrida real do harness da Fase 10 como evidencia obrigatoria antes do encerramento definitivo do incidente.