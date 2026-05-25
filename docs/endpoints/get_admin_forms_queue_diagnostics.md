# `GET /api/admin/forms/queue/diagnostics`

## Visão Geral

Retorna diagnósticos em tempo real da fila de processamento de formulários de providers. Inclui contagens de itens em cada estado da fila, métricas de latência de processamento e informações detalhadas sobre o worker background responsável por consumir a fila.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `GET`                                   |
| **Path**         | `/api/admin/forms/queue/diagnostics`    |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | —                                       |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

Nenhum.

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "generated_at": "2026-05-25T08:30:00Z",
  "backlog_count": 0,
  "pending_count": 2,
  "processing_count": 0,
  "success_count": 1540,
  "failed_count": 3,
  "oldest_backlog_age_seconds": null,
  "oldest_pending_age_seconds": 12,
  "oldest_processing_age_seconds": null,
  "recent_average_processing_ms": 48,
  "recent_processed_sample_size": 50,
  "worker": {
    "enabled": true,
    "running": true,
    "status": "idle",
    "poll_interval_seconds": 5.0,
    "thread_name": "forms-queue-worker",
    "process_id": 12345,
    "started_at": "2026-05-25T00:00:00Z",
    "last_heartbeat_at": "2026-05-25T08:29:55Z",
    "heartbeat_age_seconds": 5,
    "stale": false,
    "last_loop_started_at": "2026-05-25T08:29:55Z",
    "last_loop_completed_at": "2026-05-25T08:29:55Z",
    "last_loop_processed_count": 0,
    "consecutive_error_count": 0,
    "current_backoff_seconds": 0,
    "restart_count": 0,
    "last_error": null
  }
}
```

### Campos principais

| Campo                          | Tipo              | Descrição                                                                              |
|--------------------------------|-------------------|----------------------------------------------------------------------------------------|
| `generated_at`                 | `datetime`        | Timestamp da geração do diagnóstico.                                                   |
| `backlog_count`                | `integer`         | Itens aguardando para entrar na fila de processamento.                                 |
| `pending_count`                | `integer`         | Itens na fila aguardando processamento pelo worker.                                    |
| `processing_count`             | `integer`         | Itens sendo processados ativamente no momento.                                         |
| `success_count`                | `integer`         | Total histórico de itens processados com sucesso.                                      |
| `failed_count`                 | `integer`         | Total histórico de itens que falharam no processamento.                                |
| `oldest_backlog_age_seconds`   | `integer \| null` | Idade em segundos do item mais antigo no backlog. `null` se backlog vazio.             |
| `oldest_pending_age_seconds`   | `integer \| null` | Idade em segundos do item pendente mais antigo. `null` se fila vazia.                  |
| `oldest_processing_age_seconds`| `integer \| null` | Idade em segundos do item em processamento mais antigo. `null` se nenhum em processo.  |
| `recent_average_processing_ms` | `integer \| null` | Média de tempo de processamento (ms) dos últimos N itens. `null` se sem dados.         |
| `recent_processed_sample_size` | `integer`         | Tamanho da amostra usada para calcular `recent_average_processing_ms`.                 |

### Campos de `worker` (FormsQueueWorkerDiagnosticsResponse)

| Campo                        | Tipo              | Descrição                                                                   |
|------------------------------|-------------------|-----------------------------------------------------------------------------|
| `enabled`                    | `boolean`         | Se o worker está habilitado na configuração.                                |
| `running`                    | `boolean`         | Se a thread do worker está ativa.                                           |
| `status`                     | `string \| null`  | Estado atual: `"idle"`, `"processing"`, `"error"`, etc.                    |
| `poll_interval_seconds`      | `float`           | Intervalo de polling da fila em segundos.                                   |
| `thread_name`                | `string \| null`  | Nome da thread do worker.                                                   |
| `process_id`                 | `integer \| null` | PID do processo.                                                            |
| `started_at`                 | `datetime \| null`| Quando o worker foi iniciado.                                               |
| `last_heartbeat_at`          | `datetime \| null`| Último heartbeat registrado.                                                |
| `heartbeat_age_seconds`      | `integer \| null` | Segundos desde o último heartbeat.                                          |
| `stale`                      | `boolean`         | `true` se o heartbeat está defasado (worker possivelmente travado).         |
| `last_loop_started_at`       | `datetime \| null`| Início do último ciclo de processamento.                                    |
| `last_loop_completed_at`     | `datetime \| null`| Conclusão do último ciclo de processamento.                                 |
| `last_loop_processed_count`  | `integer`         | Quantidade de itens processados no último ciclo.                            |
| `consecutive_error_count`    | `integer`         | Número de erros consecutivos no worker.                                     |
| `current_backoff_seconds`    | `float`           | Backoff atual em segundos (cresce em caso de erros consecutivos).           |
| `restart_count`              | `integer`         | Total de restarts do worker desde o início do processo.                     |
| `last_error`                 | `string \| null`  | Mensagem do último erro registrado, se houver.                              |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso.                                                             |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/forms/queue/diagnostics
```
