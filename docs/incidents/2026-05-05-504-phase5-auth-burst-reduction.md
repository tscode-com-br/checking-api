# Reducao de tempestade de autenticacao da SPA de check - Fase 5 - incidente 504 de 2026-05-05

## 1. Objetivo executado

Reduzir burst de autenticacao em `sistema/app/static/check/app.js`, atuando sobre `refreshAuthenticationStatus`, `schedulePasswordVerification`, `attemptPasswordLogin`, `loadAuthenticatedApplication` e o fluxo de autofill/autologin equivalente.

## 2. Hipotese ou risco atacado

O principal risco desta etapa era o frontend tratar digitacao, restauracao de senha, autofill e reaparicao da aba como eventos equivalentes, permitindo:

1. login silencioso enquanto o usuario ainda digitava;
2. verificacoes repetidas da mesma combinacao `chave + senha`;
3. replay do bootstrap autenticado para a mesma sessao verificada.

## 3. Arquivos alterados

1. `sistema/app/static/check/app.js`
2. `tests/check_user_location_ui.test.js`

## 4. O que mudou

### 4.1 Gatilhos de login silencioso endurecidos

1. `syncPasswordInputState(...)` deixou de agendar verificacao automatica durante digitacao comum.
2. `schedulePasswordVerification(...)` passou a exigir senha com comprimento valido e, por padrao, compatibilidade com a senha persistida da `chave` antes de auto-submeter.
3. O fluxo de autofill continua funcional, mas agora usa uma trilha explicita de auto-verificacao estabilizada em vez de reaproveitar o mesmo caminho agressivo da digitacao.

### 4.2 Menos repeticao para a mesma combinacao `chave + senha`

1. A verificacao silenciosa agora monta um fingerprint por `chave + senha`.
2. A mesma combinacao nao e reagendada enquanto estiver pendente, em voo ou ja tentada silenciosamente na mesma pagina.
3. Tentativas explicitas do usuario continuam possiveis por `change` do campo e por `Enter`, mas sem `allowPartialVerification`.

### 4.3 Bootstrap autenticado sem replay inutil

1. `loadAuthenticatedApplication(...)` agora deduplica a carga autenticada para a mesma sessao verificada.
2. Se a mesma combinacao autenticada tentar reiniciar o bootstrap, o frontend retorna imediatamente sem repetir `projects`, `locations` e `startup lifecycle`.

## 5. Comandos executados

1. `node --test tests/check_user_location_ui.test.js`

## 6. Evidencias geradas

1. `docs/incidents/2026-05-05-504-phase5-check-spa-request-graph.md`
2. `docs/incidents/2026-05-05-504-phase5-auth-burst-reduction.md`

## 7. Validacao executada

Validacao focada do controlador web-check via `node:test`, incluindo:

1. o fluxo autenticado continua carregando catalogo e lifecycle de startup uma vez;
2. digitacao comum nao dispara auto-verificacao;
3. `refreshAuthenticationStatus(...)` so reativa auto-login quando a senha restaurada bate com a persistencia esperada;
4. o bootstrap autenticado nao e reexecutado para a mesma sessao.

Resultado observado: `42` testes aprovados, `0` falhas.

## 8. Resultado

Aprovado.

Nao houve alteracao de host, Docker, banco, edge ou worker nesta execucao. O impacto ficou restrito ao cliente web-check e aos testes unitarios focados da superficie.

## 9. Rollback

Reverter apenas este diff em:

1. `sistema/app/static/check/app.js`
2. `tests/check_user_location_ui.test.js`

E rerodar:

1. `node --test tests/check_user_location_ui.test.js`

## 10. Proximo passo recomendado

Executar a proxima tarefa da Fase 5: reduzir tempestade de lifecycle e localizacao em `runLifecycleUpdateSequence`, `updateLocationForLifecycleSequence`, `ensureLocationReadyForSubmit`, `refreshHistory` e nos listeners de `visibilitychange`, `focus` e `pageshow`.