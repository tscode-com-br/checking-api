# Reducao de tempestade de lifecycle e localizacao da SPA de check - Fase 5 - incidente 504 de 2026-05-05

## 1. Objetivo executado

Reduzir burst de requests de lifecycle e localizacao em `sistema/app/static/check/app.js`, atuando sobre `runLifecycleUpdateSequence`, `updateLocationForLifecycleSequence`, `ensureLocationReadyForSubmit`, `refreshHistory` e os listeners de `visibilitychange`, `focus` e `pageshow`.

## 2. Hipotese ou risco atacado

O risco principal desta etapa era o frontend tratar cada retorno de aba como um refresh independente, o que gerava:

1. `GET /api/web/check/state` repetido para o mesmo estado recente;
2. `POST /api/web/check/location` repetido logo apos uma resolucao de localizacao ainda fresca;
3. um segundo `GET /api/web/check/state` dentro do mesmo lifecycle por causa de `runAutomaticActivitiesIfNeeded(...)`;
4. clusters de `visibility`, `focus` e `pageshow` disparando a mesma sequencia de forma redundante.

## 3. Arquivos alterados

1. `sistema/app/static/check/app.js`
2. `tests/check_user_location_ui.test.js`

## 4. O que mudou

### 4.1 `refreshHistory(...)` passou a reutilizar estado recente

1. Foi adicionado reuso local de `latestHistoryState` por `chave`, com janela curta de `5000 ms`.
2. Requests em voo da mesma `chave` passaram a ser compartilhados, em vez de abortar e refazer imediatamente o mesmo `GET /api/web/check/state`.

### 4.2 `runLifecycleUpdateSequence(...)` deixou de reconsultar `state` no mesmo ciclo

1. O payload retornado por `refreshHistory(...)` agora e reaproveitado como `remoteState` da avaliacao automatica.
2. Isso remove o `GET /api/web/check/state` redundante que antes ocorria logo depois do primeiro `GET /api/web/check/state` do proprio lifecycle.

### 4.3 Localizacao recente passou a ser reaproveitada

1. `applyLocationMatch(...)` agora registra o ultimo payload valido de resolucao de localizacao por `chave`.
2. `updateLocationForLifecycleSequence(...)` reutiliza essa resolucao recente dentro de uma janela curta de `5000 ms`.
3. `ensureLocationReadyForSubmit(...)` tambem reutiliza essa mesma resolucao recente, evitando um novo `POST /api/web/check/location` logo antes do submit quando o lifecycle acabou de resolver a posicao.

### 4.4 Listeners de lifecycle foram coalescidos

1. `visibilitychange`, `focus` e `pageshow` agora passam por `requestLifecycleUpdateFromUi(...)`.
2. Esse helper aplica um debounce curto de `180 ms` para evitar clusters redundantes de lifecycle na mesma volta de aba.
3. O helper tambem concentra o refresh do Transporte associado a esse mesmo retorno de UI, em vez de repetir o bloco por listener.

## 5. Comandos executados

1. `node --test tests/check_user_location_ui.test.js`
2. `node --test tests/check_user_location_ui.test.js`

## 6. Evidencias geradas

1. `docs/incidents/2026-05-05-504-phase5-check-spa-request-graph.md`
2. `docs/incidents/2026-05-05-504-phase5-auth-burst-reduction.md`
3. `docs/incidents/2026-05-05-504-phase5-lifecycle-location-burst-reduction.md`

## 7. Validacao executada

Suite focada do controlador web-check via `node:test`, cobrindo:

1. reuso de `state` recente no lifecycle;
2. ausencia do `fetchWebState(...)` redundante dentro do mesmo lifecycle;
3. reuso da ultima localizacao recente no submit guard;
4. listeners de `visibility`, `focus` e `pageshow` roteados pelo helper compartilhado;
5. regressao dos fluxos existentes de localizacao, mixed zone e atividades automaticas.

Resultado observado: `44` testes aprovados, `0` falhas.

## 8. Resultado

Aprovado.

Nao houve alteracao de host, Docker, Nginx, banco, worker ou runtime HTTP nesta execucao. O impacto ficou restrito ao cliente web-check e aos testes focados da propria superficie.

## 9. Rollback

Reverter apenas este diff em:

1. `sistema/app/static/check/app.js`
2. `tests/check_user_location_ui.test.js`

E rerodar:

1. `node --test tests/check_user_location_ui.test.js`

## 10. Proximo passo recomendado

Executar a proxima tarefa da Fase 5: montar a medicao antes/depois de requests por usuario para comprovar quantitativamente a queda de burst nos cenarios de bootstrap, autenticacao, retorno de aba, concessao de localizacao e submit.