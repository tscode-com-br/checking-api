# `GET /api/admin/accidents/{accident_id}/notifications`

## Visão Geral

Retorna o feed persistente de notificações em português das chamadas de emergência de um acidente, ordenadas cronologicamente. Alimenta a barra de notificações do painel admin após um refresh ou reconexão SSE, permitindo que o frontend sincronize o estado sem depender apenas dos eventos SSE em tempo real.

| Atributo         | Valor                                                      |
|------------------|------------------------------------------------------------|
| **Método**       | `GET`                                                      |
| **Path**         | `/api/admin/accidents/{accident_id}/notifications`         |
| **Autenticação** | Sessão admin (qualquer nível de acesso)                    |

---

## Autenticação

Requer sessão admin via cookie (`require_admin_session`).

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo      | Descrição       |
|---------------|-----------|-----------------|
| `accident_id` | `integer` | ID do acidente. |

---

## Resposta

**HTTP 200**

```json
[
  {
    "id": 1,
    "call_log_id": 10,
    "accident_id": 5,
    "event_type": "call_initiated",
    "message_pt": "Chamada #000001 iniciada para +551199999999 às 08:10.",
    "occurred_at": "2026-05-25T08:10:00Z",
    "created_at": "2026-05-25T08:10:01Z"
  },
  {
    "id": 2,
    "call_log_id": 10,
    "accident_id": 5,
    "event_type": "call_completed",
    "message_pt": "Chamada #000001 concluída. Duração: 45 segundos.",
    "occurred_at": "2026-05-25T08:10:45Z",
    "created_at": "2026-05-25T08:10:46Z"
  }
]
```

### Campos de cada item

| Campo         | Tipo       | Descrição                                                               |
|---------------|------------|-------------------------------------------------------------------------|
| `id`          | `integer`  | ID da notificação.                                                      |
| `call_log_id` | `integer`  | ID do `accident_call_logs` ao qual esta notificação pertence.           |
| `accident_id` | `integer`  | ID do acidente.                                                         |
| `event_type`  | `string`   | Tipo do evento (ex.: `"call_initiated"`, `"call_completed"`, `"call_failed"`). |
| `message_pt`  | `string`   | Mensagem descritiva em português brasileiro.                            |
| `occurred_at` | `datetime` | ISO 8601 UTC do momento do evento.                                      |
| `created_at`  | `datetime` | ISO 8601 UTC de persistência no banco.                                  |

---

## Contexto de uso

As notificações são gravadas pela tabela `accident_call_notifications` (migração `0077`). O frontend deve:

1. Ao conectar/reconectar ao SSE, chamar este endpoint para recuperar notificações perdidas.
2. Usar `occurred_at` para ordenar e deduplicar por `id`.

---

## Códigos de status HTTP

| Código | Significado                                  |
|--------|----------------------------------------------|
| `200`  | Lista retornada (pode ser vazia `[]`).        |
| `401`  | Sessão ausente ou inválida.                   |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/accidents/5/notifications
```
