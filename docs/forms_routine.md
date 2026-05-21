# Rotina de preenchimento do Microsoft Forms

Status deste documento: mapeado a partir do codigo atual do repositorio em 2026-05-21.

Escopo estudado:

- `sistema/app`
- `sistema/app/static/check`
- `assets/xpath`
- `tests/test_api_flow.py`

Objetivo deste documento:

- explicar como a atividade do usuario vira, ou nao, um novo envio ao Microsoft Forms;
- explicar como o web check monta o payload que chega na API;
- explicar como a API persiste a fila e como o worker Playwright preenche o formulario real;
- registrar os pontos operacionais que hoje podem afetar a percepcao de confiabilidade do sistema.

## 1. Resumo executivo

Hoje o usuario nao preenche o Microsoft Forms diretamente pelo navegador do check web nem pelo app mobile. O fluxo real e este:

1. o canal de origem envia uma atividade para a API;
2. a API normaliza a atividade, atualiza o estado local do usuario e decide se aquilo merece novo envio ao Forms;
3. quando merece, a API grava uma linha em `forms_submissions` e responde ao cliente sem esperar o Forms terminar;
4. um worker separado consome a fila, abre o Microsoft Forms via Playwright/Chromium e executa o preenchimento real;
5. o resultado final fica refletido em `forms_submissions`, `check_events` e nos diagnosticos da fila.

Consequencia pratica importante:

- para web, mobile e RFID, a resposta positiva imediata normalmente significa `atividade aceita` ou `atividade aceita e enfileirada`;
- ela nao significa, por si so, que o Microsoft Forms ja confirmou o envio com sucesso.

## 2. Arquivos-chave

| Arquivo | Papel no fluxo |
| --- | --- |
| `sistema/app/services/forms_submit.py` | Helper central de submissao logica para web/mobile com `informe`, deduplicacao e enfileiramento |
| `sistema/app/services/forms_queue.py` | Fila persistida, reserva de itens, processamento e diagnosticos do worker |
| `sistema/app/services/forms_worker.py` | Preenchimento real do Microsoft Forms com Playwright |
| `sistema/app/services/user_sync.py` | Regra que decide quando uma atividade gera novo Forms ou apenas atualiza estado local |
| `sistema/app/routers/web_check.py` | Endpoints web, inclusive `POST /api/web/check` |
| `sistema/app/routers/mobile.py` | Endpoints mobile, inclusive `POST /api/mobile/events/forms-submit` |
| `sistema/app/routers/device.py` | Endpoint RFID `POST /api/scan` |
| `sistema/app/static/check/app.js` | Montagem do payload do web check manual e automatico |
| `sistema/app/static/check/automatic-activities.js` | Regras de check-in/check-out automaticos baseados em localizacao |
| `sistema/app/models.py` | Modelo `FormsSubmission` |
| `sistema/app/core/config.py` | URL do Forms e limites operacionais |
| `assets/xpath/*` | Seletores usados pelo Playwright para preencher o formulario |

## 3. URL de destino e configuracao operacional

O destino atual do preenchimento esta em `settings.forms_url`:

```text
https://forms.office.com/Pages/ResponsePage.aspx?id=QWJvW1ea5EuOUB36cueaV-4C0XpFTa1LmJM_FjZpp4pUOTFGR1QwSk00Vk5KQ0ExNUMzQldRSkpHWCQlQCN0PWcu&origin=QRCode
```

Parametros operacionais relevantes em `sistema/app/core/config.py`:

- `forms_timeout_seconds = 30`
- `forms_max_retries = 3`
- `forms_queue_enabled = True`
- `forms_worker_health_update_seconds = 5`
- `forms_worker_health_stale_seconds = 20`
- `forms_worker_unhealthy_consecutive_errors = 3`
- `tz_name = "Asia/Singapore"`

## 4. Canais que podem gerar preenchimento do Forms

### 4.1 Web check

Endpoint:

- `POST /api/web/check`

Fluxo de entrada:

- o front web monta um JSON e envia para `/api/web/check`;
- a rota valida sessao web, valida o projeto ativo contra os memberships do usuario e rejeita local nao operacional conhecido;
- depois chama `submit_forms_event(...)`.

Contrato de request do web check:

```json
{
  "chave": "WB12",
  "projeto": "P83",
  "action": "checkout",
  "local": "Web",
  "informe": "retroativo",
  "event_time": "2026-05-21T10:11:12.000Z",
  "client_event_id": "web-check-1747821234567-ab12cd34"
}
```

Contrato de response:

```json
{
  "ok": true,
  "duplicate": false,
  "queued_forms": true,
  "worker_healthy": true,
  "message": "Web check event accepted and queued for Forms submission",
  "state": {
    "found": true,
    "chave": "WB12",
    "nome": "Oriundo da Web",
    "projeto": "P83",
    "current_action": "checkout",
    "current_event_time": "2026-05-21T18:11:12+08:00",
    "current_local": "Web",
    "last_checkin_at": null,
    "last_checkout_at": "2026-05-21T18:11:12+08:00"
  }
}
```

Observacao importante:

- o front do web check hoje nao consome `queued_forms` nem `worker_healthy` para diferenciar `enfileirado` de `realmente enviado`.

### 4.2 Mobile com `forms-submit`

Endpoint:

- `POST /api/mobile/events/forms-submit`

Fluxo:

- reaproveita exatamente o mesmo helper `submit_forms_event(...)` usado pelo web check;
- a diferenca principal esta no canal (`android_forms`) e no `device_id` (`android-app`).

### 4.3 Mobile legado sem `informe`

Endpoint:

- `POST /api/mobile/events/submit`

Fluxo:

- e uma rota mais antiga;
- nao usa `submit_forms_event(...)`;
- ainda decide se enfileira novo Forms, mas sempre com `ontime=True` porque nao recebe `informe`.

### 4.4 RFID / ESP32

Endpoint:

- `POST /api/scan`

Fluxo:

- valida `shared_key` do dispositivo;
- busca o usuario pelo RFID;
- usa `now_sgt()` como horario da atividade;
- decide se precisa enfileirar o Forms;
- responde ao dispositivo sem esperar o Playwright terminar.

Diferenca importante em relacao a web/mobile:

- o RFID tem uma guarda extra: `checkout` sem atividade anterior valida e bloqueado;
- web/mobile nao tem essa guarda explicita no helper compartilhado.

## 5. Como o web check monta a atividade

### 5.1 Defaults visiveis no HTML

No `sistema/app/static/check/index.html`:

- a acao padrao selecionada e `checkin`;
- o `informe` padrao selecionado e `normal`;
- o submit vai para `/api/web/check`;
- o estado vem de `/api/web/check/state`;
- as localizacoes vem de `/api/web/check/locations`;
- a resolucao de localizacao usa `/api/web/check/location`.

### 5.2 Campos enviados pelo submit manual

No `form.addEventListener('submit', ...)` em `app.js`, o front envia:

- `chave`: valor sanitizado para 4 caracteres alfanumericos;
- `projeto`: `resolveCommittedProjectValue()`;
- `action`: radio selecionado (`checkin` ou `checkout`);
- `local`: local final submittable resolvido pela UI;
- `informe`: `getSelectedInformeValue()`;
- `event_time`: `new Date().toISOString()`;
- `client_event_id`: `web-check-${Date.now()}-${random}`.

### 5.3 Como o front resolve o `local`

Regras do `app.js`:

- se o submit manual permite selecao manual, `resolveSubmittedLocationValue()` usa `manualLocationSelect.value`;
- caso contrario, usa a localizacao operacional reconhecida por GPS (`resolveMatchedOperationalLocation(currentLocationMatch)`);
- `resolveFinalSubmittableLocationValue(...)` recusa:
  - valor vazio;
  - `Localização não Cadastrada`;
  - `Precisao Insuficiente`.

No backend, a rota web ainda faz uma guarda adicional e rejeita explicitamente `Localização não Cadastrada`.

### 5.4 Como o front trata `informe`

Regra central em `app.js`:

```js
function getSelectedInformeValue() {
  return isAutomaticActivitiesEnabled() ? 'normal' : getSelectedValue('informe');
}
```

Consequencia:

- submit manual com atividades automaticas desligadas respeita a escolha do usuario (`normal` ou `retroativo`);
- submit automatico sempre envia `normal`, mesmo que o radio visual esteja em `retroativo`.

### 5.5 Quando o submit manual e bloqueado pelo front

O front cancela o submit manual quando:

- a chave nao tem 4 caracteres validos;
- a sessao/autenticacao ainda nao esta liberada;
- faltou local manual quando a UI exige escolha manual;
- as atividades automaticas estao habilitadas e nao ha fallback manual por precisao baixa.

### 5.6 Automatic activities

O front tambem pode disparar submit automatico sem clique no botao principal. O caminho e:

- `runAutomaticActivitiesIfNeeded(...)`
- `submitAutomaticActivity(...)`

Casos atuais:

1. localizacao reconhecida como area operacional:
   - decide `checkin` ou `checkout` conforme `resolveAutomaticLocationAction(...)`;
   - em `Zona Mista`, a decisao alterna com base na ultima atividade gravada.

2. usuario fora do local de trabalho:
   - se o ultimo estado gravado e `checkin`, dispara `checkout` automatico;
   - o `local` enviado vira `Fora do Local de Trabalho`.

3. localizacao nao cadastrada:
   - o helper existe, mas hoje `shouldAttemptAutomaticNearbyWorkplaceCheckIn(...)` retorna sempre `false`;
   - na pratica, esse caminho nao gera check-in automatico.

### 5.7 Atualizacao de localizacao antes do submit

`ensureLocationReadyForSubmit()` tenta reaproveitar uma leitura recente de GPS. Se nao houver leitura recente:

- consulta o estado da permissao de localizacao;
- se houver chance de lookup silencioso, tenta capturar/confirmar localizacao antes do submit.

Isso significa que o web check tenta melhorar o contexto de local antes de mandar a atividade para a API, mas ainda assim a atividade aceita pela API pode terminar apenas enfileirada, nao concluida no Forms.

## 6. Regra da API: quando uma atividade vira novo Forms

O ponto central esta em `sistema/app/services/user_sync.py`:

```python
def should_enqueue_forms_for_action(latest_activity, action, event_time, timezone_name=None):
    if latest_activity is None:
        return True

    return latest_activity.action != action or not is_same_project_day(
        latest_activity.event_time,
        event_time,
        timezone_name=timezone_name,
    )
```

Em portugues claro:

- se nao existe atividade anterior relevante, a API enfileira novo Forms;
- se a nova atividade tem acao diferente da ultima, a API enfileira novo Forms;
- se a nova atividade tem a mesma acao, mas em outro dia do projeto, a API enfileira novo Forms;
- se a nova atividade repete a mesma acao no mesmo dia do projeto, a API nao envia novo Forms e apenas atualiza o estado local/historico interno.

### 6.1 Qual timezone conta para a regra diaria

O helper usa o timezone do projeto (`resolve_project_timezone_name(...)`). Logo:

- a comparacao de dia nao e "dia do navegador";
- nao e simplesmente UTC;
- e o dia local do projeto envolvido na atividade.

### 6.2 O que entra como `latest_activity`

Para a decisao interna, a API usa `resolve_latest_internal_user_activity(...)`.

Esse resolvedor:

- ignora sync events com source `provider`;
- ignora sync events com source `state_import`;
- ignora `check_events` com source `provider`;
- se o estado atual do usuario estiver "backed" por provider, tambem deixa de usar o current state para esta decisao.

Consequencia pratica:

- o provider nao deve suprimir um novo Forms interno de web/mobile/RFID nesta decisao especifica;
- a supressao da fila e guiada pelas atividades internas relevantes do proprio sistema.

## 7. O helper compartilhado `submit_forms_event(...)`

O caminho web/mobile com `informe` passa por `sistema/app/services/forms_submit.py`.

Sequencia real:

1. converte `informe` em `ontime`:
   - `normal -> True`
   - `retroativo -> False`

2. resolve `local` final:
   - usa o `local` recebido;
   - se vier vazio, cai no `default_local` do canal (`Web` ou `Aplicativo`).

3. checa duplicidade logica por `UserSyncEvent`:
   - chave: `source == channel.user_sync_source`
   - idempotencia: `source_request_id == client_event_id`

4. garante que o usuario exista:
   - web usa `ensure_web_user(...)` e pode criar `nome="Oriundo da Web"`;
   - mobile usa `ensure_mobile_user(...)` e pode criar `nome="Oriundo do Aplicativo"`.

5. normaliza `event_time` para o timezone do projeto.

6. chama `ensure_current_user_state_event(...)` para materializar estado atual como `state_import` quando necessario.

7. calcula `latest_activity` e decide `should_queue_forms`.

8. aplica o novo estado ao usuario com `apply_user_state(...)`:
   - atualiza `user.checkin`;
   - atualiza `user.time`;
   - atualiza projeto ativo quando o canal envia projeto;
   - atualiza `user.local` quando houver `local`.

9. se NAO precisa novo Forms:
   - cria `UserSyncEvent`;
   - grava `CheckEvent` com status `updated` e `forms_skipped=true`;
   - faz `commit`;
   - notifica admin;
   - dispara hook de acidente;
   - responde `queued_forms=false`.

10. se precisa novo Forms:
    - persiste `FormsSubmission` com status inicial `pending`;
    - cria `UserSyncEvent`;
    - grava `CheckEvent` com status `queued` e `forms_deferred=true`;
    - faz `commit`;
    - notifica admin;
    - dispara hook de acidente;
    - responde `queued_forms=true` e `worker_healthy=is_forms_worker_healthy_now()`.

### 7.1 Semantica da resposta ao cliente

Mesmo quando a API grava log interno com `http_status=202`, o HTTP real do endpoint web/mobile continua sendo um `200 OK` comum com corpo JSON. A distincao entre `atualizado`, `enfileirado` e `ja concluido no Forms` fica somente no corpo/logs, nao no status HTTP externo.

### 7.2 Duplicidade

Ha duas camadas relevantes:

- duplicidade logica por `UserSyncEvent.source_request_id` no helper;
- duplicidade fisica por `forms_submissions.request_id` com `UniqueConstraint`.

## 8. Persistencias que nascem dessa rotina

### 8.1 `forms_submissions`

Modelo em `sistema/app/models.py`:

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

Estados tipicos:

- `pending`
- `processing`
- `success`
- `failed`

### 8.2 `user_sync_events`

Todo submit aceito tambem gera `UserSyncEvent`:

- web forms usa `source="web_forms"`;
- mobile forms usa `source="android_forms"`;
- RFID usa `source="rfid"`;
- mobile legado usa `source="android"`.

Esse evento tambem registra `ontime` e alimenta o historico consolidado.

### 8.3 `check_events`

O sistema grava auditoria em `check_events` com status como:

- `queued`
- `updated`
- `duplicate`
- `success`
- `failed`
- `warning`

O campo `ontime` aparece tanto no evento de aceite do request quanto no evento final produzido pelo worker.

### 8.4 `checking_history`

`create_user_sync_event(...)` chama `record_checking_history(...)`, entao o historico do usuario e atualizado mesmo quando a atividade nao gera novo envio ao Forms.

## 9. Worker e fila do Forms

### 9.1 Onde o worker roda

O consumo da fila roda no entrypoint separado:

- `sistema/app/forms_worker_main.py`

Se `forms_queue_enabled` estiver desligado:

- o worker nao consome fila;
- a API ainda pode enfileirar, mas a saude do worker fica registrada como `disabled`.

### 9.2 Como a fila e consumida

Em `forms_queue.py`:

1. `_reserve_next_submission_id()` pega um item `pending` e faz claim atomico para `processing`;
2. `_process_submission(submission_id)` recarrega a linha e instancia `FormsWorker`;
3. o worker executa `submit_with_retries(...)`;
4. o item vai para `success` ou `failed`;
5. a API grava um `CheckEvent` final com o resultado.

### 9.3 Lote por loop

O worker processa em lotes de ate 10 itens por passada (`process_forms_submission_queue_once(max_items=10)`).

### 9.4 Diagnostico e observabilidade

Endpoint admin:

- `GET /api/admin/forms/queue/diagnostics`

Campos retornados:

- `generated_at`
- `backlog_count`
- `pending_count`
- `processing_count`
- `success_count`
- `failed_count`
- `oldest_backlog_age_seconds`
- `oldest_pending_age_seconds`
- `oldest_processing_age_seconds`
- `recent_average_processing_ms`
- `recent_processed_sample_size`
- `worker.*`

Campos do snapshot do worker:

- `enabled`
- `running`
- `status`
- `poll_interval_seconds`
- `thread_name`
- `process_id`
- `started_at`
- `last_heartbeat_at`
- `heartbeat_age_seconds`
- `stale`
- `last_loop_started_at`
- `last_loop_completed_at`
- `last_loop_processed_count`
- `consecutive_error_count`
- `current_backoff_seconds`
- `restart_count`
- `last_error`

Arquivo persistido de health:

- `forms_worker_health.json` em `event_archives_dir`

### 9.5 Aviso quando o worker esta ruim

`enqueue_forms_submission(...)` chama `_maybe_emit_worker_down_warning(...)`.

Se o worker estiver `disabled`, `stale`, `not running` ou acima do limite de erro consecutivo, a API grava um `CheckEvent` com:

- `source="system"`
- `action="forms_warn"`
- `status="warning"`
- `message="Forms enqueued while worker is down"`

## 10. Preenchimento real do Microsoft Forms pelo Playwright

O preenchimento real vive em `sistema/app/services/forms_worker.py`.

### 10.1 Seletores carregados

O worker carrega estes arquivos de XPath:

- `digitar_chave.txt`
- `confirmar_chave.txt`
- `botao_normal.txt`
- `botao_retroativo.txt`
- `botao_checkin.txt`
- `botao_checkout.txt`
- `botao_enviar.txt`
- `sucesso.txt`
- `botao_projeto_*.txt`

Hoje existem seletores especificos versionados para:

- `P80`
- `P82`
- `P83`

Se o projeto nao tiver arquivo proprio, o worker monta um XPath generico por texto visivel do projeto.

### 10.2 Sequencia exata de passos

O metodo `_submit_once(...)` segue esta ordem:

1. abre Chromium headless;
2. navega para `settings.forms_url`;
3. preenche `digitar_chave` com a chave;
4. preenche `confirmar_chave` com a mesma chave;
5. clica em `botao_normal` ou `botao_retroativo` conforme `ontime`;
6. se a acao for `checkin`:
   - clica em `botao_checkin`;
   - exige `projeto` nao nulo;
   - clica no botao do projeto.
7. se a acao for `checkout`:
   - clica apenas em `botao_checkout`;
   - nao seleciona projeto no formulario.
8. valida que o XPath de sucesso ainda nao esta visivel antes do envio;
9. clica em `botao_enviar`;
10. espera `sucesso` ficar visivel;
11. captura o texto de sucesso e grava isso nos detalhes de auditoria.

### 10.3 Diferenca entre check-in e check-out no Forms

Check-in:

- seleciona tipo `checkin`;
- seleciona projeto dentro do Forms.

Check-out:

- seleciona tipo `checkout`;
- nao tenta clicar em projeto.

Isso e importante porque a fila sempre persiste `projeto`, mas o Playwright so usa esse dado para o caminho de check-in.

### 10.4 Confirmacoes de cada etapa

O worker nao apenas clica ou preenche; ele valida:

- campos preenchidos realmente contem o valor esperado;
- radios clicados realmente ficaram marcados;
- o passo de sucesso apareceu apos o envio.

### 10.5 Timeouts relevantes

- busca de campo/botao: `FIELD_SEARCH_TIMEOUT_SECONDS = 10`
- confirmacao de valor/checked: `STEP_CONFIRM_TIMEOUT_SECONDS = 10`
- busca da tela de sucesso: `SUCCESS_SEARCH_TIMEOUT_SECONDS = 20`
- navegacao inicial: `settings.forms_timeout_seconds * 1000`

### 10.6 Politica de retry

`submit_with_retries(...)` nao faz retry para todo erro.

Ele encerra sem nova tentativa em caso de:

- `FormsStepTimeoutError`
- `FormsStepValidationError`
- `ValueError`

Ele so tenta novamente em caso de `PlaywrightTimeoutError` bruto durante a execucao.

Ao esgotar as tentativas, retorna:

- `error_code="forms_runtime_error"`
- `retry_count=settings.forms_max_retries`

### 10.7 Evidencia de passo bem sucedido

Os detalhes de auditoria do passo concluido incluem texto como:

```text
steps=digitar_chave:filled+verified,confirmar_chave:filled+verified,botao_normal:clicked+verified,botao_checkin:clicked+verified,botao_projeto_P80:clicked+verified,botao_enviar:clicked,sucesso:visible
```

Tambem entram nesses detalhes:

- `ontime=true|false`
- `success_xpath_visible=true`
- `submit_to_success_ms=...`
- `success_text=...`

## 11. Relacao entre atividade do usuario e o FORMS

### 11.1 Mesma acao no mesmo dia

Exemplo:

- checkout 1 no mesmo dia -> enfileira novo Forms;
- checkout 2 no mesmo dia -> nao enfileira novo Forms, mas atualiza `user.local`, `user.time`, `UserSyncEvent` e historico.

Ou seja, o sistema preserva a atividade mais recente do usuario internamente, sem necessariamente repetir o preenchimento externo do Forms.

### 11.2 `retroativo`

`retroativo` vira `ontime=False` e isso aparece em:

- `forms_submissions.ontime`
- `user_sync_events.ontime`
- `check_events.ontime`

### 11.3 Atividades automaticas do web

Quando o front dispara submit automatico:

- ele tambem usa `/api/web/check`;
- ele tambem manda `event_time = new Date().toISOString()`;
- ele forca `informe = normal`;
- ele usa o `local` calculado pelo contexto de localizacao.

### 11.4 RFID

No RFID:

- o horario do evento nao vem do dispositivo; ele nasce no servidor via `now_sgt()`;
- a regra de mesma acao no mesmo dia tambem vale;
- checkout sem atividade anterior valida e bloqueado antes de qualquer fila.

### 11.5 Web e projeto ativo

No web:

- o submit usa o projeto ativo comprometido na UI;
- a API valida se esse projeto pertence aos memberships do usuario;
- se nao pertencer, a atividade e rejeitada com `409`.

## 12. Evidencias importantes cobertas por teste

Os testes atuais provam pelo menos estes pontos:

- atividade repetida da mesma acao no mesmo dia nao gera novo Forms, mas atualiza estado local;
- mobile `retroativo` persiste `ontime=False` na fila e na trilha de auditoria;
- web `retroativo` tambem registra `ontime=False`;
- o worker grava detalhes de passos concluidos, inclusive texto de sucesso;
- o endpoint admin de diagnostico reflete backlog, processamento e saude do worker.

Casos especialmente uteis para leitura:

- `test_repeated_same_day_checkout_updates_state_without_forms_submission`
- `test_mobile_forms_submit_accepts_retroativo_and_persists_ontime_false`
- o teste web que valida dois `checkout` retroativos no mesmo dia com apenas uma linha em `forms_submissions`
- `test_forms_queue_processing_emits_structured_logs`

## 13. Pontos criticos observados neste estudo

### 13.1 Sucesso percebido pelo usuario nao e o mesmo que sucesso no Forms

Hoje:

- web check considera o submit bem sucedido quando a API aceita a atividade;
- ESP32 tambem recebe resposta positiva quando a API aceita/enfileira;
- o preenchimento real do Microsoft Forms acontece depois.

Se o worker estiver parado, atrasado ou falhando:

- o usuario ainda pode ver mensagem positiva imediata;
- a evidenca do problema fica em `forms_submissions`, `check_events` e nos diagnosticos da fila.

### 13.2 O web front ignora `queued_forms` e `worker_healthy`

O endpoint web responde esses campos, mas o `app.js` nao muda a UX com base neles. Na pratica:

- `queued_forms=true` nao vira mensagem de "aguardando processamento";
- `worker_healthy=false` nao vira alerta para o usuario.

### 13.3 O log final do worker perde o canal original

No processamento final da fila, `_process_submission(...)` grava `log_event(...)` com `request_path="/api/scan"` fixo. Isso significa que o evento final de sucesso/falha do worker nao preserva claramente se a origem foi:

- web;
- mobile;
- RFID.

Essa e uma limitacao atual da observabilidade, porque a fila persiste `device_id`, `chave`, `projeto`, `local` e `ontime`, mas nao persiste o `request_path` original do canal.

### 13.4 Modo automatico sempre manda `normal`

Mesmo que o usuario tenha selecionado `retroativo` na UI, qualquer submit automatico do web envia `informe=normal`. Isso nao e um bug de transporte; e o comportamento atual implementado no front.

## 14. Como inspecionar rapidamente em homologacao/producao

### 14.1 Diagnostico da fila

Com sessao admin valida:

```bash
GET /api/admin/forms/queue/diagnostics
```

Olhar principalmente:

- `backlog_count`
- `pending_count`
- `processing_count`
- `failed_count`
- `oldest_backlog_age_seconds`
- `worker.status`
- `worker.running`
- `worker.stale`
- `worker.last_error`

### 14.2 Eventos administrativos

Na trilha de `check_events`, procurar:

- eventos do request com status `queued` ou `updated`;
- eventos do worker com source `forms` e status `success` ou `failed`;
- eventos `forms_warn` quando o worker estiver indisponivel.

### 14.3 Tabela da fila

Em `forms_submissions`, conferir:

- se os itens ficam presos em `pending`;
- se acumulam em `processing`;
- se `last_error` descreve falha de passo, validacao ou runtime;
- se `ontime` esta coerente com o `informe` esperado.

## 15. Fluxo resumido em pseudo-pipeline

```text
usuario/web/mobile/RFID
  -> API recebe atividade
  -> normaliza chave/projeto/local/event_time
  -> calcula ultima atividade interna relevante
  -> decide se precisa novo Forms
     -> nao: atualiza estado local + historico + auditoria
     -> sim: cria FormsSubmission(pending) + historico + auditoria
  -> cliente recebe sucesso logico

worker Forms
  -> claim pending -> processing
  -> abre Forms via Playwright
  -> preenche chave, informe, acao e projeto (checkin)
  -> envia
  -> espera sucesso
  -> grava success/failed na fila e em check_events
```

## 16. Conclusao objetiva

O FORMS e preenchido de forma assincroma e orientada por atividade consolidada do usuario. O ponto central nao esta apenas em "clicar no Forms", e sim em duas camadas:

- camada 1: a API decide se a atividade merece um novo envio externo ou apenas atualizacao interna;
- camada 2: o worker Playwright executa o formulario real depois, fora do tempo de resposta do cliente.

Se houver divergencia entre o que o usuario viu e o que chegou no Microsoft Forms, a investigacao precisa sempre separar essas duas camadas.