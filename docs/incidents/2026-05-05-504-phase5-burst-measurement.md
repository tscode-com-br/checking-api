# Medicao antes/depois da reducao de burst da SPA de check - Fase 5 - incidente 504 de 2026-05-05

## 1. Objetivo executado

Medir quantitativamente a queda de requests por usuario na SPA de check, comparando:

1. o baseline anterior da superficie, servido a partir de `HEAD` de `sistema/app/static/check/app.js`;
2. o estado atual do working tree com as reducoes de burst de autenticacao, lifecycle e localizacao.

## 2. Metodo de medicao

Foi usada uma homologacao local em browser real com Playwright, subindo a API preview em SQLite e servindo o mesmo backend para os dois lados da comparacao.

O `before` e o `after` diferem apenas no `app.js` carregado pelo browser:

1. `before_head`: `HEAD:sistema/app/static/check/app.js`, interceptado no carregamento da pagina;
2. `after_worktree`: `sistema/app/static/check/app.js` atual do workspace.

Cada cenario roda com usuario proprio, seed proprio e janela de contagem limitada ao gesto medido. Requests de seed, healthcheck e bootstrap administrativo ficaram fora da contagem.

## 3. Arquivos gerados

1. `scripts/homologate_temp_010_phase5_burst_measurement.py`
2. `docs/temp_010_phase5_burst_measurement_report.json`
3. `docs/incidents/2026-05-05-504-phase5-burst-measurement.md`

## 4. Comandos executados

1. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/homologate_temp_010_phase5_burst_measurement.py --scenario open_qr_code --variant before_head`
2. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/homologate_temp_010_phase5_burst_measurement.py --scenario switch_tabs`
3. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/homologate_temp_010_phase5_burst_measurement.py --scenario grant_location`
4. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/homologate_temp_010_phase5_burst_measurement.py --scenario submit_checkin_checkout --variant before_head`
5. `c:/dev/projetos/checkcheck/.venv/Scripts/python.exe scripts/homologate_temp_010_phase5_burst_measurement.py`

## 5. Definicao operacional dos cenarios

Para evitar leitura ambigua dos nomes, esta execucao considerou:

1. Abrir o QR Code: abrir a pagina com chave, senha e configuracoes persistidas, com GPS ja concedido.
2. Autenticar: abrir a pagina sem credenciais preenchidas e digitar a senha com pausas maiores que o debounce antigo.
3. Voltar da tela bloqueada: abrir a pagina com a chave persistida, manter a shell bloqueada e destravar explicitamente por `Enter`.
4. Alternar abas: disparar o cluster de retorno de UI (`visibility` + `focus` + `pageshow`) dentro da janela curta de reuso.
5. Conceder localizacao: iniciar autenticado com GPS negado, conceder permissao depois e disparar um lifecycle de retorno de UI.
6. Registrar check-in/check-out: executar dois submits manuais sequenciais na mesma sessao autenticada.

## 6. Resultado consolidado

Total agregado nos seis cenarios medidos:

1. antes: `36` requests;
2. depois: `23` requests;
3. alivio total: `13` requests a menos;
4. reducao agregada: `36,1%`.

## 7. Matriz antes/depois por cenario

| Cenario | Usuario | Antes | Depois | Alivio | Endpoints mais aliviados |
| --- | --- | ---: | ---: | ---: | --- |
| Abrir o QR Code | `QRA1` | 9 | 8 | 1 | `GET /api/web/check/state` `-1` |
| Autenticar | `AU02` | 12 | 6 | 6 | `POST /api/web/auth/login` `-5`, `GET /api/web/check/state` `-1` |
| Voltar da tela bloqueada | `LK03` | 6 | 5 | 1 | `GET /api/web/check/state` `-1` |
| Alternar abas | `TB04` | 3 | 0 | 3 | `GET /api/web/check/state` `-2`, `POST /api/web/check/location` `-1` |
| Conceder localizacao | `GP05` | 2 | 1 | 1 | `GET /api/web/check/state` `-1` |
| Registrar check-in/check-out | `SB06` | 4 | 3 | 1 | `POST /api/web/check/location` `-1` |

## 8. Endpoints mais aliviados no agregado

1. `GET /api/web/check/state`: `-6` requests
2. `POST /api/web/auth/login`: `-5` requests
3. `POST /api/web/check/location`: `-2` requests

Leitura objetiva:

1. o maior alivio estrutural saiu de `GET /api/web/check/state`, confirmando que o segundo `state` do lifecycle e o reuso de state recente eram um multiplicador real;
2. o maior alivio concentrado num unico fluxo saiu de `POST /api/web/auth/login`, puxado pelo cenario de autenticacao com digitacao pausada;
3. `POST /api/web/check/location` caiu menos no agregado, mas zerou completamente no retorno de abas e caiu no submit manual por causa do reuso da localizacao recente.

## 9. Validacao executada

A harness foi validada incrementalmente antes da coleta final:

1. prova de troca do `app.js` baseline contra o backend atual;
2. prova isolada de `switch_tabs`, confirmando `3 -> 0` requests;
3. prova isolada de `grant_location`, confirmando `2 -> 1` requests;
4. prova isolada do submit manual baseline, confirmando `POST /api/web/check/location` repetido no fluxo antigo.

O artefato bruto final desta medicao ficou em `docs/temp_010_phase5_burst_measurement_report.json`.

## 10. Observacoes e limites

1. Esta e uma medicao local de browser real contra preview local; ela comprova o comportamento da SPA, nao a latencia ou o custo em host produtivo.
2. O baseline servido de `HEAD` apresentou mojibake em alguns textos de UI durante a interceptacao do script, mas as contagens HTTP nao foram afetadas.
3. O cenario de concessao de localizacao ficou com `automaticChecked = false` nos dois lados porque a UI mantem o toggle automatico desligado quando o GPS inicia negado; ainda assim a medicao continuou valida para o lifecycle de concessao.

## 11. Resultado

Aprovado.

Houve queda material de requests por usuario e por fluxo de uso. O hotspot mais aliviado no agregado foi `GET /api/web/check/state`, e o maior alivio pontual de autenticacao ficou no cenario `Autenticar`, com `5` `POST /api/web/auth/login` a menos no mesmo gesto de usuario.

## 12. Rollback

Esta execucao nao altera o runtime do produto. Para remover apenas a instrumentacao desta etapa, basta reverter:

1. `scripts/homologate_temp_010_phase5_burst_measurement.py`
2. `docs/temp_010_phase5_burst_measurement_report.json`
3. `docs/incidents/2026-05-05-504-phase5-burst-measurement.md`

## 13. Proximo passo recomendado

Usar este resultado como criterio de entrada da Fase 6, priorizando agora os hot paths backend mais pressionados pelo bootstrap residual da SPA:

1. `GET /api/web/check/state`
2. `POST /api/web/auth/login`
3. `POST /api/web/check/location`