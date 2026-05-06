# Nota de decisao - Fase 0A - ampliacao imediata do droplet

## Decisao

Recomendacao tecnica: sim, ampliar imediatamente o droplet para `2 GB RAM / 2 vCPU`, tratando a mudanca como mitigacao de capacidade e ganho de headroom, e nao como resolucao da causa raiz.

## Base usada nesta decisao

- O baseline consolidado em `docs/incidents/2026-05-04-504-phase0-baseline.md` registra incidente publico com `504`, `upstream timed out`, app `unhealthy`, banco `healthy` e recuperacao apenas apos reboot do droplet.
- O plano tecnico em `docs/temp_007.md` registra que o ambiente atual combina Nginx, Postgres, API Python e processamento pesado de Forms com Playwright/Chromium na mesma infraestrutura operacional.
- O `docker-compose.yml` versionado confirma que `db` e `app` compartilham a mesma stack local e que o Postgres opera com `max_connections=40`, enquanto o app continua exposto na mesma maquina.
- A Fase 0 ainda esta parcialmente bloqueada por falta de coleta host-side completa; portanto, esta decisao usa o melhor baseline tecnico hoje disponivel e nao afirma fatos nao medidos no painel da DigitalOcean.

## Beneficio esperado

- Aumentar para `2 GB / 2 vCPU` reduz o risco imediato de nova saturacao enquanto o programa estrutural ainda nao desacoplou o worker pesado do processo HTTP.
- O ganho de CPU ajuda a absorver melhor concorrencia legitima de bootstrap web, autenticacao, localizacao, check-in/check-out e qualquer disputa com Playwright/Chromium no mesmo host.
- O ganho de memoria amplia a margem operacional para Nginx, Postgres, runtime Python, navegador headless e buffers de rede coexistirem sem trabalhar tao perto do limite sob burst legitimo.
- O resize compra headroom para executar as proximas fases com menor chance de repetir o sintoma operacional antes que o desacoplamento do Forms e o hardening do runtime HTTP estejam prontos.

## Limite desta mitigacao

- O resize nao remove a causa estrutural mais provavel: trabalho pesado e runtime HTTP ainda compartilham blast radius.
- Se o burst vier da SPA de check e o app continuar single-process ou pouco concorrente, o sistema ainda pode degradar; a diferenca e que isso tende a ocorrer em um patamar mais alto de carga.
- O resize nao resolve, por si so, drift de Nginx, healthchecks insuficientes, ausencia de observabilidade, burst redundante do cliente ou gargalos de banco.
- Se a IA de transporte vier a ser habilitada no futuro, `2 GB / 2 vCPU` deve ser tratado como baseline minimo de prudencia, nao como garantia de folga definitiva.

## Risco de nao fazer agora

- Manter o host no patamar atual deixa pouca margem para novo pico legitimo de uso enquanto as correcoes estruturais ainda nao foram entregues.
- Isso aumenta a chance de repeticao do mesmo padrao operacional: app degradando sob burst, edge acumulando `504` e recuperacao dependente de intervencao manual.
- Tambem aumenta o risco de as proximas fases serem executadas em ambiente ja tensionado, tornando sinais de validacao menos confiaveis e abrindo nova janela de incidente antes do desacoplamento correto.
- Em termos práticos, nao fazer agora preserva custo, mas aceita conscientemente operar com headroom insuficiente num host que concentra banco, edge, runtime Python e workload pesado.

## Premissas e lacunas declaradas

- Esta nota assume como baseline de trabalho a configuracao mencionada no programa: host atual de `1 GB RAM / 1 vCPU` e stack consolidada no mesmo droplet.
- Esta nota nao confirma tamanho atual do droplet via painel ou CLI da DigitalOcean, porque esse acesso nao esta disponivel nesta execucao.
- Se a verificacao operacional mostrar que o host ja esta em `2 GB / 2 vCPU` ou acima, esta decisao deve ser reinterpretada como ja cumprida e a mitigacao imediata deixa de ser resize, passando a ser apenas monitoramento e validacao pos-capacidade.