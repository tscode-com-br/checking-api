# Plano de execução para a próxima rodada da tela de transporte

## Contexto atual

A tela de transporte do Checking Web foi separada para um módulo próprio em `sistema/app/static/check/transport-screen.js`, mantendo o shell principal em `sistema/app/static/check/app.js` como ponto de compatibilidade com os contratos de teste baseados em fonte.

Isso muda a forma de implementar a próxima rodada:

1. As mudanças de UX e fluxo devem ser feitas prioritariamente no módulo `transport-screen.js`, em `index.html` e em `styles.css`.
2. Mudanças de regra de negócio que precisem ser realmente garantidas devem ser fechadas também no backend, principalmente em `sistema/app/routers/web_check.py`, `sistema/app/services/transport.py` e `sistema/app/schemas.py`.
3. Os testes atuais do transporte ainda leem strings literais de `app.js`, então qualquer refino estrutural precisa preservar os contratos de fonte já existentes enquanto a nova lógica roda no módulo extraído.

## Objetivo

Executar as 7 alterações abaixo sem regressão visual indevida e sem reabrir o acoplamento anterior do transporte ao shell principal:

1. Bloquear solicitação até endereço e todos os dados obrigatórios do transporte estarem completos.
2. Renomear os botões.
3. Colocar os botões lado a lado com texto compacto e quebra controlada.
4. Adicionar a frase instrutiva acima dos botões.
5. Impedir mais de uma solicitação de veículo para a mesma data.
6. Remover a lógica de container/cartões de histórico e mostrar apenas a última solicitação por opção de transporte no layout fixo solicitado.
7. Remover toda a lógica de `Ciência`.

## Arquivos-alvo esperados

- `sistema/app/static/check/index.html`
- `sistema/app/static/check/styles.css`
- `sistema/app/static/check/transport-screen.js`
- `sistema/app/static/check/app.js`
- `sistema/app/services/transport.py`
- `sistema/app/routers/web_check.py`
- `sistema/app/schemas.py`
- testes em `tests/` que cobrem transporte e contratos de fonte

## Decisões obrigatórias antes de codar

1. A validação de completude não pode ficar só no botão desabilitado. O frontend deve guiar a UX, mas o backend precisa rejeitar payload inconsistente.
2. A regra de unicidade por data não pode depender só do estado local do navegador. O backend precisa ser a fonte de verdade.
3. A remoção de `Ciência` deve ser end-to-end. Não basta esconder a seção; é preciso eliminar estados, renderização, ação HTTP e dependência de payload onde isso ainda controlar a tela.
4. A substituição do histórico por uma visão fixa por tipo de transporte deve manter legibilidade em mobile e não pode reintroduzir o problema de altura/scroll já tratado antes.
5. Como `app.js` ainda sustenta testes textuais, qualquer limpeza nele deve ser mínima e orientada a compatibilidade.

## Fase 1 - Consolidar o novo contrato de tela e regra de disponibilidade

### Objetivo

Definir exatamente quando a UI pode permitir uma nova solicitação e quais informações cada modalidade precisa para ficar apta.

### Checklist

- [x] Mapear no payload atual quais campos já existem para indicar endereço salvo, data solicitada, horário, modalidade e status da última solicitação.
- [x] Decidir a regra de completude de endereço no frontend e no backend.
- [x] Decidir a regra de completude por modalidade:
  - `regular`: endereço válido e seleção mínima de dias úteis.
  - `weekend`: endereço válido e seleção mínima de dias de fim de semana.
  - `extra`: endereço válido, data válida e horário válido.
- [x] Criar um helper central no módulo novo para responder algo como `canSubmitTransportRequest(kind)`.
- [x] Fazer o backend rejeitar requisições sem endereço completo ou sem os campos obrigatórios da modalidade.
- [x] Padronizar a mensagem de erro para cada bloqueio, evitando mensagens genéricas de falha de comunicação.

### Critério de aceite

1. O usuário não consegue acionar uma solicitação incompleta pela UI.
2. Mesmo que force o payload manualmente, a API rejeita a solicitação inconsistente com erro claro.

## Fase 2 - Ajustar a shell visual das opções de transporte

### Objetivo

Aplicar os ajustes de texto e layout da área principal de opções sem reintroduzir scroll ruim em mobile.

### Checklist

- [x] Alterar o texto dos botões conforme a nomenclatura final desejada pelo produto.
- [x] Inserir a frase instrutiva acima dos botões diretamente no HTML da tela de transporte.
- [x] Atualizar `styles.css` para deixar os botões lado a lado sempre que houver largura suficiente.
- [x] Definir largura mínima, quebra controlada e altura mínima para que o texto compacto continue legível em `320px`, `360px` e `393px`.
- [x] Garantir que a nova linha instrutiva não empurre elementos críticos para fora da dobra sem permitir scroll.
- [x] Revalidar o comportamento da variante compacta no modal de transporte, não só na shell principal.

### Critério de aceite

1. Os botões aparecem lado a lado nos cenários alvo.
2. O texto não estoura nem fica truncado de modo ilegível.
3. A frase instrutiva é visível e consistente com o fluxo.

## Fase 3 - Substituir o histórico por uma projeção fixa da última solicitação por modalidade

### Objetivo

Trocar o modelo atual baseado em lista/cartões por uma visualização fixa e mais previsível para cada tipo de transporte.

### Checklist

- [x] Remover do módulo a dependência da renderização baseada em `transport-request-card` e na lista histórica rolável.
- [x] Definir um modelo derivado do payload que selecione apenas a última solicitação relevante de cada modalidade.
- [x] Criar uma projeção explícita por modalidade:
  - `regular`
  - `weekend`
  - `extra`
- [x] Mostrar para cada modalidade apenas o bloco fixo da última solicitação aplicável, com status e dados principais.
- [x] Decidir como tratar modalidade sem solicitação ativa ou sem histórico relevante.
- [x] Remover também a lógica de swipe, dismiss local e detalhe em overlay se esses elementos deixarem de existir no layout novo.
- [x] Atualizar o CSS para o novo layout fixo, evitando dependência de altura flexível da lista antiga.

### Critério de aceite

1. Não existe mais lista histórica de cartões nem interação de swipe/dismiss.
2. Cada modalidade mostra apenas a informação final esperada, no layout fixo solicitado.

## Fase 4 - Impedir múltiplas solicitações de veículo para a mesma data

### Objetivo

Fechar a regra de unicidade por data tanto no fluxo da UI quanto na API.

Decisão aplicada: a unicidade vale entre quaisquer modalidades que projetem a mesma `service_date` ativa para o usuário.

### Checklist

- [x] Identificar no backend o ponto de criação da solicitação para aplicar a validação de unicidade.
- [x] Definir a chave da regra de conflito, no mínimo:
  - usuário/chave
  - data de serviço
  - status ainda relevante para bloqueio
- [x] Decidir se a unicidade vale entre todas as modalidades ou apenas nas modalidades que geram veículo para aquela data.
- [x] Implementar a rejeição no serviço com mensagem explícita.
- [x] Adicionar guarda otimista no frontend para bloquear submissão quando o estado carregado já indicar conflito na mesma data.
- [x] Garantir que o refresh do estado após criação/cancelamento mantenha a regra coerente.

### Critério de aceite

1. O backend impede a duplicidade mesmo com múltiplas abas ou requests manuais.
2. A UI mostra a restrição antes ou imediatamente após a tentativa, sem estado inconsistente.

## Fase 5 - Remover a lógica de `Ciência`

### Objetivo

Eliminar completamente o fluxo de confirmação de ciência que hoje participa do estado da tela.

Decisão aplicada: o webapp deixou de consumir `awareness_*` e `/api/web/transport/acknowledge`; o backend continua expondo esses campos e endpoint por compatibilidade com outros clientes e com o painel administrativo.

### Checklist

- [x] Remover do HTML a seção de `Ciência` e seus controles.
- [x] Remover do módulo o estado local relacionado, incluindo checkbox, botão e renderização condicional.
- [x] Remover o uso de `awarenessRequired` e `awarenessConfirmed` como elementos que controlam a UX da tela.
- [x] Revisar se o endpoint de `acknowledge` ainda precisa ser chamado pelo webapp; se não, remover o uso dele do frontend.
- [x] Avaliar se o backend ainda precisa expor os campos/endpoint por compatibilidade com outros clientes. Se precisar manter, documentar que o webapp deixou de depender disso.
- [x] Remover testes e contratos de fonte que só existiam por causa da `Ciência`.

### Critério de aceite

1. Não existe mais seção, ação ou estado de `Ciência` no fluxo web de transporte.
2. A tela continua funcional sem depender de acknowledgement manual.

## Fase 6 - Ajustar os testes para o novo contrato

### Objetivo

Migrar a cobertura automatizada do modelo antigo de histórico/cartões para o novo contrato da tela.

### Checklist

- [x] Atualizar os testes que hoje verificam a lista histórica e os cartões de transporte.
- [x] Remover asserções que dependem do botão `Realizado`, swipe, dismiss ou widget de detalhe se essas superfícies forem removidas.
- [x] Adicionar cobertura para:
  - bloqueio por endereço incompleto
  - bloqueio por campos obrigatórios faltantes
  - texto instrutivo novo
  - labels novos dos botões
  - layout lado a lado dos botões
  - unicidade por data
  - ausência de `Ciência`
- [x] Preservar, enquanto necessário, os contratos de fonte mínimos que ainda protegem a extração híbrida entre `app.js` e `transport-screen.js`.

### Critério de aceite

1. A suíte falha se alguém voltar a permitir solicitação incompleta.
2. A suíte falha se alguém reintroduzir duplicidade por data.
3. A suíte falha se alguém ressuscitar a UX de histórico/cartões ou `Ciência` sem intenção explícita.

## Ordem recomendada de implementação

1. Remover `Ciência` do módulo e do HTML.
2. Implementar o helper de completude de solicitação no módulo.
3. Implementar a validação de unicidade por data no backend.
4. Aplicar a guarda otimista correspondente no frontend.
5. Refazer a shell visual dos botões e o texto instrutivo.
6. Trocar a projeção de histórico por visão fixa por modalidade.
7. Atualizar os testes de transporte para o novo contrato.

## Riscos principais

1. Tentar resolver a duplicidade só no frontend vai falhar em cenários com refresh tardio, múltiplas abas ou requests paralelos.
2. Remover o histórico sem antes decidir a projeção fixa por modalidade tende a gerar regressão de legibilidade ou perda de contexto operacional.
3. Remover `Ciência` só visualmente pode deixar estados mortos e branches inconsistentes no módulo.
4. Alterar `app.js` além do mínimo necessário pode quebrar testes baseados em grep sem ganho funcional real.

## Critério final de conclusão

O trabalho só pode ser considerado concluído quando:

1. A tela só permite solicitação válida e completa.
2. A API impede duplicidade de solicitação para a mesma data.
3. Os botões e o texto da shell seguem a UX nova pedida.
4. Não existe mais histórico em cartões nem fluxo de `Ciência` no webapp.
5. Os testes específicos do transporte refletem o novo contrato e passam.