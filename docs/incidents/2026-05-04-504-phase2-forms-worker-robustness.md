# Robustez do worker separado do Forms - Fase 2 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado em escopo de repo.
- Objetivo desta etapa: endurecer o worker separado com backoff, health observavel, logs estruturados e reinicio automatico no nivel certo, sem reaproximar o app HTTP do processamento pesado do Forms.
- Regra preservada: o preenchimento do Forms em `sistema/app/services/forms_worker.py` permaneceu intacto.

## 2. O que foi endurecido

### 2.1 Retentativa e backoff do loop do worker

- O envio de cada item continua reaproveitando `submit_with_retries(...)` do `FormsWorker`.
- Alem disso, o loop do `FormsSubmissionWorker` agora aplica backoff exponencial quando `process_forms_submission_queue_once(...)` falha por excecao nao tratada.
- Politica atual:
  - base: `1s`
  - teto: `15s`
  - crescimento: exponencial por contagem de erros consecutivos

### 2.2 Reinicio automatico

- O processo do worker continua rodando em servico separado com `restart: unless-stopped` no compose.
- Dentro do processo, `run_forms_submission_worker_forever()` passou a atuar como supervisor leve:
  - observa o thread do worker;
  - grava heartbeat periodico em arquivo compartilhado;
  - se o thread morrer inesperadamente, agenda restart com backoff exponencial;
  - religa o worker sem depender do app HTTP.

### 2.3 Logs estruturados do worker

- O logger `checking.forms_queue` continua sendo a fonte estruturada do worker.
- Eventos relevantes desta etapa:
  - `forms_queue_worker_error`
  - `forms_queue_worker_supervisor_started`
  - `forms_queue_worker_supervisor_restart_scheduled`
  - `forms_queue_worker_supervisor_stopped`
  - `forms_queue_worker_health_write_failed`
  - `forms_queue_worker_health_read_failed`

Os logs de erro e restart agora carregam campos suficientes para responder rapidamente:

- quantos erros consecutivos o loop acumulou;
- qual backoff foi aplicado;
- quantos restarts do worker ja ocorreram;
- qual foi o ultimo erro observado.

### 2.4 Health observavel do worker

- O worker agora publica um heartbeat JSON em volume compartilhado:
  - `/app/data/event_archives/forms_worker_health.json`
- O arquivo e alimentado pelo supervisor do worker, nao pelo app HTTP.
- O `forms-worker` ganhou healthcheck proprio no compose via:

```bash
python -m sistema.app.forms_worker_healthcheck
```

- O endpoint ja existente `GET /api/admin/forms/queue/diagnostics` passou a preferir esse snapshot persistido do worker, em vez do estado em memoria local do processo HTTP.

## 3. Como o worker passa a ser observado

O diagnostico minimo agora fica dividido em dois planos independentes:

### 3.1 Saude do consumidor

- `docker inspect checkcheck-forms-worker-1 --format '{{json .State.Health}}'`
- `docker logs --since 10m checkcheck-forms-worker-1`
- `docker exec checkcheck-forms-worker-1 python -m sistema.app.forms_worker_healthcheck`
- arquivo `/app/data/event_archives/forms_worker_health.json`

### 3.2 Saude da fila

- `GET /api/admin/forms/queue/diagnostics`
- consulta SQL ou admin diagnostics para backlog, pendentes, processamento, idade do item mais antigo e taxa recente de processamento

## 4. Como inspecionar backlog em producao

Ordem recomendada de inspeção:

1. verificar se o servico `forms-worker` esta `healthy`;
2. verificar o snapshot do worker e confirmar:
   - `running`
   - `status`
   - `heartbeat_age_seconds`
   - `consecutive_error_count`
   - `restart_count`
   - `last_error`
3. consultar a fila via `GET /api/admin/forms/queue/diagnostics` e observar:
   - `backlog_count`
   - `pending_count`
   - `processing_count`
   - `oldest_backlog_age_seconds`
   - `recent_average_processing_ms`
   - `failed_count`
4. correlacionar com logs estruturados do worker e do HTTP.

Exemplo operacional com sessao admin valida:

```bash
curl -sS -b /tmp/checkcheck_admin.cookies \
  http://127.0.0.1:8000/api/admin/forms/queue/diagnostics
```

Exemplo operacional no host para o servico do worker:

```bash
docker inspect checkcheck-forms-worker-1 --format '{{json .State.Health}}'
docker logs --since 10m checkcheck-forms-worker-1
docker exec checkcheck-forms-worker-1 python -m sistema.app.forms_worker_healthcheck
docker exec checkcheck-forms-worker-1 cat /app/data/event_archives/forms_worker_health.json
```

## 5. Resultado tecnico desta etapa

- o app HTTP continua sem depender do worker para responder rotas criticas;
- o worker passou a ter retry/backoff no nivel do loop de consumo;
- o processo do worker passou a ter restart automatico do thread interno quando necessario;
- o worker passou a ter health minimo observavel e separado do health do HTTP;
- o backlog pode ser inspecionado operacionalmente sem recolocar Playwright no processo da API.

## 6. Proximo passo recomendado

O proximo passo natural da Fase 2 e validar a isolacao sob backlog controlado, provando com evidencias que `/api/health`, login e `/api/web/check/state` continuam respondendo bem enquanto o worker enfrenta fila pressionada.