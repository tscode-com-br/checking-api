# `POST /api/transport/proposals/reject`

## Visão Geral

Rejeita uma proposta operacional de transporte, registrando a ação no `audit_trail` com uma mensagem opcional de justificativa. A rejeição não persiste dados no banco — apenas muda o `proposal_status` para `"rejected"`. Pode ser chamado em qualquer ponto do fluxo antes do apply.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/proposals/reject`                                 |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. O usuário logado é registrado como `actor` da rejeição no `audit_trail`.

---

## Parâmetros

### Request Body

```json
{
  "proposal": {
    "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
    "proposal_status": "draft",
    "origin": "manual",
    "snapshot": { "...": "snapshot completo" },
    "decisions": [...],
    "summary": { "...": "summary completo" },
    "validation_issues": [],
    "audit_trail": []
  },
  "message": "Proposta rejeitada — veículo indisponível confirmado."
}
```

| Campo      | Tipo           | Obrigatório | Descrição                                                                  |
|------------|----------------|-------------|----------------------------------------------------------------------------|
| `proposal` | `object`       | Sim         | Objeto `TransportOperationalProposal` completo.                            |
| `message`  | `string\|null` | Não         | Justificativa da rejeição (máx. 255 caracteres). Registrada no audit_trail.|

---

## Resposta

```json
{
  "ok": true,
  "message": "Proposal rejected without applying assignments.",
  "proposal": {
    "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
    "proposal_status": "rejected",
    "audit_trail": [
      {
        "action": "rejected",
        "actor_id": 42,
        "actor_chave": "AB12",
        "actor_nome": "João da Silva",
        "timestamp": "2026-05-25T07:40:00+08:00",
        "message": "Proposta rejeitada — veículo indisponível confirmado."
      }
    ],
    "...": "demais campos da proposta"
  }
}
```

### Campos da resposta

| Campo      | Tipo     | Descrição                                                                              |
|------------|----------|----------------------------------------------------------------------------------------|
| `ok`       | `bool`   | Sempre `true` neste endpoint.                                                          |
| `message`  | `string` | Mensagem confirmando a rejeição.                                                       |
| `proposal` | `object` | Proposta com `proposal_status: "rejected"` e registro no `audit_trail`.                |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Proposta rejeitada com sucesso.           |
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
  -d '{
    "proposal": { "...": "proposta completa" },
    "message": "Veículos não disponíveis para esta data."
  }' \
  http://127.0.0.1:8000/api/transport/proposals/reject | python -m json.tool
```
