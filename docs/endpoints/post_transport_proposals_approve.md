# `POST /api/transport/proposals/approve`

## Visão Geral

Aprova uma proposta operacional de transporte previamente validada. A aprovação não persiste dados no banco — apenas muda o `proposal_status` para `"approved"` e registra a ação no `audit_trail`. Terceiro passo do fluxo: build → validate → **approve** → apply.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/proposals/approve`                                |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. O usuário logado é registrado como `actor` da aprovação no `audit_trail`.

---

## Parâmetros

### Request Body

O corpo é um objeto `TransportOperationalProposal` completo (deve ter passado pela validação sem bloqueios):

```json
{
  "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
  "proposal_status": "draft",
  "origin": "manual",
  "snapshot": { "...": "snapshot completo" },
  "decisions": [...],
  "summary": { "...": "summary completo" },
  "validation_issues": [],
  "audit_trail": [...]
}
```

---

## Resposta

**Aprovação bem-sucedida:**

```json
{
  "ok": true,
  "message": "Proposal approved without applying assignments.",
  "proposal": {
    "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
    "proposal_status": "approved",
    "audit_trail": [
      {
        "action": "approved",
        "actor_id": 42,
        "actor_chave": "AB12",
        "actor_nome": "João da Silva",
        "timestamp": "2026-05-25T07:35:00+08:00",
        "message": null
      }
    ],
    "...": "demais campos da proposta"
  }
}
```

**Bloqueado por problemas de validação:**

```json
{
  "ok": false,
  "message": "Proposal approval was blocked by validation issues.",
  "proposal": {
    "proposal_status": "draft",
    "validation_issues": [...]
  }
}
```

### Campos da resposta

| Campo      | Tipo     | Descrição                                                                                     |
|------------|----------|-----------------------------------------------------------------------------------------------|
| `ok`       | `bool`   | `true` se `proposal_status` é `"approved"`.                                                   |
| `message`  | `string` | Descrição do resultado.                                                                       |
| `proposal` | `object` | Proposta com `proposal_status` atualizado e novo registro no `audit_trail`.                   |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Operação de aprovação executada.          |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

- Emite um evento de reavaliação `transport_operational_review_changed` no catálogo in-memory.
- Não grava nada no banco de dados.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d @proposta_validada.json \
  http://127.0.0.1:8000/api/transport/proposals/approve | python -m json.tool
```
