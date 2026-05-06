# To-do list robusta para corrigir o comportamento da Checking Web no Samsung Galaxy S21 sem alterar o layout correto do iPhone 14 Pro

## Prompt para o agente de IA

Você vai corrigir um problema da aplicação web `Checking Web`, localizada em `sistema/app/static/check`, com foco em preservar o comportamento já aprovado no iPhone 14 Pro e resolver o problema observado no Samsung Galaxy S21 no Chrome.

Há dois sintomas que precisam ser tratados como separados até prova em contrário:

1. O layout mostrado no Samsung está diferente do iPhone, mas não aparenta estar aleatoriamente "espremido" ou quebrado; ele parece estar entrando em uma variante mais empilhada da interface.
2. O sintoma mais crítico é que o usuário do Samsung não conseguiu deslizar a tela para cima e para baixo para acessar todas as opções da página. Ou seja, existe suspeita de bloqueio ou falha de scroll vertical na tela principal.

Trabalhe com extrema cautela, faça mudanças mínimas e orientadas por evidência, preserve o layout aprovado no iPhone e não introduza hacks por dispositivo, `userAgent sniffing` ou mudanças desnecessárias em JavaScript se o problema puder ser resolvido com a menor correção correta.

## 0. Diagnóstico revisado no código atual e lacunas ainda abertas

1. O HTML já usa um `meta viewport` adequado em `sistema/app/static/check/index.html` com `width=device-width`, `initial-scale=1`, `minimum-scale=1`, `viewport-fit=cover` e `shrink-to-fit=no`. Não há evidência, até aqui, de que exista alguma opção do navegador Samsung/Chrome que precise ser marcada para "ativar" o layout correto.
2. O CSS atual possui um breakpoint estrutural em `@media (max-width: 360px)` dentro de `sistema/app/static/check/styles.css`.
3. Esse breakpoint altera exatamente blocos que explicam a diferença visual entre as capturas:
   - `.history-grid` passa para `grid-template-columns: 1fr`
   - `.auth-credentials-row` passa para `grid-template-columns: 1fr`
   - `.choice-grid.two-columns` passa para `grid-template-columns: 1fr`
4. O Samsung Galaxy S21 em portrait no Chrome normalmente expõe largura lógica em torno de `360 CSS px`, então ele tende a cair exatamente nesse breakpoint. O iPhone 14 Pro em portrait costuma expor largura lógica maior, em torno de `393 CSS px`, então não cai nesse mesmo breakpoint.
5. Isso explica bem a diferença de composição visual entre as capturas, mas não explica sozinho o relato de que o usuário não conseguiu rolar a página para alcançar o restante do fluxo.
6. No código atual, não há evidência óbvia de bloqueio de scroll via JavaScript global no `body`, como `body.style.overflow = 'hidden'`, `position: fixed` aplicado dinamicamente na shell principal, ou listeners globais de `touchmove` e `wheel` com `preventDefault()` bloqueando a página inteira.
7. Mesmo assim, existe uma combinação no CSS e no contrato de viewport que precisa ser investigada com cuidado no Android Chrome:
   - `html` e `body` usam `overscroll-behavior: none`
   - `body` usa `touch-action: manipulation`
   - a shell depende de `--app-viewport-height` e `--app-header-height`
   - `body` e `.check-shell` usam `min-height` baseado no viewport dinâmico
   - dialogs e overlays usam superfícies `position: fixed`
8. Há também diferenças de estado da própria aplicação que podem alterar o que aparece ou desaparece na tela, por exemplo `Projeto`, `Local` e `Informe`, então nem toda diferença entre capturas deve ser atribuída automaticamente ao CSS responsivo sem comparar o estado da UI.
9. A hipótese visual forte continua sendo: o Samsung está entrando na variante de `360px` e, por isso, a tela fica mais empilhada que no iPhone.
10. A hipótese funcional mais importante agora é: existe um problema de scroll vertical ou de contrato de altura útil no Samsung, fazendo a tela parecer "travada" e impedindo acesso aos elementos abaixo da dobra.
11. Essas duas hipóteses devem ser investigadas separadamente. Não assuma mais que o breakpoint de `360px` seja a causa única do problema.

## 1. Resultado esperado

1. No Samsung Galaxy S21 em portrait no Chrome, o usuário deve conseguir acessar toda a tela principal da Checking Web sem ficar preso na dobra atual.
2. Se o conteúdo exceder a altura visível, o scroll vertical da página principal deve funcionar normalmente e de forma previsível.
3. Se houver espaço real para uma composição mais próxima do iPhone, a interface do Samsung pode ser aproximada visualmente do layout aprovado; porém acessibilidade e scroll correto têm prioridade sobre tentar forçar geometria idêntica entre `360px` e `393px`.
4. O iPhone 14 Pro não pode sofrer alteração perceptível de layout nesta correção.
5. Dispositivos realmente mais estreitos devem continuar tendo fallback compacto quando isso for necessário.
6. O comportamento de viewport dinâmico, teclado, dialogs e tela de transporte não pode regredir.

## 2. Decisões obrigatórias antes de codar

1. Trate o relato de scroll travado como prioridade `P0` desta investigação.
2. Trate a diferença visual entre Samsung e iPhone como um segundo eixo de análise, não como prova suficiente de causa raiz.
3. Não tente resolver isso com configuração manual de navegador, sugestão de "versão desktop", flag de Chrome ou workaround operacional no aparelho. A correção deve ficar no código.
4. Não introduza `userAgent sniffing`, classes específicas para Samsung, Android ou iPhone, nem lógica JS baseada em identificação de dispositivo.
5. Preserve o `meta viewport` atual, a sincronização de `--app-viewport-height`, `--app-viewport-width` e `--app-header-height`, e a lógica de `orientationchange`, a menos que uma evidência concreta mostre que esses trechos participam do defeito.
6. Antes de mexer no breakpoint de `360px`, confirme se o problema crítico de Samsung é realmente o empilhamento ou se o defeito principal é a falha de scroll.
7. Separe conceitualmente estes problemas:
   - variante visual mais compacta em `360px`
   - impossibilidade de rolar a tela principal e chegar às opções abaixo
8. Não force, por princípio, que `360px` reproduza exatamente a mesma composição de `393px` se isso piorar usabilidade. Primeiro garanta acesso a toda a interface; depois, refine a composição visual.

## 3. Fase 1 - Reproduzir com precisão os dois sintomas

### Objetivo

Reproduzir e distinguir claramente o que é diferença de breakpoint e o que é falha de scroll no Samsung.

### Checklist

- [ ] Comparar as capturas aprovadas e problemáticas e registrar explicitamente o que mudou em cada uma.
- [ ] Confirmar quais blocos da tela estão simplesmente abaixo da dobra no Samsung e quais estão realmente ausentes ou ocultos.
- [ ] Verificar o estado funcional da tela nas capturas, incluindo:
  - se `Atividades Automáticas` está habilitado
  - se `Projeto`, `Local` ou `Informe` estão ocultos por regra de negócio e não por layout
  - se a tela está autenticada ou parcialmente autenticada
- [ ] Validar a largura lógica alvo de pelo menos estes cenários:
  - `360 x 800` ou equivalente para simular Galaxy S21 portrait
  - `393 x 852` ou equivalente para simular iPhone 14 Pro portrait
  - `320 x 700` ou equivalente para representar aparelho realmente estreito
- [ ] Medir nesses cenários:
  - `window.innerWidth`
  - `window.innerHeight`
  - `visualViewport.width`
  - `visualViewport.height`
  - `document.documentElement.scrollHeight`
  - `document.documentElement.clientHeight`
  - `document.body.scrollHeight`
  - `document.body.clientHeight`
- [ ] Registrar o estado computado de:
  - `overflow-y` de `html`, `body`, `.check-shell`, `.check-card`
  - `touch-action` de `body` e superfícies principais
  - `overscroll-behavior` de `html` e `body`
- [ ] Confirmar separadamente:
  - se o Samsung cai mesmo no breakpoint `max-width: 360px`
  - se existe conteúdo abaixo da dobra que deveria estar acessível por scroll
  - se o scroll realmente não acontece no device problemático
- [ ] Se a falha não for reproduzível em emulação de desktop, documentar isso e exigir validação adicional em Android real ou remota antes de consolidar a correção.

### Critério de aceite

1. Você consegue responder com precisão se o problema principal é `scroll travado`, `breakpoint agressivo`, ou ambos.
2. Você consegue distinguir diferença de estado da UI de diferença real de layout responsivo.

## 4. Fase 2 - Isolar a causa do travamento de scroll vertical

### Objetivo

Garantir que a tela principal do `/user` possa sempre ser rolada verticalmente quando houver conteúdo além da altura visível.

### Checklist de investigação e correção

- [ ] Auditar `html`, `body`, `.check-shell`, `.check-card` e `.check-form` em `sistema/app/static/check/styles.css` para entender o contrato real de altura e rolagem.
- [ ] Confirmar que a shell principal não está ficando presa em uma altura incorreta por conta de `--app-viewport-height` ou `--app-header-height` no Android Chrome.
- [ ] Revisar a interação entre:
  - `min-height: var(--app-viewport-height)` no `body`
  - `min-height: calc(var(--app-viewport-height) - var(--app-header-height))` em `.check-shell`
  - `display: flex` do `body`
  - `display: flex` da shell
- [ ] Verificar se `overscroll-behavior: none` em `html` e `body` está contribuindo para a percepção de tela travada no Android Chrome.
- [ ] Verificar se `touch-action: manipulation` aplicado no `body` deve ser removido do container raiz e mantido apenas em controles interativos, caso ele esteja interferindo na rolagem do device alvo.
- [ ] Confirmar que não existe backdrop invisível, overlay ou elemento fixo ocupando a tela e capturando interação mesmo quando marcado como oculto.
- [ ] Confirmar que os dialogs e a tela de transporte não deixam nenhum estado residual que interfira na rolagem da página principal após fechar.
- [ ] Caso necessário, ajustar o contrato de scroll para que a página principal role no nível correto, sem reintroduzir scroll horizontal ou bloqueios em dialogs.
- [ ] Preservar o comportamento correto do iPhone e das demais superfícies.

### Critério de aceite

1. Em Samsung Galaxy S21 portrait, o usuário consegue deslizar verticalmente a tela principal e acessar todas as opções abaixo da dobra.
2. A página principal não fica mais com sensação de tela "travada".

## 5. Fase 3 - Reavaliar a diferença visual após corrigir o scroll

### Objetivo

Depois que o scroll vertical estiver correto, decidir se a variante visual de `360px` ainda precisa ser refinada ou se ela já é aceitável.

### Checklist de implementação visual

- [ ] Revalidar a captura do Samsung após a correção de scroll.
- [ ] Confirmar se o visual ainda é considerado incompatível com o baseline aprovado do iPhone ou se o defeito principal já foi resolvido.
- [ ] Se a diferença visual ainda for considerada inadequada, revisar o breakpoint `@media (max-width: 360px)` e separar o que é:
  - compactação legítima para telas estreitas
  - colapso estrutural agressivo demais
- [ ] Só então avaliar mover para um limiar menor, se a validação confirmar, os colapsos abaixo:
  - `.history-grid { grid-template-columns: 1fr; }`
  - `.auth-credentials-row { grid-template-columns: 1fr; }`
  - `.choice-grid.two-columns { grid-template-columns: 1fr; }`
- [ ] Avaliar alternativas menos bruscas para a faixa de `360px`, por exemplo:
  - manter o histórico em duas colunas se houver legibilidade
  - usar uma linha de autenticação mais compacta sem empilhar tudo
  - reduzir gaps e paddings antes de colapsar a estrutura
- [ ] Não alterar a organização aprovada do iPhone 14 Pro.
- [ ] Não tocar em desktop ou landscape fora do necessário.

### Critério de aceite

1. O Samsung deixa de apresentar uma composição considerada inadequada pelo baseline visual do produto.
2. O iPhone continua igual ao layout já aprovado.
3. O fallback para telas realmente estreitas continua existindo.

## 6. Fase 4 - Revisar regressões em componentes adjacentes

### Objetivo

Garantir que a correção do scroll e, se necessário, do breakpoint não quebre outras superfícies móveis da mesma aplicação.

### Checklist

- [ ] Verificar se `dialogs` de senha e cadastro continuam funcionando corretamente.
- [ ] Verificar se a tela de transporte (`transport-screen`) não sofreu regressão com a mudança.
- [ ] Verificar se o breakpoint de paisagem com baixa altura em `@media (orientation: landscape) and (max-height: 540px)` continua coerente.
- [ ] Garantir que a correção não reintroduza scroll horizontal no `body`, `.check-shell`, `.check-card` ou listas internas.
- [ ] Confirmar que `input`, `select` e botões continuam com `font-size: 16px` nos contextos onde isso evita zoom indesejado em mobile.
- [ ] Verificar que a atualização não afeta a experiência de teclado virtual nem a medição dinâmica de viewport.

### Critério de aceite

1. A correção do shell principal não quebra dialogs, overlay de transporte, landscape de baixa altura ou scroll móvel.

## 7. Fase 5 - Atualizar e endurecer os testes automatizados

### Objetivo

Transformar esse caso do Samsung em regressão coberta por teste, tanto para scroll quanto para layout responsivo.

### Checklist

- [ ] Atualizar `tests/check_responsive_layout.test.js` para refletir o novo contrato responsivo.
- [ ] Adicionar cobertura explícita para o contrato de scroll da tela principal, validando pelo menos que:
  - `html` e `body` continuam com `overflow-y: auto`
  - `.check-shell` não é convertida em superfície fixa com bloqueio de rolagem
  - não existe lógica nova de bloqueio global de scroll introduzida no JS
- [ ] Se a solução ajustar `touch-action` ou `overscroll-behavior`, registrar esse contrato em teste para evitar regressão futura.
- [ ] Se a solução ajustar o breakpoint de `360px`, adicionar cobertura para o novo limiar estrutural adotado.
- [ ] Adicionar asserções que garantam que o layout aprovado do iPhone não perdeu seus breakpoints atuais úteis (`480px`, `1024px`, `1180px`, etc.).
- [ ] Verificar se algum teste existente depende implicitamente do breakpoint atual e ajustar apenas o que for necessário.

### Critério de aceite

1. A suíte automatizada falha se alguém reintroduzir bloqueio de scroll no `/user`.
2. A suíte automatizada falha se alguém voltar a aplicar um colapso estrutural indevido na faixa corrigida.
3. A suíte continua protegendo viewport dinâmico, shell principal e layout landscape já existentes.

## 8. Fase 6 - Validação manual obrigatória

### Objetivo

Homologar visualmente e funcionalmente os mesmos cenários que hoje diferenciam Samsung e iPhone.

### Checklist

- [ ] Validar manualmente em Samsung Galaxy S21 portrait no Chrome, ou em device equivalente com mesma largura lógica e comportamento de touch.
- [ ] Validar manualmente em iPhone 14 Pro portrait no Safari e, se possível, também no Chrome iOS do fluxo já aprovado.
- [ ] Validar manualmente em uma largura realmente estreita, próxima de `320px`.
- [ ] Confirmar no Samsung:
  - que a tela pode ser deslizada para cima e para baixo normalmente
  - que o usuário consegue alcançar `Atividades Automáticas`, `Registro`, botões de ação e demais controles abaixo da dobra
  - que não há camada invisível bloqueando toque ou scroll
- [ ] Confirmar visualmente:
  - ausência de overflow horizontal
  - histórico coerente
  - linha `Chave / Senha / botão Senha` coerente para a largura disponível
  - botão `Registrar` preservado e legível
  - labels e inputs sem truncamento feio
- [ ] Validar com teclado aberto em pelo menos um fluxo de foco nos campos `Chave` e `Senha`.
- [ ] Validar a tela de transporte e os dialogs após a mudança.
- [ ] Se possível, comparar antes e depois com capturas equivalentes.

### Critério de aceite

1. O Samsung Galaxy S21 deixa de apresentar tela travada para scroll.
2. O Samsung, após isso, fica visualmente aceitável e alinhado com a direção aprovada do produto.
3. O iPhone 14 Pro permanece visualmente igual ao baseline aprovado.

## 9. Restrições que não podem ser violadas

1. Não mexer no `meta viewport` para tentar forçar o Samsung a se comportar como iPhone sem evidência real.
2. Não usar detecção de dispositivo, marca ou navegador.
3. Não alterar o layout do iPhone 14 Pro sem necessidade objetiva.
4. Não ampliar escopo para redesign visual completo da tela.
5. Não alterar a lógica de viewport em JS sem prova de que ela participa do defeito.
6. Não aceitar como solução pedir ao usuário para alterar configuração do navegador ou do sistema operacional.
7. Não introduzir regressão em landscape, dialogs ou transporte.

## 10. Hipótese de solução recomendada

Use como hipótese principal de implementação a estratégia abaixo, validando antes de consolidar:

1. Tratar primeiro o problema de scroll vertical no Samsung.
2. Investigar como candidatos principais para esse defeito:
   - contrato de altura do `body` e da `.check-shell`
   - combinação de `overflow-y`, `overscroll-behavior` e `touch-action` nas superfícies raiz
   - possível interação residual de overlays fixos
3. Somente depois reavaliar se o breakpoint `@media (max-width: 360px)` precisa ser suavizado.
4. Se o scroll correto por si só já resolver a usabilidade e tornar a variante de `360px` aceitável, evitar mexer no breakpoint sem necessidade.
5. Se a variante visual ainda for inadequada depois do scroll corrigido, transformar o breakpoint de `360px` em algo menos agressivo, sem tocar no iPhone.

## 11. Definição de pronto

Considere a tarefa concluída apenas quando todos os itens abaixo forem verdadeiros:

1. Foi confirmado, com evidência, se o problema principal era scroll travado, breakpoint agressivo ou ambos.
2. O Samsung Galaxy S21 em portrait deixa de prender o usuário sem acesso às opções abaixo da dobra.
3. Se necessário, a composição visual do Samsung foi refinada sem regressão no iPhone 14 Pro.
4. O fallback para aparelhos realmente estreitos continua existindo.
5. Dialogs, transporte, landscape e viewport dinâmico continuam funcionando.
6. Os testes foram atualizados para proteger o novo contrato de scroll e de responsividade.
7. A validação manual final confirma o comportamento esperado nos cenários-chave.