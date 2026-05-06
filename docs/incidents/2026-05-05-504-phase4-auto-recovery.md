# Auto-recuperacao operacional limitada - Fase 4 - incidente 504 de 2026-05-05

## 1. Status desta execucao

- Resultado atual: aprovado em escopo de repo.
- Objetivo desta etapa: definir uma politica operacional de remediacao para estados `unhealthy` sustentados sem voltar a usar reboot cego de host e sem reaproximar worker e API.
- Implementacao entregue no repo: `deploy/maintenance/checkcheck_auto_recovery.py`.

## 2. Problema atacado

O stack atual ja tem:

1. `restart: unless-stopped` no Compose;
2. healthcheck binario da API HTTP baseado em `GET /api/health/ready`;
3. healthcheck proprio do `forms-worker` via `python -m sistema.app.forms_worker_healthcheck`;
4. supervisor interno do worker do Forms com backoff e restart do thread.

Mas isso ainda deixa uma lacuna operacional importante:

- Docker Compose nao reinicia um container apenas porque ele ficou `unhealthy`;
- logo, sem um remediador externo, a stack continua dependente de intervencao manual mesmo quando o problema e claramente local a um unico componente.

## 3. Decisao operacional adotada

### 3.1 O que pode ser reiniciado automaticamente

So dois alvos entram em auto-recuperacao limitada:

1. `forms-worker`
2. `app` ou `api`, dependendo do compose ativo

### 3.2 O que nao entra em restart automatico

Nao entra em restart automatico por esta politica:

1. `db`
2. host inteiro
3. Nginx
4. reboot amplo de stack inteira

Se o banco estiver `unhealthy`, a politica para imediatamente em modo coleta de evidencias.

### 3.3 Principio central

Reiniciar automaticamente so faz sentido quando o problema esta suficientemente isolado para um componente.

Traducao pratica:

1. falha sustentada e isolada do worker do Forms -> pode reiniciar apenas o worker;
2. falha sustentada da API com banco saudavel -> pode reiniciar apenas a API;
3. falha do banco, `OOMKilled`, ou falhas simultaneas entre API e worker -> parar para coleta de evidencias antes de qualquer reboot maior.

## 4. Politica concreta de decisao

## 4.1 Quando reiniciar apenas o worker do Forms

O remediador reinicia apenas `forms-worker` quando todos os pontos abaixo forem verdadeiros:

1. o servico `forms-worker` existe no compose ativo;
2. o worker esta `unhealthy` de forma sustentada;
3. a API continua `ready` localmente;
4. o banco continua `healthy`;
5. o worker nao entrou em loop de restart de container;
6. o budget de restarts automaticos do worker ainda nao foi gasto.

Thresholds implementados no script:

1. `3` sondagens consecutivas unhealthy para agir;
2. no maximo `2` restarts automaticos do worker por janela de `60` minutos;
3. se o `RestartCount` do container do worker ja estiver em `>= 2`, o script deixa de reiniciar automaticamente e entra em modo evidencia.

## 4.2 Quando reiniciar apenas a API HTTP

O remediador reinicia apenas `app` ou `api` quando todos os pontos abaixo forem verdadeiros:

1. a readiness local da API falhou de forma sustentada ou o container HTTP ficou `unhealthy`;
2. o banco continua `healthy`;
3. o worker do Forms nao esta falhando ao mesmo tempo;
4. a API nao entrou em loop de restart de container;
5. o budget de restarts automaticos da API ainda nao foi gasto.

Thresholds implementados no script:

1. `3` sondagens consecutivas unhealthy para agir;
2. no maximo `1` restart automatico da API por janela de `90` minutos;
3. se o `RestartCount` do container HTTP ja estiver em `>= 2`, o script deixa de reiniciar automaticamente e entra em modo evidencia.

## 4.3 Quando parar para coleta de evidencias antes de qualquer reboot maior

O remediador para em modo `collect_evidence` quando ocorre qualquer um destes casos:

1. banco `unhealthy` ou indisponivel;
2. `OOMKilled` da API;
3. `OOMKilled` do worker do Forms;
4. API e worker unhealthy ao mesmo tempo;
5. budget de restart automatico esgotado para o componente afetado;
6. suspeita de loop de restart do proprio container antes mesmo do remediador agir;
7. falha do comando de restart automatico.

Nesses casos, a etapa correta deixa de ser restart cego e passa a ser:

1. congelar evidencias;
2. abrir incidente operacional;
3. decidir manualmente o proximo passo com base em banco, logs e estado do edge.

## 5. Implementacao entregue

## 5.1 Utilitario one-shot versionado

Arquivo entregue:

- `deploy/maintenance/checkcheck_auto_recovery.py`

Esse utilitario foi desenhado para rodar como execucao periodica no host, por exemplo via timer ou cron, e faz:

1. descobre `stack_dir` e compose quando possivel;
2. inspeciona `app` ou `api`, `db` e `forms-worker`;
3. consulta localmente `GET /api/health/ready` e `GET /api/health` pela porta publicada do container HTTP;
4. mantem estado persistido de contadores consecutivos e janelas de restart;
5. decide entre:
   - `noop`
   - `restart_forms_worker`
   - `restart_api`
   - `collect_evidence`
6. coleta evidencias antes de qualquer restart automatico;
7. registra state file para impedir loops cegos.

## 5.2 Arquivos gerados pelo remediador

Por padrao, o remediador grava:

1. state file por compose em caminho derivado do repo, por exemplo `.docker-compose.auto_recovery_state.json`;
2. diretorio de evidencias em `auto_recovery_evidence/<compose>/...`;
3. evidencias com:
   - decisao serializada;
   - `docker compose ps`;
   - `docker inspect` dos servicos relevantes;
   - `docker logs --tail` dos servicos relevantes;
   - resultado da probe local de `/api/health/ready`;
   - resultado da probe local de `/api/health`;
   - tentativa de healthcheck do worker quando o servico existe.

## 5.3 Recomendacao de acionamento no host

O repo nao ativa sozinho um timer no host porque esta sessao nao tem acesso ao droplet nem conhece caminho final de checkout da stack.

Recomendacao operacional para producao:

1. executar o utilitario a cada `60` segundos via timer ou cron;
2. usar sempre o compose real da stack ativa;
3. manter o state file em caminho persistente no host;
4. manter o evidence root em caminho com rotacao monitorada.

Exemplo de execucao manual segura:

```bash
python3 deploy/maintenance/checkcheck_auto_recovery.py \
  --stack-dir /opt/checkcheck \
  --compose-file docker-compose.yml
```

Exemplo para stack API-only:

```bash
python3 deploy/maintenance/checkcheck_auto_recovery.py \
  --stack-dir /opt/checkcheck \
  --compose-file docker-compose.api.yml
```

## 6. O que esta deliberadamente fora da auto-recuperacao

Esta etapa nao automatiza:

1. restart de banco;
2. reload ou restart de Nginx;
3. reboot de host;
4. restart total da stack;
5. decisao baseada em `degraded` de `/api/health` quando a readiness continua `ok`.

Esses caminhos ficaram fora porque o custo de um falso positivo e alto demais para o tipo de stack atual.

## 7. Validacao executada

### 7.1 Checagem estatica dos arquivos novos

- `get_errors` retornou sem erros para:
  - `deploy/maintenance/checkcheck_auto_recovery.py`
  - `tests/test_phase4_auto_recovery.py`

### 7.2 Testes focados da matriz de decisao

Comando executado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_phase4_auto_recovery.py -q
```

Resultado:

- `5 passed`

Cobertura objetiva:

1. reinicia apenas o worker quando o worker falha isoladamente e a API continua pronta;
2. reinicia apenas a API quando a readiness falha e o banco continua saudavel;
3. bloqueia restart automatico quando o banco esta unhealthy;
4. bloqueia restart automatico quando o worker esgotou o budget;
5. bloqueia restart automatico quando API e worker falham juntos.

## 8. Limitacoes declaradas

1. Esta sessao nao tem acesso ao host DigitalOcean para instalar timer, cron ou unit de systemd em producao.
2. O remediador foi implementado como utilitario one-shot versionado; a ativacao automatica no host ainda e etapa de rollout operacional.
3. A decisao atual usa sinais locais de Docker e health HTTP; ela nao tenta inferir causas mais profundas do banco, do edge ou da rede publica.

## 9. Resultado tecnico

- aprovado.
- o repo agora tem politica de auto-recuperacao clara e implementacao limitada para o que hoje pode ser reiniciado com seguranca;
- a politica evita confundir `degraded` com indisponibilidade real;
- a politica tambem evita loops cegos porque exige falha sustentada, impõe budgets de restart e para automaticamente quando o problema parece maior que um componente isolado.

## 10. Rollback

Rollback desta etapa, se desejado:

1. remover `deploy/maintenance/checkcheck_auto_recovery.py`;
2. remover `tests/test_phase4_auto_recovery.py`;
3. remover `docs/incidents/2026-05-05-504-phase4-auto-recovery.md`.

Nenhum host, container de producao, banco ou edge foi alterado nesta sessao.

## 11. Proximo passo recomendado

O proximo passo natural e ligar esse remediador ao host real na Fase 10 ou Fase 11:

1. instalar timer ou cron com caminho final da stack;
2. validar em homologacao que a evidencia e capturada antes do restart automatico;
3. incorporar essa politica no runbook final de operacao.