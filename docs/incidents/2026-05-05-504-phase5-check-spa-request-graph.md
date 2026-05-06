# Auditoria do grafo de requests da SPA de check - Fase 5 - incidente 504 de 2026-05-05

## 1. Status desta execucao

- Resultado atual: aprovado como auditoria de leitura.
- Objetivo desta etapa: mapear o grafo real de requests gerado por `sistema/app/static/check/app.js` antes de qualquer alteracao de reducao de burst.
- Escopo desta leitura: bootstrap, restauracao de sessao, verificacao de senha, `focus`, `pageshow`, `visibilitychange`, localizacao, submit e o ramo de Transporte que divide a mesma SPA.

## 2. Resposta objetiva

O burst principal da SPA de check nao nasce no submit manual isolado.

Ele nasce do encadeamento abaixo, que hoje pode ocorrer em bootstrap autenticado e em gatilhos de lifecycle:

1. `GET /api/web/auth/status`
2. `POST /api/web/auth/login`
3. `GET /api/web/projects`
4. `GET /api/web/check/locations`
5. `GET /api/web/check/state`
6. `POST /api/web/check/location`
7. `GET /api/web/check/state`
8. `POST /api/web/check`

Quando a tela de Transporte esta aberta, a mesma pagina ainda adiciona:

1. `GET /api/web/transport/stream` como SSE;
2. `GET /api/web/transport/state` na abertura, nos gatilhos de lifecycle e em polling de `10s` enquanto houver solicitacoes ativas.

## 3. Inventario de endpoints realmente usados por `app.js`

### 3.1 Autenticacao e sessao

- `GET /api/web/auth/status`
- `POST /api/web/auth/login`
- `POST /api/web/auth/register-password`
- `POST /api/web/auth/register-user`
- `POST /api/web/auth/change-password`
- `POST /api/web/auth/logout`

### 3.2 Check e localizacao

- `GET /api/web/projects`
- `PUT /api/web/project`
- `GET /api/web/check/locations`
- `POST /api/web/check/location`
- `GET /api/web/check/state`
- `POST /api/web/check`

### 3.3 Transporte dentro da mesma SPA

- `GET /api/web/transport/state`
- `GET /api/web/transport/stream`
- `POST /api/web/transport/address`
- `POST /api/web/transport/request`
- `POST /api/web/transport/cancel`
- `POST /api/web/transport/acknowledge`

## 4. Matriz `evento -> funcao -> endpoint -> frequencia esperada -> risco de burst`

| Evento | Funcao | Endpoint | Frequencia esperada | Risco de burst |
| --- | --- | --- | --- | --- |
| Bootstrap frio da pagina, mesmo sem sessao restaurada | `loadProjectCatalog()` no final do IIFE | `GET /api/web/projects` | `1x` por page load | medio |
| Bootstrap com chave persistida | `logoutWebSession()` | `POST /api/web/auth/logout` | `1x` por page load com chave persistida | medio |
| Bootstrap com chave persistida | `refreshAuthenticationStatus()` -> `fetchAuthenticationStatus()` | `GET /api/web/auth/status?chave=...` | `1x` por page load com chave persistida | medio |
| Bootstrap com senha persistida ou autofill valido | `schedulePasswordVerification()` -> `attemptPasswordLogin()` | `POST /api/web/auth/login` | `0..1x` apos `260ms` de debounce; pode repetir em focus/autofill | alto |
| Login bem-sucedido, alteracao de senha, cadastro de usuario ou restauracao de sessao que conclui login | `loadAuthenticatedApplication()` -> `loadProjectCatalog()` | `GET /api/web/projects` | `1x` por autenticacao bem-sucedida | medio |
| Login bem-sucedido, alteracao de senha, cadastro de usuario ou restauracao de sessao que conclui login | `loadAuthenticatedApplication()` -> `loadManualLocations()` | `GET /api/web/check/locations` | `1x` por autenticacao bem-sucedida | medio |
| Login bem-sucedido, alteracao de senha, cadastro de usuario ou restauracao de sessao que conclui login | `loadAuthenticatedApplication()` -> `runLifecycleUpdateSequence()` -> `refreshHistory()` | `GET /api/web/check/state?chave=...` | `1x` no startup autenticado | alto |
| Login bem-sucedido, alteracao de senha, cadastro de usuario ou restauracao de sessao que conclui login | `loadAuthenticatedApplication()` -> `runLifecycleUpdateSequence()` -> `updateLocationForLifecycleSequence()` -> `resolveCurrentLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `1x` no startup autenticado quando geolocalizacao pode ser consultada | alto |
| Startup autenticado com atividades automaticas habilitadas | `runLifecycleUpdateSequence()` -> `runAutomaticActivitiesIfNeeded()` -> `fetchWebState()` | `GET /api/web/check/state?chave=...` | `+1x` depois da localizacao em cada startup que entra no ramo automatico | alto |
| Startup autenticado com atividades automaticas habilitadas e regra satisfeita | `runLifecycleUpdateSequence()` -> `runAutomaticActivitiesIfNeeded()` -> `submitAutomaticActivity()` | `POST /api/web/check` | `0..1x` por startup autenticado | alto |
| Digitar ou colar chave ate um valor valido de 4 caracteres | listener de `chaveInput` -> `refreshAuthenticationStatus()` -> `fetchAuthenticationStatus()` | `GET /api/web/auth/status?chave=...` | `1x` por novo valor valido de 4 caracteres | medio |
| Digitar senha com usuario que ja tem senha | listener de `passwordInput` -> `syncPasswordInputState()` -> `schedulePasswordVerification()` -> `attemptPasswordLogin()` | `POST /api/web/auth/login` | uma tentativa por pausa de `260ms` enquanto a senha valida muda | alto |
| `change` no campo senha | listener de `passwordInput` -> `attemptPasswordLogin()` | `POST /api/web/auth/login` | `1x` por blur/change com senha valida | medio |
| `focus` no campo senha com autofill atrasado do navegador | listener de `passwordInput` -> `schedulePasswordAutofillSync()` -> `syncPasswordInputState()` -> `schedulePasswordVerification()` -> `attemptPasswordLogin()` | `POST /api/web/auth/login` | `0..1x` por cluster de focus/autofill | medio |
| Submit do dialogo de troca de senha | `submitPasswordChange()` | `POST /api/web/auth/change-password` ou `POST /api/web/auth/register-password` | `1x` por submit | medio |
| Submit do dialogo de troca de senha bem-sucedido | `submitPasswordChange()` -> `loadAuthenticatedApplication()` | `GET /api/web/projects`, `GET /api/web/check/locations`, `GET /api/web/check/state`, `POST /api/web/check/location`, `GET /api/web/check/state`, `POST /api/web/check` | cadeia completa apos sucesso; a ultima dupla depende de atividades automaticas | alto |
| Submit do cadastro de usuario | `submitUserSelfRegistration()` | `POST /api/web/auth/register-user` | `1x` por submit | medio |
| Submit do cadastro de usuario bem-sucedido | `submitUserSelfRegistration()` -> `loadAuthenticatedApplication()` | `GET /api/web/projects`, `GET /api/web/check/locations`, `GET /api/web/check/state`, `POST /api/web/check/location`, `GET /api/web/check/state`, `POST /api/web/check` | cadeia completa apos sucesso; a ultima dupla depende de atividades automaticas | alto |
| Atualizacao manual de localizacao pelo botao | `runManualLocationRefreshSequence()` -> `resolveCurrentLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `1x` por clique | medio |
| Atualizacao manual de localizacao com atividades automaticas habilitadas | `runManualLocationRefreshSequence()` -> `runAutomaticActivitiesIfNeeded()` -> `fetchWebState()` | `GET /api/web/check/state?chave=...` | `+1x` por clique quando entra no ramo automatico | medio |
| Atualizacao manual de localizacao com atividade automatica aplicavel | `runManualLocationRefreshSequence()` -> `runAutomaticActivitiesIfNeeded()` -> `submitAutomaticActivity()` | `POST /api/web/check` | `0..1x` por clique | medio |
| Habilitar atividades automaticas | `runAutomaticActivitiesEnableSequence()` -> `resolveCurrentLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `1x` por habilitacao | medio |
| Habilitar atividades automaticas | `runAutomaticActivitiesEnableSequence()` -> `runAutomaticActivitiesIfNeeded()` -> `fetchWebState()` | `GET /api/web/check/state?chave=...` | `1x` por habilitacao | medio |
| Habilitar atividades automaticas com evento automatico aplicavel | `runAutomaticActivitiesEnableSequence()` -> `submitAutomaticActivity()` | `POST /api/web/check` | `0..1x` por habilitacao | medio |
| Desabilitar atividades automaticas com GPS ja concedido | listener de `automaticActivitiesToggle` -> `runLifecycleUpdateSequence({ triggerSource: 'automatic_activities_disable' })` -> `refreshHistory()` | `GET /api/web/check/state?chave=...` | `1x` por desabilitacao | medio |
| Desabilitar atividades automaticas com GPS ja concedido | listener de `automaticActivitiesToggle` -> `runLifecycleUpdateSequence({ triggerSource: 'automatic_activities_disable' })` -> `updateLocationForLifecycleSequence()` -> `resolveCurrentLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `1x` por desabilitacao | medio |
| `visibilitychange` para `visible` | `runLifecycleUpdateSequence({ triggerSource: 'visibility' })` -> `refreshHistory()` | `GET /api/web/check/state?chave=...` | `1x` por evento aceito pela janela de cooldown de `1200ms` | alto |
| `visibilitychange` para `visible` | `runLifecycleUpdateSequence({ triggerSource: 'visibility' })` -> `updateLocationForLifecycleSequence()` -> `resolveCurrentLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `1x` por evento aceito | alto |
| `visibilitychange` para `visible` com atividades automaticas habilitadas | `runLifecycleUpdateSequence({ triggerSource: 'visibility' })` -> `runAutomaticActivitiesIfNeeded()` -> `fetchWebState()` | `GET /api/web/check/state?chave=...` | `+1x` por evento aceito quando o ramo automatico roda | alto |
| `visibilitychange` para `visible` com evento automatico aplicavel | `runLifecycleUpdateSequence({ triggerSource: 'visibility' })` -> `submitAutomaticActivity()` | `POST /api/web/check` | `0..1x` por evento aceito | alto |
| `focus` da janela | `runLifecycleUpdateSequence({ triggerSource: 'focus' })` -> `refreshHistory()` | `GET /api/web/check/state?chave=...` | `1x` por evento aceito pela janela de cooldown de `1200ms` | alto |
| `focus` da janela | `runLifecycleUpdateSequence({ triggerSource: 'focus' })` -> `updateLocationForLifecycleSequence()` -> `resolveCurrentLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `1x` por evento aceito | alto |
| `focus` da janela com atividades automaticas habilitadas | `runLifecycleUpdateSequence({ triggerSource: 'focus' })` -> `runAutomaticActivitiesIfNeeded()` -> `fetchWebState()` | `GET /api/web/check/state?chave=...` | `+1x` por evento aceito quando o ramo automatico roda | alto |
| `focus` da janela com evento automatico aplicavel | `runLifecycleUpdateSequence({ triggerSource: 'focus' })` -> `submitAutomaticActivity()` | `POST /api/web/check` | `0..1x` por evento aceito | alto |
| `pageshow` | `runLifecycleUpdateSequence({ triggerSource: 'pageshow' })` -> `refreshHistory()` | `GET /api/web/check/state?chave=...` | `1x` por evento aceito pela janela de cooldown de `1200ms` | alto |
| `pageshow` | `runLifecycleUpdateSequence({ triggerSource: 'pageshow' })` -> `updateLocationForLifecycleSequence()` -> `resolveCurrentLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `1x` por evento aceito | alto |
| `pageshow` com atividades automaticas habilitadas | `runLifecycleUpdateSequence({ triggerSource: 'pageshow' })` -> `runAutomaticActivitiesIfNeeded()` -> `fetchWebState()` | `GET /api/web/check/state?chave=...` | `+1x` por evento aceito quando o ramo automatico roda | alto |
| `pageshow` com evento automatico aplicavel | `runLifecycleUpdateSequence({ triggerSource: 'pageshow' })` -> `submitAutomaticActivity()` | `POST /api/web/check` | `0..1x` por evento aceito | alto |
| Submit principal do formulario | handler de `form.addEventListener('submit', ...)` -> `ensureLocationReadyForSubmit()` -> `captureAndResolveLocation()` -> `matchCurrentPosition()` | `POST /api/web/check/location` | `0..1x` por submit; roda quando a permissao permite busca silenciosa e nao ha request pendente | medio |
| Submit principal do formulario | handler de `form.addEventListener('submit', ...)` | `POST /api/web/check` | `1x` por submit | medio |
| Abrir a tela de Transporte | `openTransportScreen()` -> `startTransportRealtimeUpdates()` | `GET /api/web/transport/stream?chave=...` | `1x` por abertura da tela; conexao longa SSE | medio |
| Abrir a tela de Transporte | `openTransportScreen()` -> `loadTransportState()` -> `fetchTransportStatePayload()` | `GET /api/web/transport/state?chave=...` | `1x` por abertura da tela | medio |
| Transporte com requisicoes ativas e modal aberto | `scheduleTransportAutoRefresh()` -> `loadTransportState()` | `GET /api/web/transport/state?chave=...` | `1x` a cada `10s` enquanto houver requests ativas e nenhum bloqueio de UI | alto |
| Mensagem SSE do Transporte | `handleTransportRealtimeMessage()` -> `requestTransportRealtimeRefresh()` -> `loadTransportState()` | `GET /api/web/transport/state?chave=...` | `0..1x` por janela de debounce de `220ms` por rajada de eventos | medio |
| `visibilitychange`, `focus` ou `pageshow` com tela de Transporte aberta | listener de lifecycle -> `loadTransportState()` | `GET /api/web/transport/state?chave=...` | `+1x` por evento, alem do ramo do check | alto |

## 5. Helpers com request que existem no arquivo, mas nao aparecem ligados a listener ativo desta superficie

- `registerPasswordForCurrentUser()` faz `POST /api/web/auth/register-password`, mas nesta leitura nao aparece ligado a listener ativo do arquivo.
- Ele nao foi incluido como origem principal do burst runtime atual porque o fluxo efetivamente usado pela UI passa por `submitPasswordChange()` e `submitUserSelfRegistration()`.

## 6. Encadeamentos de maior risco observados

## 6.1 Bootstrap autenticado com chave persistida, senha restaurada e atividades automaticas habilitadas

Sequencia observada hoje:

1. `loadProjectCatalog()` -> `GET /api/web/projects`
2. `logoutWebSession({ silent: true })` -> `POST /api/web/auth/logout`
3. `refreshAuthenticationStatus()` -> `GET /api/web/auth/status`
4. `schedulePasswordVerification()` -> `attemptPasswordLogin()` -> `POST /api/web/auth/login`
5. `loadAuthenticatedApplication()` -> `GET /api/web/projects`
6. `loadAuthenticatedApplication()` -> `GET /api/web/check/locations`
7. `runLifecycleUpdateSequence()` -> `GET /api/web/check/state`
8. `runLifecycleUpdateSequence()` -> `POST /api/web/check/location`
9. `runAutomaticActivitiesIfNeeded()` -> `GET /api/web/check/state`
10. `submitAutomaticActivity()` -> `POST /api/web/check` quando a regra automatica dispara

Conclusao objetiva:

- um unico bootstrap autenticado pode empilhar ate `10` requests HTTP antes de qualquer acao manual do usuario.

## 6.2 Cada evento de lifecycle aceito pelo cooldown

Para `visibility`, `focus` e `pageshow`, o pacote padrao do check hoje e:

1. `GET /api/web/check/state`
2. `POST /api/web/check/location`
3. `GET /api/web/check/state` quando atividades automaticas estao habilitadas
4. `POST /api/web/check` quando uma atividade automatica e aplicavel

Se a tela de Transporte estiver aberta, soma-se:

5. `GET /api/web/transport/state`

Conclusao objetiva:

- cada retorno de aba ou janela pode produzir de `2` a `5` requests por pagina aberta, dependendo do estado de autenticacao, GPS, atividades automaticas e Transporte.

## 6.3 Verificacao silenciosa de senha

Hoje a senha pode disparar login em tres situacoes diferentes:

1. digitacao com debounce de `260ms`;
2. evento `change` do campo;
3. sincronizacao de autofill agendada em `focus` e em transicoes de lifecycle.

Conclusao objetiva:

- a verificacao silenciosa de senha e um dos maiores multiplicadores de burst porque antecipa `POST /api/web/auth/login` antes mesmo do submit principal.

## 7. Guardas que ja existem, mas nao eliminam o burst

Os principais freios ja presentes no arquivo sao:

1. `lifecycleTriggerCooldownMs = 1200` em `runLifecycleUpdateSequence()`;
2. `passwordVerificationDebounceMs = 260` em `schedulePasswordVerification()`;
3. `projectCatalogPromise` evita apenas duplicacao concorrente de `GET /api/web/projects`;
4. `locationRequestPromise` reutiliza request de localizacao pendente quando `forceRefresh` esta desligado;
5. `historyAbortController` e `authStatusAbortController` abortam requests anteriores das mesmas familias;
6. `transportRealtimeRefreshDebounceMs = 220` reduz rajada de refresh apos SSE;
7. `transportAutoRefreshIntervalMs = 10000` limita polling do Transporte a cada `10s`.

Conclusao objetiva:

- o arquivo ja tem alguns mecanismos de deduplicacao local, mas eles ainda nao evitam a soma de chamadas em cascata entre auth, state, location e auto-submit.

## 8. Resultado da auditoria

O maior risco de burst atual da SPA de check esta concentrado em quatro pontos:

1. restauracao de sessao com logout silencioso e relogin silencioso;
2. verificacao automatica de senha por debounce, change e autofill/focus;
3. pacote de lifecycle que consulta historico, localizacao e depois consulta historico de novo para decidir atividade automatica;
4. tela de Transporte aberta somando SSE, polling e refresh extra no mesmo lifecycle.

Essa leitura deixa a proxima etapa bem delimitada: reduzir tempestade de autenticacao e depois reduzir o pacote de lifecycle/localizacao, sem perder a telemetria nem quebrar o fluxo legitimo.