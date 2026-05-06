# Mapeamento do fluxo atual do Forms - Fase 2 - incidente 504 de 2026-05-04

## 1. Status desta auditoria

- Resultado atual: aprovado como mapeamento tecnico de leitura.
- Escopo desta etapa: documentar o desenho atual e o desenho alvo do fluxo do Forms, sem alterar codigo de runtime.
- Objetivo operacional: deixar explicito onde a API persiste a fila, onde o worker nasce hoje, quais recursos pesados ele usa e por que isso amplia blast radius.

## 2. Resumo executivo

Hoje, a API HTTP nao envia o Microsoft Forms diretamente dentro das rotas mais importantes. Ela primeiro persiste um item em `forms_submissions` e responde rapido ao cliente. O problema estrutural nao esta na persistencia da fila, e sim no fato de o consumo dessa fila ainda acontecer dentro do mesmo processo FastAPI e do mesmo container que atende HTTP.

O worker atual e um `threading.Thread` daemon iniciado no `lifespan` do app. Esse worker instancia `FormsWorker`, abre Playwright com Chromium headless e executa navegacao, espera de elementos, clique e submissao do formulario. Como Chromium e Playwright vivem na mesma imagem e no mesmo runtime do HTTP, backlog ou falha do worker ainda concorrem por CPU, memoria, I/O e ciclo de vida com `/api/health`, login, web check, admin e mobile.

O desenho alvo desta fase e manter a fila persistida, mas mover o consumo para um processo ou servico separado do app HTTP, com bootstrap, health, restart, logs e capacidade de escalonamento independentes.

## 3. Desenho atual ponta a ponta

## 3.1 Pontos de entrada que podem enfileirar Forms

### A. RFID / ESP32

- Rota: `POST /api/scan` em `sistema/app/routers/device.py`.
- Fluxo atual:
  - valida a shared key do dispositivo;
  - registra o evento recebido em `check_events`;
  - carrega o usuario por RFID;
  - atualiza o estado local do usuario;
  - decide se precisa ou nao gerar novo envio ao Forms com `should_enqueue_forms_for_action(...)`;
  - quando precisa, persiste o item da fila via `enqueue_forms_submission(...)`;
  - grava `user_sync_events` e evento `queued`;
  - responde ao dispositivo sem esperar o envio ao Microsoft Forms terminar.

### B. Mobile app - submit direto

- Rota: `POST /api/mobile/events/submit` em `sistema/app/routers/mobile.py`.
- Fluxo atual:
  - valida a shared key do app mobile;
  - carrega ou cria o usuario;
  - normaliza horario e projeto;
  - atualiza estado do usuario;
  - decide se precisa ou nao gerar novo envio ao Forms;
  - quando precisa, chama `enqueue_forms_submission(...)` diretamente;
  - grava `user_sync_events` e evento `queued`;
  - responde sem esperar o envio ao Microsoft Forms terminar.

### C. Mobile app - Forms submit com `informe`

- Rota: `POST /api/mobile/events/forms-submit` em `sistema/app/routers/mobile.py`.
- Fluxo atual:
  - reutiliza o helper `submit_forms_event(...)` de `sistema/app/services/forms_submit.py`;
  - o helper converte `informe` em `ontime`;
  - atualiza estado do usuario;
  - quando precisa, persiste a fila via `enqueue_forms_submission(...)`;
  - grava `user_sync_events` e evento `queued`;
  - responde sem esperar o Forms.

### D. Web check

- Rota: `POST /api/web/check` em `sistema/app/routers/web_check.py`.
- Fluxo atual:
  - valida sessao web do usuario;
  - reutiliza o mesmo helper `submit_forms_event(...)`;
  - atualiza estado do usuario;
  - quando precisa, persiste a fila via `enqueue_forms_submission(...)`;
  - grava `user_sync_events` e evento `queued`;
  - responde sem esperar o Forms.

## 3.2 Onde a API grava o item de fila

- Ponto unico de persistencia: `enqueue_forms_submission(...)` em `sistema/app/services/forms_queue.py`.
- Tabela persistida: `forms_submissions` em `sistema/app/models.py`.
- Campos principais persistidos hoje:
  - `request_id`
  - `rfid`
  - `action`
  - `chave`
  - `projeto`
  - `device_id`
  - `local`
  - `ontime`
  - `status`
  - `retry_count`
  - `last_error`
  - `created_at`
  - `updated_at`
  - `processed_at`
- Estado inicial do item: `status="pending"`.
- Garantia de idempotencia da fila: `UniqueConstraint` por `request_id`.

## 3.3 Onde o worker e iniciado hoje

- Objeto global: `forms_submission_worker = FormsSubmissionWorker()` em `sistema/app/services/forms_queue.py`.
- Bootstrap atual: `forms_submission_worker.start()` dentro do `lifespan` em `sistema/app/main.py`, condicionado a `settings.forms_queue_enabled`.
- Encerramento atual: `forms_submission_worker.stop()` no `finally` do mesmo `lifespan`.
- Implicacao direta: o worker nasce e morre junto com o processo FastAPI.

## 3.4 Como o worker consome a fila hoje

- `FormsSubmissionWorker` cria um thread daemon local ao processo HTTP.
- Loop atual:
  - chama `process_forms_submission_queue_once(max_items=10)`;
  - se nao processou nada, espera `0.25s`;
  - se processou, volta imediatamente ao loop.
- Reserva do proximo item:
  - `_reserve_next_submission_id()` seleciona o primeiro `pending` por `id`;
  - muda o item para `processing`;
  - faz `commit`;
  - devolve o `submission_id`.
- Processamento do item:
  - `_process_submission(...)` recarrega o item por `id`;
  - instancia um novo `FormsWorker`;
  - executa `submit_with_retries(...)`;
  - grava o resultado final como `success` ou `failed` em `forms_submissions`;
  - grava trilha de auditoria em `check_events`;
  - emite telemetria estruturada de fila.

## 4. Recursos pesados usados pelo worker atual

## 4.1 No codigo

- `sistema/app/services/forms_worker.py` usa `playwright.sync_api`.
- Para cada item processado, o worker:
  - abre Playwright com `sync_playwright()`;
  - executa `p.chromium.launch(headless=True)`;
  - cria `browser.new_page()`;
  - navega ate `settings.forms_url`;
  - espera seletores XPath;
  - preenche campos;
  - clica botoes de check-in, check-out e projeto;
  - aguarda confirmacoes e tela de sucesso;
  - fecha o browser.

## 4.2 Na imagem de container

- O `Dockerfile` instala `playwright` e `chromium` na mesma imagem usada pelo servico `app`.
- O mesmo container que sobe `uvicorn` e responde HTTP carrega dependencias de browser headless e sistema operacional para Playwright.

## 4.3 Nos recursos operacionais

- CPU para lancar e operar Chromium.
- Memoria para processo de browser, pagina e DOM.
- I/O de rede para navegar ate o Microsoft Forms.
- Tempo de espera prolongado em timeout e retentativa.
- Ciclo de vida adicional dentro do mesmo container do runtime HTTP.

## 5. Por que isso amplia blast radius hoje

## 5.1 Mesmo processo HTTP, mesmo ciclo de vida

- O worker atual nao e um servico separado; ele e um thread daemon do mesmo processo FastAPI.
- Se o processo HTTP degradar ou reiniciar, o worker degrada ou reinicia junto.
- Se o worker travar, consumir CPU ou ficar preso em timeout, a competicao acontece no mesmo processo da API.

## 5.2 Mesmo container e mesmo cgroup

- O `docker-compose.yml` hoje tem apenas `app` e `db`.
- O servico `app` concentra:
  - Uvicorn;
  - import do backend;
  - thread do worker do Forms;
  - dependencias de Playwright/Chromium.
- Isso faz o HTTP compartilhar CPU, memoria e disco com o processamento pesado do Forms.

## 5.3 Health atual observa HTTP, nao isolacao do worker

- O healthcheck atual do `app` consulta `http://127.0.0.1:8000/api/health`.
- Esse check prova apenas que o endpoint de health respondeu; ele nao separa claramente saude do HTTP da saude do worker.
- Portanto, pode haver fila crescendo, worker falhando ou Chromium pressionando recursos enquanto o health do app ainda parece util por algum tempo.

## 5.4 Backlog e falha do Forms ainda pressionam rotas quentes

- Mesmo com fila persistida, o consumo continua no mesmo runtime que precisa atender:
  - `/api/health`
  - `/api/web/check/state`
  - `/api/mobile/state`
  - `/api/admin/checkin`
  - `/api/admin/checkout`
  - `/api/admin/projects`
- Em burst, o sistema continua vulneravel a tempo de resposta pior, `5xx` e `upstream timed out` se o worker disputar recurso suficiente com o app.

## 5.5 Risco adicional para futuros passos de concorrencia

- Como o worker hoje nasce dentro do `lifespan` do app, qualquer estrategia futura de multiworker HTTP faria cada processo subir seu proprio worker local, a menos que o wiring mudasse antes.
- A reserva atual da fila foi desenhada para o consumidor unico atual. Ela nao foi documentada como semantica de consumo distribuido entre varios processos HTTP concorrentes.

## 6. Desenho alvo desta fase

## 6.1 Responsabilidade do app HTTP

O app HTTP deve ficar restrito a:

- validar a request;
- atualizar estado de dominio e usuario;
- gravar `user_sync_events`, `check_events` e `forms_submissions`;
- dar `commit`;
- responder rapido ao cliente.

O app HTTP nao deve:

- iniciar `forms_submission_worker` no `lifespan`;
- importar ou executar Playwright como parte do caminho operacional normal do HTTP;
- depender do worker para responder rotas criticas.

## 6.2 Responsabilidade do worker separado

O worker separado deve:

- rodar como processo ou servico proprio;
- ser o unico responsavel por consumir `forms_submissions`;
- carregar Playwright e Chromium;
- mover itens entre `pending`, `processing`, `success` e `failed`;
- manter logs estruturados, health proprio e restart policy propria;
- falhar sem derrubar o HTTP.

## 6.3 Topologia alvo minima

Topologia minima recomendada para a proxima etapa:

- `app`: valida request, persiste fila, responde HTTP.
- `forms-worker`: consome `forms_submissions` e executa Playwright/Chromium.
- `db`: continua sendo a fonte de verdade da fila persistida.

Opcao preferencial de empacotamento:

- imagem HTTP sem dependencias de Chromium;
- imagem do worker com Playwright/Chromium;
- ou, se a equipe quiser otimizar build depois, base comum com entrypoints distintos, desde que o runtime HTTP nao precise carregar o browser.

## 6.4 Invariantes que o desenho alvo precisa preservar

- os endpoints atuais continuam aceitando o evento e respondendo rapido;
- a fila continua persistida em `forms_submissions`;
- idempotencia por `request_id` continua valendo;
- falha do worker nao perde o item persistido;
- backlog do worker nao bloqueia `/api/health`, login, web check, admin e mobile.

## 7. Conclusao objetiva

O sistema ja tem um desacoplamento parcial importante: a API persiste o trabalho em `forms_submissions` e responde antes do envio ao Microsoft Forms terminar.

O acoplamento que ainda falta remover e o acoplamento de execucao. Hoje, quem consome a fila continua dentro do mesmo processo e do mesmo container do HTTP, com Playwright e Chromium instalados na mesma imagem do app. Esse desenho mantem blast radius compartilhado entre fila pesada e rotas quentes.

O proximo passo correto e mover o consumo do Forms para um processo ou servico separado, mantendo a fila persistida atual como contrato. Isso isola CPU, memoria, lifecycle, restart e health do Forms sem quebrar os endpoints que ja respondem rapido hoje.

## 8. Dependencia direta para o proximo prompt

Para implementar a proxima etapa com a menor mudanca correta, o proximo prompt deve:

- remover o start/stop do worker do `lifespan` do app;
- criar entrypoint ou modulo dedicado do worker;
- adicionar servico separado no compose;
- garantir que apenas o worker carregue Playwright/Chromium;
- preservar `forms_submissions` como fila persistida e contrato atual dos endpoints.