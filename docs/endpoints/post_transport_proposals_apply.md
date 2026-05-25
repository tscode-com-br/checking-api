# `POST /api/transport/proposals/apply`

## Visão Geral

Aplica uma proposta operacional aprovada, persistindo as alocações de transporte no banco de dados. Este é o último passo do fluxo: build → validate → approve → **apply**. Apenas propostas com `proposal_status: "approved"` podem ser aplicadas com sucesso.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/proposals/apply`                                  |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. O usuário logado é resolvido como `AdminUser` para registro nas colunas FK→`admin_users.id` das alocações criadas/atualizadas.

---

## Parâmetros

### Request Body

```json
{
  "proposal": {
    "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
    "proposal_status": "approved",
    "origin": "manual",
    "snapshot": { "...": "snapshot completo" },
    "decisions": [
      {
        "request_id": 10,
        "request_kind": "regular",
        "service_date": "2026-05-25",
        "route_kind": "home_to_work",
        "suggested_status": "confirmed",
        "vehicle_id": 5,
        "boarding_time": "07:30",
        "response_message": null,
        "rationale": null
      }
    ],
    "summary": { "...": "summary completo" },
    "validation_issues": [],
    "audit_trail": [...]
  }
}
```

| Campo      | Tipo     | Obrigatório | Descrição                                                        |
|------------|----------|-------------|------------------------------------------------------------------|
| `proposal` | `object` | Sim         | Proposta completa com `proposal_status: "approved"`.             |

---

## Resposta

**Aplicação bem-sucedida:**

```json
{
  "ok": true,
  "message": "Proposal applied to transport assignments.",
  "proposal": {
    "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
    "proposal_status": "applied",
    "audit_trail": [
      {
        "action": "applied",
        "actor_id": 42,
        "actor_chave": "AB12",
        "actor_nome": "João da Silva",
        "timestamp": "2026-05-25T07:50:00+08:00",
        "message": null
      }
    ]
  },
  "applied_assignments": [
    {
      "assignment_id": 101,
      "request_id": 10,
      "service_date": "2026-05-25",
      "route_kind": "home_to_work",
      "status": "confirmed",
      "vehicle_id": 5,
      "was_update": false
    }
  ]
}
```

**Bloqueado por problemas de validação:**

```json
{
  "ok": false,
  "message": "Proposal application was blocked by validation issues.",
  "proposal": { "proposal_status": "draft", "validation_issues": [...] },
  "applied_assignments": []
}
```

### Campos da resposta

| Campo                | Tipo     | Descrição                                                                          |
|----------------------|----------|------------------------------------------------------------------------------------|
| `ok`                 | `bool`   | `true` se `proposal_status` é `"applied"`.                                         |
| `message`            | `string` | Descrição do resultado.                                                            |
| `proposal`           | `object` | Proposta com `proposal_status: "applied"` e novo registro no `audit_trail`.        |
| `applied_assignments`| `array`  | Lista das alocações criadas ou atualizadas no banco.                               |

#### Campos de cada item em `applied_assignments`

| Campo           | Tipo          | Descrição                                                              |
|-----------------|---------------|------------------------------------------------------------------------|
| `assignment_id` | `int`         | ID do registro de alocação no banco.                                   |
| `request_id`    | `int`         | ID da solicitação de transporte.                                       |
| `service_date`  | `date`        | Data do serviço.                                                       |
| `route_kind`    | `string`      | Sentido da rota.                                                       |
| `status`        | `string`      | Status aplicado: `confirmed`, `rejected`, `cancelled` ou `pending`.    |
| `vehicle_id`    | `int\|null`   | ID do veículo alocado (somente quando `status = confirmed`).           |
| `was_update`    | `bool`        | `true` se a alocação já existia e foi atualizada; `false` se é nova.   |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Operação de aplicação executada.          |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

- **Persiste** as alocações de transporte no banco de dados (tabela `transport_assignments`).
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite um evento de reavaliação `transport_assignment_changed` no catálogo in-memory.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d @proposta_aprovada.json \
  http://127.0.0.1:8000/api/transport/proposals/apply | python -m json.tool
```
