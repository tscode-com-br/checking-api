# Plano robusto e minucioso para implementar a Situação 8 - Zona Mista no Checking Web

## 1. Objetivo

Implementar a nova Situação 8 do Checking Web de forma consistente, previsível e testável, cobrindo:

1. os 4 gatilhos de atualização descritos na regra funcional;
2. a alternância automática imediata ao entrar ou ser identificado na `Zona Mista`;
3. o bloqueio temporário configurável para leituras consecutivas ainda na `Zona Mista`;
4. as exceções que continuam permitindo transição imediata para `Zona de CheckOut`, `outside_workplace` e retorno a local elegível de check-in;
5. a atualização do documento funcional em `docs/regras_checkin_checkout_webapp.txt` para eliminar ambiguidades.

O objetivo não é criar uma solução paralela ou um fluxo ad hoc. O objetivo é encaixar a regra nova na superfície correta já existente do Checking Web, reaproveitando o estado remoto do usuário, o catálogo web de localizações e a orquestração automática já usada nos eventos de ciclo de vida.

## 2. Base técnica já confirmada no código

Os pontos abaixo já existem hoje e devem ser tratados como âncoras do plano:

1. `sistema/app/static/check/app.js` já executa a sequência automática de atualização em `startup`, `visibility`, `focus` e `pageshow` por meio de `runLifecycleUpdateSequence()`.
2. `sistema/app/static/check/app.js` já reaproveita a mesma decisão automática no botão de atualização manual, via `runManualLocationRefreshSequence()` chamando `runAutomaticActivitiesIfNeeded(locationPayload)`.
3. `sistema/app/static/check/automatic-activities.js` hoje só especializa `Zona de CheckOut`, `outside_workplace` e o retorno ao ambiente de trabalho sem localização cadastrada; `Zona Mista` ainda não é tratada como categoria própria.
4. A supressão atual de "mesma localização" impede nova ação quando `resolved_local` coincide com `current_local`; isso hoje bloquearia a `Zona Mista` para sempre, mesmo depois de o intervalo configurado expirar.
5. `sistema/app/services/user_sync.py`, por meio de `build_web_check_history_state()`, já expõe `current_action`, `current_local`, `last_checkin_at` e `last_checkout_at`; estes campos são suficientes para calcular a janela da `Zona Mista` sem exigir nova tabela.
6. `sistema/app/services/location_settings.py` e o admin em `sistema/app/static/admin` já persistem `mixed_zone_interval_minutes`; o campo já existe no produto, mas ainda não faz parte do contrato web do Checking Web.
7. `sistema/app/routers/web_check.py` ainda devolve, no catálogo web de localizações, apenas `items` e `location_accuracy_threshold_meters`; será necessário expor também `mixed_zone_interval_minutes`.
8. A `Zona Mista` já pode continuar sendo tratada como uma localização `matched`; não há necessidade de criar um novo `status` no backend de matching.

## 3. Consolidação funcional da nova Situação 8

Antes de codificar, a regra precisa ficar sem ambiguidades. A consolidação funcional recomendada é a seguinte:

1. A regra vale quando a aplicação estiver com `Atividades Automáticas` habilitada e a localização com permissão total.
2. Os gatilhos obrigatórios são: carregar a aplicação, dar `Refresh` no navegador, trazer o navegador para primeiro plano com a URL já aberta e alternar de volta para a aba do Checking Web.
3. A atualização de localização deve sempre acontecer nesses gatilhos.
4. A `Zona Mista` não depende apenas de "mudança de local". Ela também precisa reagir a leituras consecutivas ainda dentro da própria `Zona Mista`, porque é justamente aí que entra o cooldown configurável.
5. Na primeira identificação da `Zona Mista` após um estado anterior não misto, a ação continua sendo imediata:
   - último evento `checkin` -> fazer `checkout` em `Zona Mista`;
   - último evento `checkout` -> fazer `checkin` em `Zona Mista`.
6. Depois que a própria `Zona Mista` gerou a última atividade automática, leituras consecutivas nela entram em janela de bloqueio temporário.
7. O cooldown deve ser considerado ativo enquanto `tempo_decorrido < mixed_zone_interval_minutes`.
8. O cooldown deve ser considerado expirado quando `tempo_decorrido >= mixed_zone_interval_minutes`.
9. Ao expirar o cooldown, a aplicação volta a permitir alternância automática na própria `Zona Mista`, mesmo que `current_local` ainda seja `Zona Mista`.
10. As exceções continuam valendo sem esperar o cooldown:
    - se o usuário estava em `checkin` na `Zona Mista` e agora caiu em `Zona de CheckOut` ou `outside_workplace`, o `checkout` deve acontecer imediatamente;
    - se o usuário estava em `checkout` na `Zona Mista` e agora caiu em qualquer outra localização elegível de check-in, ou em `not_in_known_location` ainda dentro da distância mínima de check-out automático, o `checkin` deve acontecer imediatamente e o cooldown da `Zona Mista` deve ser ignorado.

## 4. Matriz de decisão resumida

| Estado remoto anterior | Leitura atual | Janela da Zona Mista | Resultado esperado |
| --- | --- | --- | --- |
| Última ação = `checkin` em local regular ou arredores | `matched` em `Zona Mista` | não aplicável | `checkout` imediato em `Zona Mista` |
| Última ação = `checkout` em local regular, `Zona de CheckOut` ou `outside_workplace` | `matched` em `Zona Mista` | não aplicável | `checkin` imediato em `Zona Mista` |
| Última ação = `checkin` em `Zona Mista` | nova leitura em `Zona Mista` | `< intervalo` | nenhuma ação |
| Última ação = `checkin` em `Zona Mista` | nova leitura em `Zona Mista` | `>= intervalo` | `checkout` em `Zona Mista` |
| Última ação = `checkout` em `Zona Mista` | nova leitura em `Zona Mista` | `< intervalo` | nenhuma ação |
| Última ação = `checkout` em `Zona Mista` | nova leitura em `Zona Mista` | `>= intervalo` | `checkin` em `Zona Mista` |
| Última ação = `checkin` em `Zona Mista` | `matched` em `Zona de CheckOut` ou `status = outside_workplace` | qualquer valor | `checkout` imediato |
| Última ação = `checkout` em `Zona Mista` | outro local `matched` elegível ou `status = not_in_known_location` dentro do ambiente de trabalho | qualquer valor | `checkin` imediato e descarte do cooldown |

## 5. Tradução dos exemplos do requisito em critérios de aceite

### Exemplo 1 traduzido para aceite

1. O usuário entra na `Zona Mista` vindo de um estado anterior de `checkin` no ambiente de trabalho.
2. O Checking Web faz `checkout` imediato em `Zona Mista`.
3. Antes de o intervalo da `Zona Mista` expirar, o usuário volta para uma localização elegível de `checkin` fora da `Zona Mista` ou para `not_in_known_location` ainda dentro do ambiente de trabalho.
4. O sistema deve fazer `checkin` imediato e ignorar o cooldown da `Zona Mista`.

### Exemplo 2 traduzido para aceite

1. O usuário entra na `Zona Mista` vindo de um estado anterior de `checkin`.
2. O sistema faz `checkout` em `Zona Mista`.
3. Antes de o intervalo expirar, a nova leitura volta a apontar `Zona Mista`.
4. O sistema não deve fazer `checkin` ainda.

### Exemplo 3 traduzido para aceite

1. A última atividade do usuário já foi um `checkout` em `Zona Mista`.
2. A nova leitura ainda aponta `Zona Mista`.
3. O tempo decorrido desde esse `checkout` ainda está abaixo do intervalo configurado.
4. O sistema não deve fazer `checkin`.

### Exemplo 4 traduzido para aceite

1. A última atividade do usuário já foi um `checkout` em `Zona Mista`.
2. A nova leitura ainda aponta `Zona Mista`.
3. O tempo decorrido desde esse `checkout` já atingiu ou superou o intervalo configurado.
4. O sistema deve fazer `checkin` imediato em `Zona Mista`.

### Casos simétricos que também precisam entrar

Mesmo que não estejam descritos com o mesmo detalhamento nos exemplos do usuário, os casos abaixo precisam ser cobertos para que a implementação fique coerente:

1. `checkin` em `Zona Mista` seguido de nova leitura em `Zona Mista` antes do intervalo: não fazer `checkout`.
2. `checkin` em `Zona Mista` seguido de nova leitura em `Zona Mista` após o intervalo: fazer `checkout`.
3. `checkin` em `Zona Mista` seguido de `Zona de CheckOut` ou `outside_workplace`: fazer `checkout` imediatamente, independentemente do intervalo.

## 6. Lacunas reais que precisam ser fechadas

### 6.1 Contrato web ainda incompleto para a nova regra

Hoje o Checking Web não recebe `mixed_zone_interval_minutes` no catálogo `GET /api/web/check/locations`. Sem isso, a UI não tem como saber quando permitir nova alternância consecutiva na própria `Zona Mista`.

Consequência prática: a regra nova não pode ficar apenas no frontend sem antes estender esse contrato.

### 6.2 A engine automática atual não sabe o que é `Zona Mista`

Hoje o arquivo `sistema/app/static/check/automatic-activities.js` só responde a três grandes grupos:

1. `Zona de CheckOut`;
2. `outside_workplace`;
3. retorno ao ambiente de trabalho sem local cadastrado.

Consequência prática: a `Zona Mista` não tem helpers próprios, não tem cooldown próprio e não tem critério para reabilitar alternância depois de uma leitura consecutiva na mesma localização.

### 6.3 A regra nova exige quebrar a supressão genérica de "mesma localização"

O comportamento atual de não repetir ação quando `resolved_local === current_local` continua correto para os demais locais, mas não é suficiente para `Zona Mista`.

Se nada mudar, o sistema bloqueará indefinidamente qualquer nova alternância em `Zona Mista` após o primeiro evento misto. Isso contradiz diretamente os exemplos 3 e 4.

### 6.4 Não há cobertura de teste para cooldown em `Zona Mista`

Os testes existentes cobrem:

1. troca de local após `checkin`;
2. saída da `Zona de CheckOut`;
3. `outside_workplace`;
4. retorno aos arredores do ambiente de trabalho.

Ainda não há testes exercitando `Zona Mista`, expiração de cooldown ou reaproveitamento dessa regra nos gatilhos de ciclo de vida.

## 7. Plano de implementação por superfície

### Fase 1 - Fechar o contrato de configuração para o frontend web

#### Objetivo

Garantir que o frontend do Checking Web receba o intervalo configurável da `Zona Mista` sem depender de hardcode.

#### Arquivos-alvo

1. `sistema/app/schemas.py`
2. `sistema/app/routers/web_check.py`
3. `sistema/app/services/location_settings.py` (reuso apenas, sem nova regra persistente)
4. `tests/test_api_flow.py`

#### Mudanças previstas

1. Estender `WebLocationOptionsResponse` para incluir `mixed_zone_interval_minutes`.
2. Alterar `get_web_check_locations()` para retornar o valor vindo de `get_mixed_zone_interval_minutes(db)`.
3. Atualizar os testes do catálogo web para exigir a nova chave.
4. Manter o catálogo mobile inalterado, porque a regra solicitada é do Checking Web.

#### Critério de saída

`GET /api/web/check/locations` devolve, no mínimo, `items`, `location_accuracy_threshold_meters` e `mixed_zone_interval_minutes`.

### Fase 2 - Introduzir estado local explícito para a janela da Zona Mista

#### Objetivo

Fazer o app carregar, guardar, limpar e propagar o intervalo da `Zona Mista` até a engine automática.

#### Arquivos-alvo

1. `sistema/app/static/check/app.js`

#### Mudanças previstas

1. Criar estado local explícito, por exemplo `mixedZoneIntervalMinutes`.
2. Popular esse estado em `loadManualLocations()` junto com `location_accuracy_threshold_meters`.
3. Resetar esse estado quando o usuário deixar de estar autenticado ou quando o catálogo for limpo.
4. Garantir que o valor esteja pronto antes do `runLifecycleUpdateSequence({ triggerSource: 'startup' })`, aproveitando o fato de que `loadAuthenticatedApplication()` já chama `loadManualLocations()` antes da sequência automática.
5. Definir fallback seguro para rollout parcial: se o payload vier sem o campo por algum motivo transitório, usar o default backend conhecido apenas como proteção temporária e registrar isso em comentário curto ou helper dedicado.

#### Critério de saída

Os gatilhos automáticos conseguem consultar `mixedZoneIntervalMinutes` sem nova chamada extra de rede no momento da decisão.

### Fase 3 - Refatorar a engine de decisão automática para tratar Zona Mista

#### Objetivo

Tratar `Zona Mista` como categoria especial de automação sem quebrar as regras já existentes de `Zona de CheckOut`, `outside_workplace` e arredores do ambiente de trabalho.

#### Arquivos-alvo

1. `sistema/app/static/check/automatic-activities.js`
2. `sistema/app/static/check/app.js`

#### Mudanças previstas

1. Criar helper explícito para reconhecer `Zona Mista`, por exemplo `isMixedZoneLocationName()`.
2. Criar helper para identificar se a última atividade relevante aconteceu na própria `Zona Mista`.
3. Criar helper para calcular tempo decorrido desde o último `checkin` ou `checkout` em `Zona Mista`, usando `last_checkin_at`, `last_checkout_at`, `current_action` e `current_local`.
4. Criar helper para dizer se o cooldown da `Zona Mista` ainda está ativo.
5. Refatorar a decisão automática para retornar um resultado mais rico do que simples booleanos quando a regra exigir isso. O melhor formato tende a ser algo como `resolveAutomaticActivityDecision(...) -> { performed, action, local, reason }` ou equivalente.
6. Preservar a supressão de "mesma localização" para todos os locais não mistos.
7. Quebrar a supressão de "mesma localização" apenas na `Zona Mista`, mas somente quando o cooldown já tiver expirado.
8. Manter o backend de matching inalterado: `Zona Mista` continua chegando como `matched` com `resolved_local = 'Zona Mista'`.

#### Critério de saída

O comportamento automático passa a distinguir três estados para `Zona Mista`:

1. primeira entrada ou retorno após outro local -> alternância imediata;
2. repetição consecutiva antes do intervalo -> nenhuma ação;
3. repetição consecutiva depois do intervalo -> nova alternância permitida.

### Fase 4 - Acoplar a nova decisão aos gatilhos do ciclo de vida sem abrir regressão

#### Objetivo

Garantir que a Situação 8 funcione nos 4 gatilhos descritos pelo requisito e continue integrada ao fluxo já existente do Checking Web.

#### Arquivos-alvo

1. `sistema/app/static/check/app.js`

#### Mudanças previstas

1. Fazer `runAutomaticActivitiesIfNeeded()` receber o intervalo configurado da `Zona Mista`.
2. Preservar o fluxo já existente de `refreshHistory()` -> `updateLocationForLifecycleSequence()` -> `runAutomaticActivitiesIfNeeded()`.
3. Validar explicitamente os 4 gatilhos da Situação 8: `startup`, `visibility`, `focus` e `pageshow`.
4. Decidir conscientemente se o botão manual de atualizar localização deve herdar a mesma regra. Tecnicamente ele já compartilha a mesma engine automática, então a tendência correta é herdar a mesma decisão para não duplicar regra.
5. Garantir que mensagens de status continuem genéricas e não virem fonte de regressão visual.

#### Critério de saída

A nova regra funciona no ciclo de vida e continua compatível com o refresh manual já alinhado à automação.

### Fase 5 - Cobertura de testes automática e regressão

#### Objetivo

Provar a nova regra na menor superfície correta e evitar regressão nos comportamentos já existentes.

#### Arquivos-alvo

1. `tests/web_automatic_activities.test.js`
2. `tests/check_user_location_ui.test.js`
3. `tests/test_api_flow.py`

#### Mudanças previstas

1. Em `tests/web_automatic_activities.test.js`, adicionar casos unitários para:
   - reconhecimento de `Zona Mista`;
   - `checkout` imediato ao entrar em `Zona Mista` vindo de `checkin`;
   - `checkin` imediato ao entrar em `Zona Mista` vindo de `checkout`;
   - repetição consecutiva em `Zona Mista` antes do intervalo -> sem ação;
   - repetição consecutiva em `Zona Mista` após o intervalo -> ação permitida;
   - exceção para `Zona de CheckOut` e `outside_workplace` após `checkin` em `Zona Mista`;
   - exceção para retorno a local elegível após `checkout` em `Zona Mista`.
2. Em `tests/check_user_location_ui.test.js`, adicionar pelo menos um teste de integração leve provando que a sequência de ciclo de vida chama a engine automática com a configuração necessária e não perde a regra na passagem pelo controller.
3. Em `tests/test_api_flow.py`, atualizar o contrato de `/api/web/check/locations` para incluir `mixed_zone_interval_minutes`.
4. Reexecutar testes existentes ligados a `Zona de CheckOut`, `outside_workplace`, refresh manual e catálogo web para garantir que nada regrediu.

#### Critério de saída

Existe cobertura automatizada para todos os exemplos fornecidos pelo usuário e para os casos simétricos necessários à consistência da regra.

### Fase 6 - Atualização documental e homologação funcional

#### Objetivo

Fechar a implementação com regra funcional escrita de forma inequívoca e uma matriz de homologação que o time consiga seguir.

#### Arquivos-alvo

1. `docs/regras_checkin_checkout_webapp.txt`
2. `docs/temp_008.md`

#### Mudanças previstas

1. Atualizar a Situação 8 no documento funcional para incluir:
   - os 4 gatilhos;
   - a leitura consecutiva na própria `Zona Mista`;
   - o campo `Intervalo de Tempo para Zona Mista` como parâmetro da regra;
   - as exceções de saída;
   - a regra de expiração do cooldown.
2. Registrar neste plano que a comparação temporal consolidada deve ser `tempo_decorrido >= intervalo` para reabrir a alternância na própria `Zona Mista`.
3. Preparar uma checklist de homologação manual com os exemplos do requisito e os casos simétricos.

#### Critério de saída

O código e a documentação passam a descrever exatamente a mesma regra.

## 8. Riscos e decisões que precisam ser respeitados

1. Não criar nova tabela nem novo estado persistente sem necessidade; o estado remoto atual do usuário já fornece os dados mínimos para o cooldown.
2. Não espalhar a regra da `Zona Mista` por vários lugares do frontend; a decisão deve ficar concentrada na engine automática.
3. Não transformar `Zona Mista` em novo `status` backend se a informação necessária já chega como `matched` com `resolved_local`.
4. Não perder as regras existentes de `Zona de CheckOut` e `outside_workplace` ao introduzir a `Zona Mista`.
5. Não depender de relógio salvo em `localStorage` como fonte de verdade; o cálculo deve usar preferencialmente os timestamps remotos do histórico.
6. Não deixar a reabertura da `Zona Mista` dependente exclusivamente de "mudança de local", porque isso contradiz os exemplos de repetição consecutiva na própria zona.
7. Se houver rollout parcial frontend/backend, proteger a UI com fallback mínimo para `mixed_zone_interval_minutes`, mas tratar isso apenas como defesa transitória, não como contrato definitivo.

## 9. Critérios de aceite final

O trabalho só deve ser considerado concluído quando todos os itens abaixo forem verdadeiros:

1. `GET /api/web/check/locations` entrega `mixed_zone_interval_minutes`.
2. A `Zona Mista` é reconhecida explicitamente pela engine automática.
3. Leituras consecutivas em `Zona Mista` antes do intervalo não geram nova alternância.
4. Leituras consecutivas em `Zona Mista` após o intervalo geram a alternância esperada.
5. `Zona de CheckOut` e `outside_workplace` continuam funcionando como exceções imediatas após `checkin` em `Zona Mista`.
6. O retorno a localização elegível de `checkin` continua funcionando imediatamente após `checkout` em `Zona Mista`, descartando o cooldown.
7. Os 4 gatilhos do ciclo de vida da Situação 8 ficam cobertos.
8. Os documentos `docs/regras_checkin_checkout_webapp.txt` e `docs/temp_008.md` ficam alinhados com a implementação.

## 10. Checklist executável de homologação

### 10.1 Pré-condições gerais da rodada manual

Antes de marcar qualquer cenário como homologado, confirmar os itens abaixo:

- [ ] existe pelo menos um projeto com `Zona Mista`, `Zona de CheckOut` e uma localização elegível de `checkin` fora da `Zona Mista`;
- [ ] o campo `Intervalo de Tempo para Zona Mista` está configurado no admin com um valor conhecido para a rodada, de preferência `20` minutos para facilitar comparação com os testes automatizados;
- [ ] o usuário de teste está autenticado no Checking Web e com `Atividades Automáticas` habilitada;
- [ ] a permissão de localização do navegador está em compartilhamento total, sem bloqueio parcial do browser ou do sistema operacional;
- [ ] o estado remoto inicial do usuário (`current_action`, `current_local`, `last_checkin_at`, `last_checkout_at`) está conhecido antes do início de cada cenário;
- [ ] a rodada manual explicita qual gatilho será usado para disparar a atualização: `startup`, `refresh`, `focus` ou `pageshow`/troca de aba;
- [ ] quando o cenário depender de expiração do cooldown, o horário de início da janela foi anotado para confirmar a comparação `tempo_decorrido < intervalo` versus `tempo_decorrido >= intervalo`.

### 10.2 Checklist por cenário funcional

#### H0. Matriz de gatilhos obrigatórios

- [ ] com o usuário elegível e a geolocalização disponível, validar `startup` carregando a aplicação já com a sessão ativa;
- [ ] validar `refresh` recarregando a página com a mesma URL do Checking Web;
- [ ] validar `focus` trazendo o navegador para primeiro plano com a aplicação já aberta;
- [ ] validar `pageshow`/troca de aba saindo e voltando para a aba do Checking Web;
- [ ] em todos os quatro gatilhos, confirmar que a localização é atualizada antes da decisão automática;
- [ ] em todos os quatro gatilhos, confirmar que a decisão automática usa o intervalo configurado da `Zona Mista`.

Resultado esperado:

1. a atualização de localização sempre acontece;
2. a mesma orquestração automática continua ativa em todos os gatilhos;
3. se a leitura atual cair em `Zona Mista`, a decisão considera o cooldown configurado.

#### H1. Exemplo 1 do requisito

- [ ] preparar o usuário em `checkin` fora da `Zona Mista`;
- [ ] levar a leitura atual para `Zona Mista` e disparar um dos gatilhos válidos;
- [ ] confirmar `checkout` imediato em `Zona Mista`;
- [ ] antes de o intervalo expirar, voltar para uma localização elegível de `checkin` fora da `Zona Mista` ou para `not_in_known_location` ainda dentro do ambiente de trabalho;
- [ ] disparar novo gatilho automático ou usar o botão de atualização manual;
- [ ] confirmar `checkin` imediato e descarte do cooldown da `Zona Mista`.

#### H2. Exemplo 2 do requisito

- [ ] preparar o usuário em `checkin` fora da `Zona Mista`;
- [ ] levar a leitura para `Zona Mista` e confirmar `checkout` imediato;
- [ ] antes de o intervalo expirar, manter ou repetir a leitura em `Zona Mista`;
- [ ] disparar novo gatilho automático ou atualização manual;
- [ ] confirmar que nenhum `checkin` novo é realizado enquanto `tempo_decorrido < intervalo`.

#### H3. Exemplo 3 do requisito

- [ ] preparar o usuário com última atividade igual a `checkout` em `Zona Mista`;
- [ ] manter a nova leitura em `Zona Mista`;
- [ ] executar o gatilho ainda dentro da janela configurada;
- [ ] confirmar que nenhum `checkin` é realizado enquanto `tempo_decorrido < intervalo`.

#### H4. Exemplo 4 do requisito

- [ ] preparar o usuário com última atividade igual a `checkout` em `Zona Mista`;
- [ ] manter a nova leitura em `Zona Mista`;
- [ ] aguardar até `tempo_decorrido >= intervalo` e disparar novo gatilho;
- [ ] confirmar `checkin` imediato em `Zona Mista`.

#### H5. Caso simétrico obrigatório: `checkin` em `Zona Mista` seguido de repetição antes do intervalo

- [ ] preparar o usuário com última atividade igual a `checkin` em `Zona Mista`;
- [ ] repetir a leitura em `Zona Mista` antes do intervalo expirar;
- [ ] disparar novo gatilho automático ou atualização manual;
- [ ] confirmar que nenhum `checkout` é realizado enquanto `tempo_decorrido < intervalo`.

#### H6. Caso simétrico obrigatório: `checkin` em `Zona Mista` seguido de repetição após o intervalo

- [ ] preparar o usuário com última atividade igual a `checkin` em `Zona Mista`;
- [ ] manter a leitura em `Zona Mista`;
- [ ] aguardar até `tempo_decorrido >= intervalo` e disparar novo gatilho;
- [ ] confirmar `checkout` imediato em `Zona Mista`.

#### H7. Caso simétrico obrigatório: saída imediata para `Zona de CheckOut` ou `outside_workplace`

- [ ] preparar o usuário com última atividade igual a `checkin` em `Zona Mista`;
- [ ] antes de o intervalo expirar, mover a leitura para `Zona de CheckOut`;
- [ ] confirmar `checkout` imediato sem esperar o cooldown;
- [ ] repetir a preparação, agora movendo a leitura para `outside_workplace`;
- [ ] confirmar `checkout` imediato também nesse caso.

#### H8. Caso de coerência complementar: entrada inicial na `Zona Mista` a partir de estados não mistos

- [ ] validar entrada em `Zona Mista` a partir de `checkin` em local regular e confirmar `checkout` imediato;
- [ ] validar entrada em `Zona Mista` a partir de `checkout` em local regular e confirmar `checkin` imediato;
- [ ] validar entrada em `Zona Mista` a partir de `checkout` em `Zona de CheckOut` e confirmar `checkin` imediato;
- [ ] validar entrada em `Zona Mista` a partir de `checkout` em `outside_workplace` e confirmar `checkin` imediato.

### 10.3 Resumo curto de cobertura automática e lacunas manuais

Cobertura automatizada já existente:

1. Contrato e propagação de configuração:
   - `tests/test_api_flow.py::test_web_locations_catalog_includes_accuracy_threshold_for_lifecycle_capture`;
   - `tests/test_api_flow.py::test_admin_locations_crud_and_mobile_catalog_sync`;
   - `tests/check_user_location_ui.test.js::check controller stores mixed zone interval from the web locations catalog, falls back during partial rollout, and clears it on reset paths`;
   - `tests/check_user_location_ui.test.js::check controller forwards the loaded mixed zone interval into the automatic location decision engine`.
2. Matriz da engine automática da `Zona Mista`:
   - `tests/web_automatic_activities.test.js::mixed zone initial entry triggers automatic alternation from prior non-mixed states` cobre a entrada inicial a partir de estados não mistos;
   - `tests/web_automatic_activities.test.js::mixed zone repeated reads stay blocked while the cooldown is active and reopen when it expires` cobre o caminho de `checkout` em `Zona Mista` antes e depois do intervalo;
   - `tests/web_automatic_activities.test.js::mixed zone repeated reads also reopen for a prior mixed-zone check-in only after the interval expires` cobre o caminho simétrico de `checkin` em `Zona Mista` antes e depois do intervalo;
   - `tests/web_automatic_activities.test.js::mixed zone exit exceptions keep automatic checkout immediate after a mixed-zone check-in` cobre `Zona de CheckOut` e `outside_workplace` após `checkin` em `Zona Mista`;
   - `tests/web_automatic_activities.test.js::mixed zone exit exceptions keep automatic check-in immediate after a mixed-zone checkout` cobre retorno imediato a local elegível após `checkout` em `Zona Mista`.
3. Orquestração do controller e passagem correta dos dados:
   - `tests/check_user_location_ui.test.js::check controller keeps loading the locations catalog before the startup lifecycle refresh` cobre `startup`;
   - `tests/check_user_location_ui.test.js::check lifecycle sequence forwards the stored mixed zone interval into the automatic engine` cobre a passagem de configuração no fluxo de lifecycle;
   - `tests/check_user_location_ui.test.js::check controller keeps visibility, focus and pageshow routed through the shared lifecycle update sequence` cobre o roteamento dos demais gatilhos de ciclo de vida;
   - `tests/check_user_location_ui.test.js::manual refresh forwards the stored mixed zone interval into the automatic engine` cobre o refresh manual;
   - `tests/check_user_location_ui.test.js::check controller submits automatic checkout when Zona Mista is reached after a remote check-in`, `check controller keeps checkout zone forcing automatic checkout after a mixed-zone check-in`, `check controller keeps outside_workplace forcing automatic checkout after a mixed-zone check-in`, `check controller keeps automatic check-in immediate when leaving mixed zone for a known location after checkout` e `check controller keeps automatic check-in immediate when leaving mixed zone for a nearby eligible unregistered location` cobrem as decisões automáticas finais no controller.

Cenários que ainda dependem de validação manual em navegador real:

1. comprovação fim a fim de que `startup`, `refresh`, troca de aba, `focus` e `pageshow` disparam atualização de localização real no browser com a permissão de geolocalização efetivamente concedida;
2. comprovação fim a fim de que a leitura real do GPS cai na geofence esperada para `Zona Mista`, `Zona de CheckOut`, local elegível de `checkin` e `outside_workplace`;
3. comprovação de UX e timing real das mensagens de status durante a atualização automática e o refresh manual;
4. comprovação operacional do cooldown usando relógio real e estado remoto real, sem harnesses ou tempos simulados.

## 11. To-do executável por fases

### Fase 1 - Contrato web e configuração

1. Você é o agente responsável por estender o contrato do catálogo web de localizações para a Situação 8. Audite `sistema/app/schemas.py` e `sistema/app/routers/web_check.py`, adicione `mixed_zone_interval_minutes` ao `WebLocationOptionsResponse`, devolva esse valor em `GET /api/web/check/locations` usando a configuração já persistida no backend, e atualize os testes de contrato em `tests/test_api_flow.py`. Preserve o catálogo mobile sem mudanças. Valide com o menor conjunto de testes focados nesse contrato.

2. Você é o agente responsável por propagar a configuração da `Zona Mista` para o frontend do Checking Web. Trabalhe em `sistema/app/static/check/app.js`, introduza estado explícito para `mixedZoneIntervalMinutes`, carregue esse valor em `loadManualLocations()`, limpe-o quando o catálogo for resetado e garanta que ele esteja disponível antes da sequência automática de `startup`. Se precisar de fallback para rollout parcial, implemente o menor fallback seguro e documente a escolha. Valide com testes focados ou, se não houver teste pronto, com a menor verificação executável da superfície tocada.

### Fase 2 - Engine automática da Zona Mista

1. Você é o agente responsável por refatorar `sistema/app/static/check/automatic-activities.js` para tratar `Zona Mista` como categoria própria. Adicione helpers explícitos para reconhecer `Zona Mista`, identificar se a última atividade relevante aconteceu nela e calcular se o cooldown ainda está ativo a partir de `current_action`, `current_local`, `last_checkin_at`, `last_checkout_at` e do intervalo configurado. Preserve integralmente as regras já existentes de `Zona de CheckOut`, `outside_workplace` e arredores do ambiente de trabalho.

2. Você é o agente responsável por corrigir a lacuna central da Situação 8: a supressão genérica de "mesma localização" não pode bloquear a `Zona Mista` para sempre. Refatore a decisão automática para que leituras consecutivas em `Zona Mista` continuem bloqueadas apenas enquanto `tempo_decorrido < intervalo`, e voltem a permitir alternância quando `tempo_decorrido >= intervalo`. Mantenha a supressão de "mesma localização" para todos os outros locais. Valide primeiro com testes unitários da própria engine.

### Fase 3 - Orquestração do ciclo de vida e refresh

1. Você é o agente responsável por acoplar a nova decisão da `Zona Mista` aos gatilhos de ciclo de vida do Checking Web sem abrir regressão. Revise `runAutomaticActivitiesIfNeeded()`, `runLifecycleUpdateSequence()` e `runManualLocationRefreshSequence()` em `sistema/app/static/check/app.js`, injete a configuração da `Zona Mista` na decisão automática e confirme que `startup`, `visibility`, `focus` e `pageshow` continuam passando pela mesma orquestração. Só mude o que for necessário para a regra nova.

2. Você é o agente responsável por tratar corretamente as exceções da Situação 8 na mesma orquestração. Garanta que `Zona de CheckOut` e `outside_workplace` continuem forçando `checkout` imediato após `checkin` em `Zona Mista`, e que retorno a qualquer local elegível de `checkin` continue fazendo `checkin` imediato após `checkout` em `Zona Mista`, descartando o cooldown. Rode a menor validação executável logo após a primeira edição substantiva.

### Fase 4 - Testes automatizados

1. Você é o agente responsável por ampliar `tests/web_automatic_activities.test.js` para cobrir toda a matriz da `Zona Mista`. Escreva testes unitários para entrada inicial na `Zona Mista`, repetição consecutiva antes do intervalo, repetição consecutiva depois do intervalo, exceções imediatas de saída e simetria entre `checkin` e `checkout`. Preserve os testes existentes e mantenha a cobertura focada na menor superfície correta.

2. Você é o agente responsável por adicionar cobertura de integração leve em `tests/check_user_location_ui.test.js` para provar que a sequência de ciclo de vida e o refresh manual continuam chamando a engine automática com a configuração necessária da `Zona Mista`. Evite testes excessivamente amplos; priorize um harness focado na passagem correta dos dados e no não rompimento do fluxo existente.

3. Você é o agente responsável por atualizar os testes Python do contrato web em `tests/test_api_flow.py` para a Situação 8. Faça o catálogo web exigir `mixed_zone_interval_minutes`, mantenha o catálogo mobile sem essa chave e rode apenas os testes mínimos necessários para validar o contrato alterado.

### Fase 5 - Documentação e homologação

1. Você é o agente responsável por revisar a documentação funcional para que ela fique rigorosamente alinhada ao código. Atualize `docs/regras_checkin_checkout_webapp.txt`, deixando a Situação 8 explícita quanto aos gatilhos, leituras consecutivas em `Zona Mista`, cooldown configurável, exceções imediatas e regra de expiração `tempo_decorrido >= intervalo`.

2. Você é o agente responsável por consolidar a homologação da Situação 8 em `docs/temp_008.md` ou documento equivalente aprovado. Transforme os exemplos do requisito em checklist executável, inclua os casos simétricos que faltam para coerência e feche com um resumo curto dizendo quais testes automatizados cobrem cada cenário e quais cenários ainda dependem de validação manual em navegador real.