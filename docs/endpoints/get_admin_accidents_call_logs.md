# `GET /api/admin/accidents/{accident_id}/call-logs`

## Visão Geral

Retorna todos os logs de chamadas de emergência associadas a um acidente, ordenados pelo número sequencial da chamada (`call_number`).

| Atributo         | Valor                                                   |
|------------------|---------------------------------------------------------|
| **Método**       | `GET`                                                   |
| **Path**         | `/api/admin/accidents/{accident_id}/call-logs`          |
| **Autenticação** | Sessão admin (qualquer nível de acesso)                 |

---

## Autenticação

Requer sessão admin via cookie (`require_admin_session`).

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo      | Descrição               |
|---------------|-----------|-------------------------|
| `accident_id` | `integer` | ID do acidente.         |

---

## Resposta

**HTTP 200**

```json
[
  {
    "id": 1,
    "call_number": 1,
    "call_number_label": "000001",
    "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "accident_id": 5,
    "project_id": 3,
    "triggered_by_user_id": null,
    "triggered_by_admin_id": 2,
    "triggered_by_label": "João da Silva (AB12) [admin]",
    "to_phone": "+551199999999",
    "from_phone": "+15105551234",
    "call_status": "completed",
    "duration_seconds": 45,
    "ended_by": "caller",
    "error_message": null,
    "created_at": "2026-05-25T08:10:00Z",
    "updated_at": "2026-05-25T08:11:00Z"
  }
]
```

### Campos de cada item

| Campo                  | Tipo           | Descrição                                                              |
|------------------------|----------------|------------------------------------------------------------------------|
| `id`                   | `integer`      | ID do log.                                                             |
| `call_number`          | `integer`      | Número sequencial da chamada (por acidente).                           |
| `call_number_label`    | `string`       | Número formatado com 6 dígitos.                                        |
| `call_sid`             | `string\|null` | SID retornado pelo Twilio.                                             |
| `accident_id`          | `integer\|null`| ID do acidente associado.                                              |
| `project_id`           | `integer\|null`| ID do projeto.                                                         |
| `triggered_by_user_id` | `integer\|null`| ID do usuário que disparou a chamada (via Check Web), se aplicável.    |
| `triggered_by_admin_id`| `integer\|null`| ID do `admin_users` que disparou a chamada (via painel admin), se aplicável. |
| `triggered_by_label`   | `string`       | Nome formatado de quem disparou: `"Nome (chave) [admin]"` ou `"Nome (chave)"`. |
| `to_phone`             | `string`       | Número de destino da chamada.                                          |
| `from_phone`           | `string`       | Número de origem (Twilio).                                             |
| `call_status`          | `string`       | Status final da chamada (`"queued"`, `"ringing"`, `"in-progress"`, `"completed"`, `"failed"`, etc.). |
| `duration_seconds`     | `integer\|null`| Duração em segundos. `null` se não concluída.                          |
| `ended_by`             | `string\|null` | Quem encerrou a chamada (`"caller"`, `"callee"`, etc.).                |
| `error_message`        | `string\|null` | Mensagem de erro do Twilio, se aplicável.                              |
| `created_at`           | `datetime`     | ISO 8601 UTC de criação do log.                                        |
| `updated_at`           | `datetime`     | ISO 8601 UTC da última atualização (via Twilio callback).              |

---

## Códigos de status HTTP

| Código | Significado                              |
|--------|------------------------------------------|
| `200`  | Lista retornada (pode ser vazia `[]`).   |
| `401`  | Sessão ausente ou inválida.              |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/accidents/5/call-logs
```
