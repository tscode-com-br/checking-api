# `POST /api/transport/proposals/validate`

## Visão Geral

Valida uma proposta operacional de transporte contra as restrições do sistema (capacidade de veículos, disponibilidade para a data/rota, conflitos de escopo, etc.). Retorna a proposta com a lista de `validation_issues` preenchida e indica se há bloqueios. Segundo passo do fluxo: build → **validate** → approve → apply.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/proposals/validate`                               |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. O usuário logado é registrado como `actor` da validação.

---

## Parâmetros

### Request Body

O corpo é um objeto `TransportOperationalProposal` completo (retornado pelo endpoint `/proposals/build`):

```json
{
  "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
  "proposal_status": "draft",
  "origin": "manual",
  "replaces_proposal_key": null,
  "created_at": "2026-05-25T07:30:00+08:00",
  "expires_at": null,
  "snapshot": { "...": "snapshot completo obtido de /proposals/build" },
  "decisions": [...],
  "summary": { "...": "summary completo" },
  "validation_issues": [],
  "audit_trail": []
}
```

Consulte `post_transport_proposals_build.md` para a estrutura completa de `TransportOperationalProposal`.

---

## Resposta

```json
{
  "ok": false,
  "message": "Proposal validation found blocking issues.",
  "proposal": {
    "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
    "proposal_status": "draft",
    "validation_issues": [
      {
        "code": "vehicle_over_capacity",
        "message": "Vehicle SGP-1234 (van, 14 lugares) has 15 passengers assigned.",
        "message_key": "issues.vehicleOverCapacity",
        "message_params": {"vehicle_id": 5, "capacity": 14, "assigned": 15},
        "blocking": true,
        "request_id": null,
        "vehicle_id": 5
      }
    ],
    "...": "demais campos da proposta"
  }
}
```

Quando sem bloqueios:

```json
{
  "ok": true,
  "message": "Proposal validation passed without blocking issues.",
  "proposal": { "...": "proposta com validation_issues vazio ou apenas avisos" }
}
```

### Campos da resposta

| Campo      | Tipo     | Descrição                                                                           |
|------------|----------|-------------------------------------------------------------------------------------|
| `ok`       | `bool`   | `true` se não há `validation_issues` com `blocking: true`.                          |
| `message`  | `string` | Descrição do resultado da validação.                                                |
| `proposal` | `object` | Proposta com o campo `validation_issues` atualizado.                                |

#### Campos de cada item em `validation_issues`

| Campo            | Tipo           | Descrição                                                              |
|------------------|----------------|------------------------------------------------------------------------|
| `code`           | `string`       | Código do problema (ex.: `vehicle_over_capacity`).                     |
| `message`        | `string`       | Descrição legível do problema.                                         |
| `message_key`    | `string\|null` | Chave i18n para tradução no frontend.                                  |
| `message_params` | `object`       | Parâmetros para interpolação na mensagem i18n.                         |
| `blocking`       | `bool`         | Se `true`, impede a aprovação da proposta.                             |
| `request_id`     | `int\|null`    | ID da solicitação relacionada ao problema (quando aplicável).          |
| `vehicle_id`     | `int\|null`    | ID do veículo relacionado ao problema (quando aplicável).              |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Validação executada (independente do resultado). |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

- Emite um evento de reavaliação `transport_operational_review_changed` no catálogo in-memory.

---

## Exemplo cURL (ambiente local)

```bash
# Assumindo que PROPOSAL contém o JSON da proposta obtida de /proposals/build
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d @proposta.json \
  http://127.0.0.1:8000/api/transport/proposals/validate | python -m json.tool
```
