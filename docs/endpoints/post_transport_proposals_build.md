# `POST /api/transport/proposals/build`

## Visão Geral

Constrói uma nova proposta operacional de alocação de transporte para uma data e sentido de rota. A proposta contém um snapshot do estado atual, uma lista de decisões de alocação e um resumo quantitativo. Este é o primeiro passo do fluxo: **build → validate → approve → apply**.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/proposals/build`                                  |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. O usuário logado é registrado como `actor` da proposta.

---

## Parâmetros

### Request Body

```json
{
  "service_date": "2026-05-25",
  "route_kind": "home_to_work",
  "origin": "manual",
  "replaces_proposal_key": null,
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
      "rationale": "Veículo com capacidade disponível"
    }
  ],
  "captured_at": null,
  "created_at": null,
  "expires_at": null
}
```

| Campo                  | Tipo             | Obrigatório | Descrição                                                                       |
|------------------------|------------------|-------------|---------------------------------------------------------------------------------|
| `service_date`         | `date`           | Sim         | Data do serviço no formato `YYYY-MM-DD`.                                        |
| `route_kind`           | `string`         | Sim         | `home_to_work` ou `work_to_home`.                                               |
| `origin`               | `string`         | Não         | `manual` (padrão), `system` ou `agent`.                                         |
| `replaces_proposal_key`| `string\|null`   | Não         | Chave da proposta anterior que esta substitui.                                  |
| `decisions`            | `array`          | Não         | Lista de decisões de alocação (pode ser vazia para proposta em branco).         |
| `captured_at`          | `datetime\|null` | Não         | Timestamp de captura do snapshot (opcional — gerado pelo servidor se omitido).  |
| `created_at`           | `datetime\|null` | Não         | Timestamp de criação (opcional — gerado pelo servidor se omitido).              |
| `expires_at`           | `datetime\|null` | Não         | Timestamp de expiração da proposta (opcional).                                  |

#### Campos de cada decisão em `decisions`

| Campo              | Tipo           | Obrigatório | Descrição                                                                 |
|--------------------|----------------|-------------|---------------------------------------------------------------------------|
| `request_id`       | `int`          | Sim         | ID da solicitação de transporte.                                          |
| `request_kind`     | `string`       | Sim         | `regular`, `weekend` ou `extra`.                                          |
| `service_date`     | `date`         | Sim         | Data do serviço.                                                          |
| `route_kind`       | `string`       | Sim         | `home_to_work` ou `work_to_home`.                                         |
| `suggested_status` | `string`       | Sim         | `confirmed`, `rejected` ou `pending`.                                     |
| `vehicle_id`       | `int\|null`    | Condicional | Obrigatório quando `suggested_status = confirmed`.                        |
| `boarding_time`    | `string\|null` | Não         | Horário de embarque `HH:MM`; apenas para `confirmed` + `home_to_work`.    |
| `response_message` | `string\|null` | Não         | Mensagem de resposta ao passageiro (máx. 255 caracteres).                 |
| `rationale`        | `string\|null` | Não         | Justificativa da decisão (máx. 500 caracteres).                           |

---

## Resposta

Retorna um objeto `TransportOperationalProposal` completo com `proposal_status: "draft"`:

```json
{
  "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
  "proposal_status": "draft",
  "origin": "manual",
  "replaces_proposal_key": null,
  "created_at": "2026-05-25T07:30:00+08:00",
  "expires_at": null,
  "snapshot": { "...": "campos do snapshot operacional" },
  "decisions": [...],
  "summary": {
    "total_snapshot_requests": 5,
    "total_snapshot_vehicles": 3,
    "total_decisions": 5,
    "confirmed_decisions": 4,
    "rejected_decisions": 1,
    "pending_decisions": 0
  },
  "validation_issues": [],
  "audit_trail": []
}
```

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Proposta construída com sucesso.          |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

Nenhum. A proposta não é persistida no banco de dados — ela vive apenas na memória do cliente enquanto percorre o fluxo build → validate → approve → apply.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "origin": "manual",
    "decisions": []
  }' \
  http://127.0.0.1:8000/api/transport/proposals/build | python -m json.tool
```
