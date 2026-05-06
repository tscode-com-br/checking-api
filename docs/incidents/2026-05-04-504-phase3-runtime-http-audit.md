# Auditoria do runtime HTTP e proposta de runtime final - Fase 3 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado como auditoria e proposta tecnica; sem implementacao ainda nesta etapa.
- Objetivo desta etapa: responder, com base no runtime versionado e no baseline do incidente, quantos workers existem hoje, qual servidor ASGI/WSGI e o mais apropriado, como tratar keepalive e timeouts, e quantos processos HTTP devem existir no baseline de `2 GB / 2 vCPU`.
- Escopo usado nesta leitura: `Dockerfile`, `deploy/docker/Dockerfile.api`, `docker-compose.yml`, `docker-compose.api.yml`, `sistema/app/main.py`, `sistema/app/services/admin_updates.py`, `deploy/nginx/checking-edge-routes.conf`, `docs/incidents/2026-05-04-504-phase0-baseline.md` e o workflow `.github/workflows/deploy-oceandrive-api-only.yml`.

## 2. Resposta objetiva

### 2.1 Quantos workers existem hoje

- O runtime HTTP versionado hoje sobe com um unico processo `uvicorn`.
- Isso aparece tanto no `Dockerfile` raiz quanto em `deploy/docker/Dockerfile.api`, ambos com `alembic upgrade head && uvicorn sistema.app.main:app --host 0.0.0.0 --port 8000`.
- Nao existe process manager versionado para o HTTP, nem contagem explicita de workers, nem politica de reciclagem de processos.
- O baseline consolidado do incidente registra que o upstream observado pelo Nginx foi `127.0.0.1:8000`, o que e compativel com um unico processo HTTP exposto por tras do proxy.

Conclusao objetiva:

- hoje o backend opera, no que esta versionado, com `1` worker HTTP efetivo.

### 2.2 Qual servidor ASGI/WSGI e o mais apropriado

Servidor recomendado:

- `gunicorn` como process manager, usando worker ASGI do Uvicorn para executar `sistema.app.main:app`.

Justificativa:

1. A aplicacao e FastAPI/ASGI; portanto a classe correta continua sendo ASGI, nao WSGI.
2. `sistema/app/main.py` expõe rotas long-lived com `StreamingResponse`, incluindo `/api/admin/stream`, `/api/transport/stream` e `/api/web/transport/stream`, entao um server WSGI seria um encaixe tecnicamente errado para o comportamento atual.
3. O Uvicorn puro funciona para desenvolvimento e runtime simples, mas nao entrega sozinho o mesmo nivel de supervisao de processos, timeouts de worker, restart gracioso e reciclagem controlada que a producao precisa.
4. `gunicorn` com workers Uvicorn e a menor mudanca correta porque preserva o app ASGI atual e adiciona exatamente as alavancas operacionais que faltam.

Conclusao objetiva:

- o servidor de producao mais apropriado aqui e `gunicorn` gerenciando workers ASGI do Uvicorn; nao ha ganho tecnico em migrar para WSGI.

### 2.3 Como tratar keepalive

Decisao proposta:

- manter keepalive curto no servidor HTTP da aplicacao, em `5s`.

Justificativa:

1. O edge Nginx ja faz a terminacao publica e deve continuar sendo o ponto principal de persistencia de conexao.
2. Keepalive alto no processo Python so aumenta retencao de conexoes ociosas e disputa recursos em um host pequeno.
3. As conexoes realmente longas do sistema atual sao SSE, e elas devem ser tratadas como stream da aplicacao + `proxy_read_timeout` adequado no Nginx, nao como keepalive longo do gunicorn.

Conclusao objetiva:

- `keep-alive` do processo HTTP: `5s`.
- timeout longo de SSE continua sendo responsabilidade do Nginx por rota, nao do keepalive do app server.

### 2.4 Como tratar timeouts

Decisao proposta:

- `timeout` do gunicorn: `90s`.
- `graceful-timeout` do gunicorn: `30s`.

Justificativa:

1. As rotas quentes medidas ate aqui ficam muito abaixo disso; portanto `90s` nao mascara regressao e ainda mata worker realmente travado.
2. O incidente real foi de degradacao sustentada, nao de requests legitimas de dezenas de segundos; o timeout precisa proteger contra travamento, nao acomodar silenciosamente o problema.
3. O `graceful-timeout` de `30s` da tempo para drenagem ou shutdown limpo sem prolongar demais a troca de processo.
4. SSE nao deve ser modelado por timeout de request do app server; o que precisa sobreviver e o loop do worker, e nao um timeout inflado para todos os caminhos.

Conclusao objetiva:

- `timeout=90` e `graceful-timeout=30` sao o baseline recomendado para este host.

### 2.5 Quantos processos devem existir para `2 GB / 2 vCPU`

Decisao proposta:

- alvo final do runtime HTTP: `2` workers HTTP.
- nao exceder `2` workers nesse baseline de host.

Justificativa:

1. O host de `2 GB / 2 vCPU` continua pequeno para rodar simultaneamente Nginx, Postgres, API HTTP e worker separado do Forms.
2. Com dois vCPUs, `2` workers entrega concorrencia real sem oversubscription agressiva do CPU.
3. Subir para `3` ou mais workers neste host aumenta pressao de memoria, conexoes de banco e disputa de CPU sem base de capacidade ainda validada.
4. O worker de Forms ja foi separado; logo o budget do container HTTP pode focar em duas replicas de processo Python, nao em absorver Playwright/Chromium no mesmo processo.

Conclusao objetiva:

- para `2 GB / 2 vCPU`, a meta final correta e `2` workers HTTP.

## 3. Restricao obrigatoria antes de habilitar multiworker

Esta auditoria encontrou um gate explicito que impede autorizar `workers > 1` imediatamente em producao.

Fato tecnico observado:

- `sistema/app/services/admin_updates.py` define `admin_updates_broker` e `transport_updates_broker` como singletons em memoria do processo.
- `sistema/app/routers/admin.py`, `sistema/app/routers/transport.py` e `sistema/app/routers/web_check.py` usam esses brokers para SSE.

Implicacao:

- com mais de um worker HTTP, cada processo teria seu proprio broker local;
- um evento publicado em um worker nao chegaria automaticamente aos assinantes conectados em outro worker;
- isso quebra coerencia de refresh do admin, do transport e do stream web de transporte.

Conclusao obrigatoria:

- o runtime final desejado e `gunicorn` com `2` workers;
- o rollout imediato seguro, antes do prompt seguinte da Fase 3, ainda deve permanecer em `1` worker enquanto o barramento cross-worker nao for implementado e validado.

## 4. Menor mudanca correta para producao

### 4.1 Etapa segura imediata

Trocar o processo HTTP de `uvicorn` puro para `gunicorn` com worker Uvicorn, mas manter:

- `APP_WORKERS=1`

Comando proposto:

```sh
gunicorn sistema.app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers ${APP_WORKERS:-1} \
  --bind 0.0.0.0:8000 \
  --keep-alive ${APP_KEEPALIVE_SECONDS:-5} \
  --timeout ${APP_TIMEOUT_SECONDS:-90} \
  --graceful-timeout ${APP_GRACEFUL_TIMEOUT_SECONDS:-30} \
  --max-requests ${APP_MAX_REQUESTS:-1000} \
  --max-requests-jitter ${APP_MAX_REQUESTS_JITTER:-100}
```

Ganho desta etapa:

- processo supervisionado;
- limites claros de timeout;
- reciclagem defensiva de worker;
- mesma semantica funcional atual de single worker, sem quebrar SSE cross-worker antes da hora.

### 4.2 Etapa final apos o barramento cross-worker

Depois da entrega e validacao do prompt seguinte da Fase 3, elevar para:

- `APP_WORKERS=2`

Sem trocar novamente de servidor HTTP.

## 5. Observacoes de topologia real de producao

Esta execucao nao teve acesso SSH ao host, entao o estado real atual nao pode ser reafirmado como fato novo. O que esta consolidado no programa e:

1. o incidente observado passou por `127.0.0.1:8000`;
2. o repo tambem versiona topologia separada com API em `18080` e websites em `18081-18083`;
3. o workflow `.github/workflows/deploy-oceandrive-api-only.yml` valida a API separada em `http://127.0.0.1:18080/api/health`;
4. a reconciliacao final do edge continua dependente da Fase 7.

Implicacao pratica:

- a decisao do servidor HTTP independe de o edge ja estar apontando hoje para `8000` ou `18080`;
- a mesma proposta vale dentro do container da API;
- o que muda entre `8000` e `18080` e a topologia de exposicao e proxy, nao o runtime ASGI recomendado.

## 6. Pontos materialmente relacionados, mas fora da menor mudanca desta etapa

1. O startup ainda encadeia `alembic upgrade head` antes do processo HTTP. Isso continua sendo um risco operacional real, mas a separacao da migracao deve entrar como mudanca dedicada da Fase 9 para nao misturar superficies nesta entrega.
2. O healthcheck atual continua chamando `http://127.0.0.1:8000/api/health` dentro do container. Isso continua valido com gunicorn, desde que a porta interna permaneça `8000`.
3. O pool de banco ainda precisa ser recalibrado na Fase 6 levando em conta o alvo final de `2` workers HTTP.

## 7. Recomendacao final desta auditoria

Recomendacao objetiva:

1. padronizar o runtime HTTP em `gunicorn` + worker ASGI do Uvicorn;
2. introduzir desde ja os controles de `keep-alive=5`, `timeout=90`, `graceful-timeout=30` e reciclagem por `max-requests`;
3. subir primeiro com `1` worker em producao enquanto o broker cross-worker nao existir;
4. apos validar o barramento cross-worker da Fase 3, promover para `2` workers HTTP no baseline `2 GB / 2 vCPU`;
5. nao autorizar `3+` workers neste host antes de medir CPU, memoria, pool de banco e coerencia de SSE sob carga.

Conclusao resumida:

- hoje: `1` worker HTTP efetivo em `uvicorn` puro;
- servidor correto: `gunicorn` com workers ASGI do Uvicorn;
- keepalive: `5s`;
- timeouts: `90s` + `30s` graceful;
- alvo final para `2 GB / 2 vCPU`: `2` workers HTTP;
- gate de rollout: manter `1` worker ate o barramento de realtime cross-worker ser entregue e validado.