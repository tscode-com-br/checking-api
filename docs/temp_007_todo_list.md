# Checklist executável e priorizado para eliminar o erro 504

## 0. Contrato global de execução para o agente que vai usar esta checklist

Antes de executar qualquer prompt abaixo, o agente executor deve obedecer a este contrato.

### 0.1 Regras globais de segurança

1. Nunca assumir contexto ausente. Se um prompt depender de acesso ao host, credenciais, variáveis de ambiente, segredos, painel da DigitalOcean ou arquivos fora do repo, o agente deve declarar explicitamente a dependência e pedir ou preparar um procedimento alternativo sem inventar resultados.
2. Nunca reiniciar host, container, Nginx, Postgres, worker ou processo HTTP, exceto quando o prompt autorizar explicitamente e depois da coleta mínima de evidências exigida para aquela fase.
3. Nunca sobrescrever ou reverter mudanças não relacionadas já existentes no workspace sem autorização explícita.
4. Nunca habilitar a IA de transporte em produção durante este programa, salvo se uma fase posterior disser expressamente que todos os gates técnicos foram cumpridos e a validação específica foi aprovada.
5. Nunca colocar multiworker em produção sem resolver o barramento de realtime cross-worker.
6. Nunca tratar aumento de CPU/RAM do droplet como substituto do desacoplamento do Forms, do hardening do runtime HTTP ou da redução de burst do cliente.
7. Nunca concluir uma fase apenas porque o código foi alterado; a fase só termina quando a validação prevista tiver passado e a evidência tiver sido salva.

### 0.2 Regras globais de execução técnica

1. Antes de editar qualquer arquivo, o agente deve identificar o ponto exato de alteração e nomear a hipótese local que a mudança pretende validar ou implementar.
2. Depois da primeira edição substantiva de uma fase, a próxima ação deve ser uma validação focada daquela mudança.
3. Se uma validação falhar, o agente deve corrigir a mesma superfície antes de ampliar o escopo.
4. Quando uma fase envolver produção, o agente deve separar claramente o que foi apenas observado, o que foi alterado no repo e o que foi alterado no host.
5. Quando uma fase envolver host DigitalOcean, o agente deve produzir trilha de evidências brutas e relatório consolidado.
6. Quando uma fase envolver frontend, o agente deve explicitar quais eventos de UI, timers, streams, polls ou requests foram alterados e como isso reduz burst.
7. Quando uma fase envolver banco, o agente deve explicitar pool, limites, queries afetadas, índices, locks e evidência de validação.
8. Quando uma fase envolver edge, o agente deve explicitar configuração anterior, configuração nova, comando de teste sintático e comando de validação funcional.

### 0.3 Formato mínimo de resposta para cada prompt executado

Cada execução de prompt deve terminar com um relatório curto no seguinte formato:

1. `Objetivo executado`: o que foi feito nesta execução.
2. `Hipótese ou risco atacado`: qual problema este prompt atacou.
3. `Arquivos alterados`: lista de arquivos modificados no repo, se houver.
4. `Comandos executados`: lista objetiva de comandos relevantes, se houver.
5. `Evidências geradas`: caminhos de arquivos, logs, relatórios ou artefatos produzidos.
6. `Validação executada`: testes, curls, medições ou checks rodados após a mudança.
7. `Resultado`: aprovado, parcialmente aprovado ou bloqueado.
8. `Rollback`: como desfazer apenas esta execução, se aplicável.
9. `Próximo passo recomendado`: qual prompt deve ser executado na sequência.

### 0.4 Condições de parada obrigatória

O agente deve parar e reportar bloqueio, sem improvisar, quando ocorrer qualquer uma destas condições:

1. acesso inexistente ao host ou a credenciais necessárias para a fase;
2. drift grave entre host e repo que torne a mudança insegura sem reconciliação prévia;
3. fila, banco ou runtime em estado desconhecido que tornaria rollback cego;
4. validação de produção falhando sem evidências suficientes para decidir rollback com segurança;
5. risco de perda de dados, fila persistida ou estado operacional não reconstituível;
6. dependência de segredo, token ou painel que não esteja disponível ao agente executor.

### 0.5 Checklist de encerramento de cada fase

Antes de considerar qualquer fase concluída, o agente deve confirmar explicitamente que:

1. a mudança foi implementada na menor superfície correta;
2. a validação prevista foi realmente executada;
3. a evidência foi salva em caminho conhecido;
4. o critério de rollback foi documentado;
5. o impacto em produção, host, banco, edge, worker e cliente foi declarado quando aplicável;
6. o próximo prompt dependente desta fase está claro.

## 1. Decisões obrigatórias antes de iniciar

### Decisão A - IA de transporte entra no programa, mas não entra no caminho crítico do fix imediato

1. A IA de transporte deve entrar neste programa como trilha preventiva e de readiness para produção futura.
2. A IA de transporte não deve bloquear o fix principal do incidente do web check.
3. A IA de transporte não deve ser habilitada em produção apenas porque o código local existe.
4. Qualquer rollout futuro da IA de transporte deve ficar condicionado a:
   - fila e worker pesado desacoplados do processo HTTP;
   - runtime HTTP endurecido;
   - broker de realtime compatível com multiworker;
   - rate control no dashboard Transport;
   - teste de carga e validação específicos da superfície `/transport` e `/api/transport/ai/*`.
5. Até essa trilha preventiva ser concluída, a IA de transporte deve permanecer desabilitada em produção por flag, configuração ou ausência deliberada de credenciais e rotas expostas.

### Decisão B - Aumentar o droplet ajuda, mas não substitui a correção estrutural

1. Aumentar o servidor de `1 GB RAM / 1 vCPU` para `2 GB RAM / 2 vCPU` ajuda de forma material a reduzir o risco imediato de saturação.
2. Essa ampliação é recomendada como mitigação de capacidade e headroom, principalmente porque a stack atual combina Python, Postgres, Nginx, Playwright e Chromium no mesmo host.
3. Esse upgrade não deve ser tratado como resolução da causa raiz.
4. Se a arquitetura continuar compartilhando runtime HTTP e trabalho pesado, o sistema ainda pode colapsar em bursts futuros, apenas em um patamar mais alto de carga.
5. Se a IA de transporte vier a ser habilitada depois, `2 GB / 2 vCPU` deve ser tratado como baseline mínimo, não como garantia de folga definitiva.

## 2. Issues técnicas priorizadas

## Issue P0 - Baseline operacional e coleta forense mínima

Ordem de entrega: 1
Prioridade: P0
Objetivo: congelar o estado real do host, do Docker, do Nginx e do runtime antes de qualquer mudança invasiva.
Rollback: não aplicável, porque esta issue é apenas de coleta e comparação.

## Issue P0A - Mitigação imediata de capacidade do droplet

Ordem de entrega: 2
Prioridade: P0
Objetivo: adicionar headroom de CPU e RAM para reduzir o risco de nova saturação enquanto as correções estruturais são implementadas.
Rollback: reverter o tamanho do droplet apenas depois de ao menos uma janela estável em produção e com comparativo de métricas antes/depois.

## Issue P1 - Observabilidade mínima da API, fila e worker

Ordem de entrega: 3
Prioridade: P0
Objetivo: transformar degradação em algo observável por rota, fila, banco e container.
Rollback: manter logs e métricas novas; não remover a instrumentação, exceto se ela causar regressão funcional comprovada.

## Issue P2 - Desacoplamento do Forms do processo HTTP

Ordem de entrega: 4
Prioridade: P0
Objetivo: impedir que backlog ou lentidão do Forms derrubem login, estado, histórico, admin e mobile.
Rollback: voltar temporariamente ao modelo atual apenas se o worker separado impedir processamento de operação crítica e houver fila persistida preservada.

## Issue P3 - Hardening do runtime HTTP e do realtime multiworker

Ordem de entrega: 5
Prioridade: P0
Objetivo: permitir maior concorrência HTTP sem quebrar SSE, stream e atualizações entre workers.
Rollback: voltar para runtime single-process somente se o broker cross-worker não estiver estável; se isso ocorrer, manter a redução de burst e a separação do Forms já entregues.

## Issue P4 - Redução de burst do web check

Ordem de entrega: 6
Prioridade: P0
Objetivo: reduzir a tempestade de requests gerada pela SPA de check em bootstrap, autenticação, foco e localização.
Rollback: reverter apenas os trechos de UX que bloquearem fluxo legítimo; manter toda a telemetria de requests criada para comparar antes/depois.

## Issue P5 - Hot paths, pool de banco e firewall do Postgres

Ordem de entrega: 7
Prioridade: P1
Objetivo: reduzir latência das rotas mais quentes e evitar espera por conexões ou queries ruins.
Rollback: reverter individualmente query plans, índices ou parâmetros de pool que mostrem piora de latência ou bloqueio inesperado.

## Issue P6 - Reconciliação do edge Nginx e proteção por superfície

Ordem de entrega: 8
Prioridade: P1
Objetivo: alinhar repo e host e aplicar políticas adequadas por rota, classe de cliente e upstream.
Rollback: restaurar imediatamente a configuração anterior do Nginx a partir de backup validado com `nginx -t` se qualquer mudança gerar 4xx/5xx anormais ou quebra de roteamento.

## Issue P7 - Hardening preventivo do dashboard Transport e readiness da IA de transporte

Ordem de entrega: 9
Prioridade: P1
Objetivo: impedir que o dashboard Transport ou a futura IA de transporte introduzam novo vetor de saturação.
Rollback: manter a IA desabilitada em produção e reverter apenas as mudanças de UI que causem regressão operacional no `/transport`.

## Issue P8 - Startup, migração e deploy sem janelas frágeis

Ordem de entrega: 10
Prioridade: P1
Objetivo: remover acoplamento entre migração, boot HTTP e readiness pública.
Rollback: restaurar o processo anterior de startup apenas se o novo fluxo impedir a subida da stack; nesse caso, manter os artefatos e logs para corrigir o rollout e não improvisar no host.

## Issue P9 - Harness de reprodução e teste de carga recorrente

Ordem de entrega: 11
Prioridade: P1
Objetivo: provar sob carga que o incidente foi resolvido e não apenas deslocado.
Rollback: não aplicável; a issue produz teste e relatório, não altera runtime por si só.

## Issue P10 - Rollout, runbook, alertas e aceite final

Ordem de entrega: 12
Prioridade: P0
Objetivo: colocar as mudanças em produção com checkpoints, rollback e operação repetível.
Rollback: executar a matriz de rollback por issue, preservando evidências e sem rebootar antes da coleta mínima definida no runbook.

## 3. Fase 0 - Checklist operacional objetivo para o host DigitalOcean

### Contexto da fase

Objetivo: congelar o baseline do host, do Docker, do Nginx e do runtime efetivo de produção antes das correções.

Critério de conclusão: existe um conjunto de evidências brutas e um resumo consolidado, sem depender de memória informal.

Critério de rollback: não aplicável.

### Prompts executáveis

1. Você é o agente responsável por congelar o baseline do incidente no host DigitalOcean. Trabalhe em modo somente coleta: não reinicie serviços, não mude configurações e não rode deploy. Acesse o host com o usuário operacional correto e crie um diretório de evidências com timestamp, por exemplo `/root/checkcheck_incidents/2026-05-04-504-phase0` ou caminho equivalente aprovado pela equipe. Dentro desse diretório, salve a saída bruta de `date -u`, `timedatectl`, `uptime`, `hostnamectl`, `uname -a`, `free -m`, `df -h`, `nproc`, `lscpu` e `cat /etc/os-release`. No final, gere um resumo curto explicando timezone ativo, horário de boot, memória total, CPU total e espaço em disco. Se você não tiver acesso SSH neste contexto, não invente resultados: produza um pacote de comandos pronto para execução e descreva exatamente quais arquivos de evidência devem ser devolvidos.

2. Você é o agente responsável por congelar o estado do Docker e dos containers de produção. No host, identifique o diretório real da stack e execute `docker ps --no-trunc`, `docker compose ps`, `docker inspect checkcheck-app-1`, `docker inspect checkcheck-db-1`, `docker logs --tail 500 checkcheck-app-1` e `docker logs --tail 200 checkcheck-db-1`, salvando cada comando em arquivo separado dentro do diretório de evidências. Extraia explicitamente de `docker inspect` os campos `State.Status`, `State.Health`, `RestartCount`, `StartedAt`, `FinishedAt`, `OOMKilled` e qualquer detalhe de `Health.Log`. Gere um resumo final dizendo se o app está `healthy`, `unhealthy`, reiniciando ou apenas vivo sem responder utilmente.

3. Você é o agente responsável por congelar a configuração ativa do Nginx e comparar edge real com repo. No host, execute `nginx -T` e salve a saída integral em arquivo. Em seguida, copie para o relatório os blocos `server` e `location` que governam `tscode.com.br`, `/api/`, `/checking/user`, `/checking/admin` e `/checking/transport`. Compare essa configuração ativa com o arquivo versionado `deploy/nginx/checking-edge-routes.conf` do repo. No resultado, responda objetivamente: o host está roteando para `127.0.0.1:8000`, para `18080/18081/18082/18083`, ou para ambos em configurações diferentes? Liste qualquer drift encontrado e marque cada divergência como `crítica`, `importante` ou `cosmética`.

4. Você é o agente responsável por congelar logs e sinais do incidente no edge. Colete a janela relevante dos logs de acesso e erro do Nginx. Salve, no mínimo, a saída de comandos equivalentes a `grep ' 504 ' access.log`, `grep 'upstream timed out' error.log`, `tail -n 500 error.log`, `tail -n 500 access.log` e qualquer `journalctl -u nginx` relevante. Se os logs estiverem rotacionados, colete também os arquivos rotacionados. Agrupe no relatório final por rota, host, status, user-agent e IP de origem, destacando especialmente `/checking/user`, `/checking/admin`, `/api/web/check/state`, `/api/mobile/state`, `/api/admin/stream`, `/api/admin/checkin`, `/api/admin/checkout` e `/api/admin/projects`.

5. Você é o agente responsável por verificar se a API responde local e publicamente no estado atual do host. Sem alterar nada, execute e salve a saída de `curl -i http://127.0.0.1:8000/api/health`, `curl -i https://tscode.com.br/api/health`, `curl -i https://tscode.com.br/checking/user` e `curl -i https://tscode.com.br/checking/admin`, respeitando cookies ou autenticação apenas quando a rota exigir. Adicione ao relatório final a diferença entre saúde local do upstream e saúde pública no edge.

6. Você é o agente responsável por consolidar a Fase 0 em um único relatório versionado no repo, preferencialmente em `docs/incidents/2026-05-04-504-phase0-baseline.md` ou arquivo equivalente aprovado. O relatório deve conter: linha do tempo mínima, topologia ativa, estado dos containers, upstreams reais do Nginx, sinais locais e públicos de saúde, e lista objetiva de drifts entre repo e host. Não proponha correções ainda nesta etapa; apenas registre fatos, evidências e lacunas.

## 4. Fase 0A - Mitigação imediata de capacidade do droplet

### Contexto da fase

Objetivo: adicionar headroom para reduzir risco enquanto as mudanças estruturais são implementadas.

Critério de conclusão: existe decisão documentada sobre o resize e validação técnica antes/depois.

Critério de rollback: reduzir novamente o tamanho do droplet apenas depois de estabilidade comprovada e com aprovação operacional.

### Prompts executáveis

1. Você é o agente responsável por decidir tecnicamente se o droplet deve ser ampliado imediatamente para `2 GB RAM / 2 vCPU`. Baseie-se nas evidências da Fase 0, no fato de a stack atual combinar Nginx, Postgres, Python, Playwright e Chromium no mesmo host, e na leitura de risco do incidente. Produza uma nota de decisão curta com três blocos: `benefício esperado`, `limite desta mitigação`, `risco de não fazer agora`.

2. Você é o agente responsável por executar ou preparar a ampliação do droplet, dependendo do nível de acesso que tiver. Se tiver acesso ao painel ou CLI da DigitalOcean, documente exatamente o tipo atual do droplet, o tipo alvo, a janela de mudança, a necessidade ou não de power cycle, e os passos de validação pós-mudança. Se não tiver acesso, gere um procedimento operacional objetivo para outro executor, incluindo pré-requisitos, captura de evidências antes da mudança e checklist pós-mudança.

3. Você é o agente responsável por validar o host após a ampliação. Depois do resize, repita `free -m`, `nproc`, `lscpu`, `docker compose ps`, `curl -i http://127.0.0.1:8000/api/health` e `curl -i https://tscode.com.br/api/health`, e compare os resultados com a Fase 0. Registre explicitamente se houve efeito colateral em Docker, Nginx, mounts, network ou healthchecks.

## 5. Fase 1 - Observabilidade mínima da API, fila, worker e banco

### Contexto da fase

Objetivo: tornar a degradação observável por rota, fila, processo e banco.

Critério de conclusão: o time consegue identificar rapidamente onde a pressão nasce.

Critério de rollback: reverter apenas instrumentação que introduzir regressão funcional mensurável.

### Prompts executáveis

1. Você é o agente responsável por adicionar instrumentação de requests no backend Python. Audite `sistema/app/main.py`, middlewares existentes, routers em `sistema/app/routers/` e o ponto mais apropriado para inserir middleware de request logging estruturado. Implemente logs estruturados contendo, no mínimo, `request_id`, `method`, `path`, `status_code`, `latency_ms`, `client_surface`, `authenticated_kind` quando possível e um marcador se a resposta veio de rota crítica. Evite logar segredos, payloads sensíveis ou dados pessoais completos. Depois, descreva como validar a nova telemetria localmente e em produção.

2. Você é o agente responsável por adicionar telemetria da fila do Forms e do worker separado ou futuro worker. Audite `sistema/app/services/forms_queue.py`, `sistema/app/services/forms_worker.py`, `sistema/app/main.py` e qualquer model relacionada a `forms_submissions`. Exponha sinais suficientes para responder: quantos itens estão pendentes, quantos estão em processamento, idade do item mais antigo, tempo médio de processamento, total de falhas e total de sucessos. Se a stack atual ainda não tiver sistema de métricas consolidado, implemente ao menos logs estruturados e endpoints leves de diagnóstico que possam ser consultados operacionalmente.

3. Você é o agente responsável por expor sinais mínimos do banco e do pool de conexões. Audite `sistema/app/database.py` e as superfícies mais quentes da API. Se não houver sistema pronto de métricas, implemente ao menos logs e um endpoint ou utilitário operacional capaz de reportar saturação de pool, latência de query agregada e contagem de conexões relevantes. Documente quais limites devem virar alerta, mesmo que o alerta final seja configurado em fase posterior.

4. Você é o agente responsável por definir o pacote mínimo de alertas operacionais que precisa existir antes do rollout principal. Produza uma lista priorizada com thresholds iniciais para `5xx`, latência p95/p99 por rota crítica, backlog da fila do Forms, `unhealthy` do app, `RestartCount` anormal, CPU alta, memória alta e conexões de banco elevadas. Se a stack de monitoração ainda não estiver pronta, descreva o fallback operacional temporário com comandos e logs a consultar.

## 6. Fase 2 - Desacoplamento do Forms do processo HTTP

### Contexto da fase

Objetivo: retirar Playwright e Chromium do mesmo processo ou container que responde HTTP.

Critério de conclusão: falha ou backlog do Forms não derruba a API.

Critério de rollback: manter a fila persistida e reverter apenas o wiring entre app e worker se o novo consumo impedir processamento operacional.

### Prompts executáveis

1. Você é o agente responsável por mapear o fluxo atual do Forms de ponta a ponta. Audite `sistema/app/routers/device.py`, `sistema/app/routers/mobile.py`, `sistema/app/routers/web_check.py`, `sistema/app/services/forms_submit.py`, `sistema/app/services/forms_queue.py`, `sistema/app/services/forms_worker.py` e `sistema/app/main.py`. Escreva um resumo técnico objetivo indicando onde a API grava o item de fila, onde o worker é iniciado hoje, quais recursos pesados o worker usa e por que isso amplia blast radius. Não mude código ainda nesta primeira tarefa; apenas documente o desenho atual e o desenho alvo.

2. Você é o agente responsável por implementar um worker de Forms separado da API. Escolha a menor mudança correta que mantenha o contrato atual dos endpoints: a API deve continuar aceitando o evento, persistindo a fila e respondendo rápido, enquanto um processo ou serviço separado consome `forms_submissions`. Ajuste `docker-compose.yml`, `Dockerfile` e os entrypoints necessários para que o worker rode separado do app HTTP. Se a melhor opção for um novo script de inicialização ou módulo dedicado, crie-o de forma clara e versionada.

3. Você é o agente responsável por revisar a robustez do novo worker. Implemente e valide política de retentativa, backoff, logs estruturados, reinício automático e forma mínima de health observável do worker. O worker não deve bloquear o app HTTP ao falhar, e o app HTTP não deve depender do worker para responder rotas críticas. Documente como o backlog deve ser inspecionado em produção.

4. Você é o agente responsável por validar a isolação do Forms. Monte um experimento local ou controlado que gere backlog de `forms_submissions` suficiente para pressionar o worker. Durante esse backlog, prove com evidências que `/api/health`, login, `/api/web/check/state` e demais rotas quentes continuam respondendo sem degradação comparável ao incidente. Se a validação falhar, pare e documente o bloqueador antes de ampliar o escopo.

## 7. Fase 3 - Hardening do runtime HTTP e do realtime multiworker

### Contexto da fase

Objetivo: permitir mais concorrência HTTP sem quebrar SSE e updates entre workers.

Critério de conclusão: runtime HTTP endurecido e updates cross-worker consistentes.

Critério de rollback: manter single-process temporariamente apenas se o barramento de eventos cross-worker ainda não estiver seguro.

### Prompts executáveis

1. Você é o agente responsável por auditar o runtime HTTP atual e propor o runtime de produção final. Use `Dockerfile`, `docker-compose.yml`, `sistema/app/main.py` e o estado real da produção para responder: quantos workers existem hoje, qual servidor ASGI/WSGI é mais apropriado, como tratar keepalive, timeouts e quantos processos devem existir para `2 GB / 2 vCPU`. Entregue uma proposta objetiva e justificada, com a menor mudança correta para produção.

2. Você é o agente responsável por auditar o realtime atual antes de habilitar multiworker. Leia `sistema/app/services/admin_updates.py`, `sistema/app/routers/admin.py`, `sistema/app/routers/transport.py` e `sistema/app/routers/web_check.py` e identifique toda dependência de broker em memória do processo. Se a aplicação depender hoje de `admin_updates_broker` e `transport_updates_broker` locais ao processo, proponha e implemente um barramento cross-worker adequado, preferencialmente pequeno e operacionalmente simples para a stack do projeto. Se a sua proposta exigir Redis, explicite isso claramente no diff e na documentação.

3. Você é o agente responsável por implementar o novo runtime HTTP de produção de modo compatível com o barramento de eventos escolhido. Ajuste o comando de startup, a imagem, o compose e qualquer documentação operacional necessária. Garanta que os fluxos de SSE ou stream do admin, do transport e do web check continuem coerentes quando a aplicação tiver mais de um processo HTTP.

4. Você é o agente responsável por validar consistência multiworker. Execute um teste controlado com mais de um processo HTTP, abra sessões do admin e do transport, gere eventos que publiquem updates e prove que as telas continuam recebendo refresh coerente mesmo quando as requests caem em workers diferentes. Se não conseguir provar isso, não autorize rollout do multiworker.

## 8. Fase 4 - Healthcheck, readiness e auto-recuperação reais

### Contexto da fase

Objetivo: detectar degradação útil e sair dela sem reboot manual imediato.

Critério de conclusão: health, readiness e restart passam a representar o estado real da aplicação.

Critério de rollback: restaurar healthcheck anterior apenas se o novo modelo gerar falso positivo severo e indisponibilidade operacional, preservando logs e evidências.

### Prompts executáveis

1. Você é o agente responsável por redefinir a semântica de saúde da aplicação. Audite o endpoint atual `/api/health`, o `healthcheck` do `docker-compose.yml`, o comando de startup e as dependências essenciais do app. Proponha um modelo claro de `liveness`, `readiness` e `degraded`, mesmo que a stack atual implemente isso por aproximação prática. Seja explícito sobre o que precisa ser considerado indispensável para o app estar apto a receber tráfego.

2. Você é o agente responsável por implementar healthchecks mais fiéis ao estado real do sistema. Ajuste o endpoint de health e o compose para que o app não pareça saudável quando estiver vivo, mas incapaz de responder utilmente. Trate a API HTTP e o worker de Forms como componentes diferentes: a falha do worker não deve mascarar a saúde da API, mas também não pode ficar invisível.

3. Você é o agente responsável por definir a auto-recuperação operacional. Documente e, quando a stack permitir, implemente a estratégia de restart ou remediação automática para estados `unhealthy` sustentados, incluindo limites para evitar loops cegos. O resultado deve dizer claramente quando reiniciar apenas o worker, quando reiniciar a API e quando parar para coleta de evidências antes de qualquer reboot maior.

## 9. Fase 5 - Redução de burst da SPA de check

### Contexto da fase

Objetivo: diminuir a tempestade de requests gerada pela superfície `sistema/app/static/check`.

Critério de conclusão: queda material de requests por usuário e por fluxo de uso.

Critério de rollback: reverter apenas ajustes de UX que quebrem uso legítimo; manter telemetria para comparar o impacto real.

### Prompts executáveis

1. Você é o agente responsável por mapear o grafo de requests da SPA de check. Audite `sistema/app/static/check/app.js` e identifique, com nomes de funções e endpoints, tudo o que dispara requests em bootstrap, restauração de sessão, verificação de senha, `focus`, `pageshow`, `visibilitychange`, localização e submit. Entregue uma matriz `evento -> função -> endpoint -> frequência esperada -> risco de burst` antes de alterar o código.

2. Você é o agente responsável por reduzir tempestade de autenticação. Trabalhe sobre `refreshAuthenticationStatus`, `schedulePasswordVerification`, `attemptPasswordLogin`, `loadAuthenticatedApplication` e qualquer fluxo de autofill/autologin equivalente em `sistema/app/static/check/app.js`. A meta é impedir login silencioso repetitivo, validação parcial agressiva e loops desnecessários quando muitos usuários digitam ou retornam à tela. Preserve a UX funcional, mas privilegie estabilidade operacional.

3. Você é o agente responsável por reduzir tempestade de lifecycle e localização. Trabalhe sobre `runLifecycleUpdateSequence`, `updateLocationForLifecycleSequence`, `ensureLocationReadyForSubmit`, `refreshHistory` e os listeners de `visibilitychange`, `focus` e `pageshow`. Introduza deduplicação, cooldown mais inteligente, cache local com invalidação clara, e evite reconsultas redundantes de histórico e localização quando não houver mudança real de estado.

4. Você é o agente responsável por validar a redução de burst da SPA. Monte uma medição antes/depois com contagem de requests por usuário em pelo menos estes cenários: abrir o QR Code, autenticar, voltar da tela bloqueada, alternar abas, conceder localização e registrar check-in/check-out. O relatório deve mostrar claramente quais endpoints foram mais aliviados.

## 10. Fase 6 - Hot paths do backend, pool de banco e firewall do Postgres

### Contexto da fase

Objetivo: reduzir custo das rotas quentes e impedir saturação por pool ou banco.

Critério de conclusão: rotas quentes melhoram de forma mensurável e o banco deixa de ser amplificador oculto.

Critério de rollback: reverter ajustes isolados de query, índice ou pool que piorarem latência ou bloqueio.

### Prompts executáveis

1. Você é o agente responsável por auditar e otimizar as rotas quentes do backend. Comece por `/api/web/check/state`, `/api/mobile/state`, `/api/admin/checkin`, `/api/admin/checkout` e `/api/admin/projects`. Audite routers, services, serialização e queries correspondentes. Corrija repetições, N+1, joins caros, serialização excessiva e qualquer trabalho desnecessário por request. Se um endpoint estiver fazendo mais do que o necessário para bootstrap, considere separar leituras especializadas.

2. Você é o agente responsável por endurecer o pool de conexões e a camada de acesso ao banco. Audite `sistema/app/database.py`, a configuração atual de `create_engine`, o `max_connections=40` do Postgres em `docker-compose.yml` e o padrão real de concorrência esperado. Proponha e implemente parâmetros explícitos de pool, overflow, timeout e reciclagem, com justificativa técnica. Não escolha valores arbitrários; conecte a decisão ao tamanho do host e ao número alvo de workers/processos.

3. Você é o agente responsável por reduzir risco operacional do Postgres exposto. Verifique se a porta `5432` está de fato acessível externamente, avalie o ruído já observado com o usuário inexistente `reader` e proponha a menor mudança correta para fechar ou restringir esse acesso. Se a mudança envolver host, firewall ou compose, documente exatamente onde o controle deve viver e como validar que o app interno continua funcionando.

4. Você é o agente responsável por validar os ganhos de backend e banco. Rode medições de latência p50, p95 e p99 das rotas quentes, e registre o uso de conexões de banco antes e depois das mudanças. Se algum ajuste melhorar uma rota e piorar outra, documente o tradeoff explicitamente antes de seguir.

## 11. Fase 7 - Reconciliação do edge Nginx e proteção por superfície

### Contexto da fase

Objetivo: alinhar repo e host e aplicar políticas de edge coerentes com o novo runtime.

Critério de conclusão: configuração ativa do host coincide com a configuração versionada e com a topologia final.

Critério de rollback: restaurar backup da configuração anterior e validar com `nginx -t` antes de reload se qualquer teste falhar.

### Prompts executáveis

1. Você é o agente responsável por reconciliar o Nginx real com o repo. Use o `nginx -T` capturado na Fase 0 e compare com `deploy/nginx/checking-edge-routes.conf`. Defina a topologia final de upstreams e documente explicitamente se a produção deve continuar com `127.0.0.1:8000`, migrar para `18080/18081/18082/18083` ou adotar outra forma clara e versionada. Não aceite drift manual como estado final.

2. Você é o agente responsável por endurecer o edge por classe de superfície. Revise `proxy_read_timeout`, `proxy_connect_timeout`, buffering, keepalive e políticas distintas para API, HTML, SSE/stream e autenticação. Introduza proteção de burst ou rate limit nas superfícies mais sensíveis, sem quebrar uso legítimo da equipe. Toda política nova deve vir acompanhada de justificativa e plano de validação.

3. Você é o agente responsável por validar o edge final. Gere backup da configuração anterior, rode `nginx -t`, aplique reload seguro, teste `curl` local e público para `/api/health`, `/checking/user`, `/checking/admin` e `/checking/transport`, e confirme que a configuração ativa no host voltou a coincidir com o repo. Registre qualquer dependência manual que ainda restar e trate isso como débito a eliminar, não como solução definitiva.

## 12. Fase 8 - Hardening preventivo do dashboard Transport e readiness da IA de transporte

### Contexto da fase

Objetivo: evitar que o dashboard Transport ou a futura IA introduzam novo vetor de saturação.

Critério de conclusão: o `/transport` fica mais eficiente e a IA futura permanece sob gate de segurança.

Critério de rollback: manter a IA desabilitada e reverter apenas mudanças de dashboard que causem regressão funcional comprovada.

### Prompts executáveis

1. Você é o agente responsável por auditar o comportamento de rede do dashboard Transport. Trabalhe em `sistema/app/static/transport/app.js` e foque, no mínimo, nestas funções ou trechos: `requestDashboardRefresh`, `startRealtimeUpdates`, `scheduleTransportVerification`, `loadDashboard`, qualquer `authVerifyTimer`, qualquer `realtimeRefreshTimer` e qualquer `aiRoutePollingTimer`. O objetivo é identificar duplicação de `loadDashboard`, tempestade de verificação de credenciais, refresh redundante por SSE e polling de IA desnecessário. Entregue primeiro um mapa `gatilho -> endpoint -> risco -> proposta de mitigação`.

2. Você é o agente responsável por implementar mitigação no dashboard Transport sem degradar operação. Introduza deduplicação de requests em voo, cancelamento ou coalescência de refreshes redundantes, pausa de polling quando a aba estiver invisível, backoff de reconexão para SSE, e guardas para evitar que uma enxurrada de eventos dispare vários `loadDashboard` seguidos. Preserve a funcionalidade do dashboard, mas privilegie estabilidade do backend.

3. Você é o agente responsável por endurecer a verificação de autenticação do dashboard Transport. Revise os listeners de `authKeyInput` e `authPasswordInput`, a função `scheduleTransportVerification` e o fluxo de `bootstrapTransportSession`. Garanta que o dashboard não dispare verificações agressivas por tecla pressionada e que transientes de input não limpem a sessão de forma precipitada. Se houver risco de burst de `/api/transport/auth/verify`, reduza isso sem quebrar a UX.

4. Você é o agente responsável por preparar a IA de transporte para produção futura sem habilitá-la prematuramente. Audite `sistema/app/routers/transport_ai.py`, `sistema/app/services/transport_ai_agent.py`, o polling de `route-calculations` no dashboard e qualquer config relacionada. Mantenha a IA desabilitada por default em produção e implemente, se necessário, guardas explícitas para que a superfície `/api/transport/ai/*` não entre ativa sem: flag operacional habilitada, recursos aprovados, timeouts definidos, limite de concorrência e validação de carga dedicada. Se o código já tiver flag existente, reutilize-a; não crie outra sem motivo forte.

5. Você é o agente responsável por validar o dashboard Transport após o hardening preventivo. Abra múltiplas abas do `/transport`, simule eventos de stream, verificação de auth e refresh de dashboard, e prove que o número de requests caiu ou se manteve sob controle. Se a IA estiver desabilitada, prove também que o dashboard não fica fazendo polling de rotas de IA por acidente.

## 13. Fase 9 - Startup, migração e deploy sem janelas frágeis

### Contexto da fase

Objetivo: remover acoplamento entre migração, boot HTTP e exposure do edge.

Critério de conclusão: deploy e reboot ficam previsíveis e seguros.

Critério de rollback: restaurar o processo anterior apenas se o novo fluxo impedir a subida da stack, preservando evidências e corrigindo o mecanismo antes da próxima tentativa.

### Prompts executáveis

1. Você é o agente responsável por revisar o startup atual do app. Audite o `Dockerfile`, `docker-compose.yml` e qualquer script de deploy relevante. O comando atual faz `alembic upgrade head && uvicorn ...`; avalie o risco disso e implemente o desenho final mais seguro, preferencialmente separando migração de processo HTTP ou, no mínimo, tornando a readiness pública dependente da conclusão real do boot.

2. Você é o agente responsável por endurecer o deploy. Garanta que o fluxo de rollout tenha checkpoints claros: build, migração, subida do runtime HTTP, validação local do health, validação pública do health e só então exposição total do tráfego. Se existir workflow em `.github/workflows/` ou scripts em `deploy/`, atualize-os para refletir esse desenho e elimine qualquer dependência manual fora do repo.

3. Você é o agente responsável por definir rollback de deploy. Para cada mudança de runtime, edge, worker e startup, documente o passo exato de reversão, o teste que confirma rollback válido e a evidência que precisa ser preservada antes de reverter. Não aceite rollback implícito ou baseado em memória da equipe.

## 14. Fase 10 - Harness de reprodução e teste de carga recorrente

### Contexto da fase

Objetivo: provar que o incidente foi resolvido sob carga semelhante ao caso real.

Critério de conclusão: teste repetível aprovado com evidências antes/depois.

Critério de rollback: não aplicável diretamente; o resultado do teste governa rollout e ajustes adicionais.

### Prompts executáveis

1. Você é o agente responsável por criar um harness de carga para o caso real do incidente. O foco principal deve ser a superfície web de check, simulando um grupo de usuários abrindo o QR Code, registrando ou autenticando chave/senha, consultando estado, processando localização e realizando check-in/check-out em janelas curtas. Escolha a ferramenta mais apropriada para o repo e para a stack do projeto, mas entregue uma execução repetível, documentada e com parâmetros ajustáveis.

2. Você é o agente responsável por criar cenários complementares de carga para superfícies relacionadas. Inclua, quando fizer sentido, consultas simultâneas de admin e dashboard Transport, e um experimento separado de backlog do Forms para comprovar que a API não degrada mesmo com o worker ocupado. Não misture tudo em um único teste cego; produza cenários isolados e um cenário integrado.

3. Você é o agente responsável por produzir um relatório antes/depois. O relatório deve conter, no mínimo, throughput, erro, latência p50/p95/p99, uso de CPU, memória, conexões de banco e backlog de fila para o baseline atual e para a arquitetura corrigida. Se algum cenário ainda falhar, pare o rollout e aponte exatamente em qual fase o bloqueador precisa ser retomado.

## 15. Fase 11 - Rollout, runbook, alertas e aceite final

### Contexto da fase

Objetivo: colocar a correção em produção com ordem, rollback e operação repetível.

Critério de conclusão: produção atualizada, validada e com runbook claro.

Critério de rollback: executar rollback por issue e por onda de rollout, sem improvisar reboot e sem perder evidências.

### Prompts executáveis

1. Você é o agente responsável por montar a ordem final de rollout. Use as issues priorizadas deste documento para propor ondas de entrega pequenas e seguras. A ordem mínima recomendada é: `P0`, `P0A`, `P1`, `P2`, `P3`, `P4`, `P5`, `P6`, `P7`, `P8`, `P9`, `P10`. Para cada onda, descreva objetivo, pré-requisitos, métricas que devem ficar verdes e critério de abortar ou reverter.

2. Você é o agente responsável por escrever o runbook operacional final. O runbook precisa responder objetivamente: como verificar saúde do host, da API, do worker de Forms, do Nginx, do banco e do dashboard Transport; quando reiniciar apenas o worker; quando reiniciar a API; quando coletar evidências antes de qualquer reboot; como validar se o edge está em drift; e onde consultar métricas e logs introduzidos nas fases anteriores.

3. Você é o agente responsável por definir alertas e thresholds finais. Transforme os sinais criados nas fases anteriores em uma lista operacional de alertas obrigatórios, com severidade, janela, threshold e ação esperada. Inclua, no mínimo, `5xx` por rota crítica, backlog da fila do Forms, `unhealthy` do app, latência alta sustentada, CPU alta sustentada, memória alta sustentada e crescimento de conexões de banco.

4. Você é o agente responsável por emitir o aceite final técnico. Antes de declarar o problema resolvido, produza um documento curto com: o que mudou, quais evidências sustentam a resolução, quais riscos residuais permanecem, qual foi o ganho do upgrade do droplet, por que a IA de transporte continuou desabilitada ou em gate, e qual seria o gatilho técnico para reabrir este programa.

## 16. Regra de uso desta checklist por outro agente

1. Execute as fases na ordem definida, salvo bloqueio técnico documentado.
2. Não pule a Fase 0 nem a Fase 1.
3. Não habilite multiworker sem tratar o realtime cross-worker.
4. Não habilite a IA de transporte em produção antes da Fase 8 e da Fase 10.
5. Não trate o upgrade do droplet como resolução da causa raiz.
6. Não use reboot do host como primeiro passo de mitigação sem coletar as evidências mínimas desta checklist.
7. A cada fase, produza diff, validação e critério de rollback no próprio relatório da fase.

## 17. Resultado esperado ao final desta checklist

1. A API deixa de compartilhar blast radius com o processamento pesado do Forms.
2. O runtime HTTP fica apto a burst legítimo com observabilidade e auto-recuperação melhores.
3. A SPA de check deixa de gerar tempestade desnecessária de requests.
4. O dashboard Transport fica endurecido contra polling, refresh redundante e riscos futuros da IA.
5. O banco, o edge e o deploy ficam alinhados com o uso real e com o repo.
6. O time ganha runbook, alertas e harness de reprodução para não depender de reboot e intuição.
