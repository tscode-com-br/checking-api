# `POST /api/transport/ai/suggestions/{suggestion_key}/save`

## Visão Geral

Salva uma sugestão de rotas gerada pela IA, marcando-a como revisada e pronta para aplicação posterior. A operação persiste o status `"saved"` tanto na sugestão quanto na execução (`TransportAIRun`) associada, registra um evento de ciclo de vida e notifica o painel administrativo e o frontend de transport via SSE.

Após salvar, a sugestão pode ser aplicada (via `POST /api/transport/ai/suggestions/{suggestion_key}/apply`) em um momento posterior, sem necessidade de recalcular.

| Atributo         | Valor                                                       |
|------------------|-------------------------------------------------------------|
| **Método**       | `POST`                                                      |
| **Path**         | `/api/transport/ai/suggestions/{suggestion_key}/save`       |
| **Autenticação** | Sessão de transporte obrigatória (cookie)                   |
| **Content-Type** | N/A (sem corpo de requisição)                               |

---

## Autenticação

Requer sessão de transporte ativa. O cookie de sessão é verificado pela dependência `require_transport_session`. Sem sessão válida, o servidor retorna `401 Unauthorized` ou `403 Forbidden`.

---

## Parâmetros

### Path Parameters

| Parâmetro        | Tipo     | Descrição                                                                                          |
|------------------|----------|----------------------------------------------------------------------------------------------------|
| `suggestion_key` | `string` | Identificador único da sugestão a ser salva (obtido via `GET /api/transport/ai/route-calculations/{run_key}` ou `GET /api/transport/ai/suggestions/latest`) |

---

## Pré-condições

A operação é aceita apenas quando:
- O status da sugestão é `"shown"` ou `"saved"`.
- O status da execução (`run`) associada é `"proposed"` ou `"saved"`.
- O payload da sugestão (plano de rotas) é válido e não possui problemas bloqueantes.

Se a sugestão já estiver com status `"saved"` e o run com status `"saved"`, a operação é idempotente — retorna `200 OK` sem realizar alterações.

---

## Resposta

Retorna um objeto `TransportAgentRunStatusResponse` com o estado atualizado.

```json
{
  "ok": true,
  "run_key": "ai-run-550e8400-e29b-41d4-a716-446655440000",
  "service_date": "2026-05-26",
  "route_kind": "home_to_work",
  "status": "saved",
  "llm_provider": "openai",
  "llm_model": "o3",
  "llm_reasoning_effort": "high",
  "message": "Sugestão salva. Revise e aplique quando estiver pronto.",
  "message_key": "ai.suggestionSaved",
  "message_params": {},
  "error_code": null,
  "failure_category": null,
  "review_state": "pending_review",
  "issues": [],
  "suggestion_key": "sug-660e8400-e29b-41d4-a716-446655441111",
  "suggestion_ready": true,
  "can_save": false,
  "can_apply": true,
  "can_cancel_restore": false,
  "created_at": "2026-05-26T05:30:00+08:00",
  "updated_at": "2026-05-26T05:40:00+08:00",
  "completed_at": "2026-05-26T05:35:42+08:00",
  "suggestion": {
    "suggestion_key": "sug-660e8400-e29b-41d4-a716-446655441111",
    "proposal_key": "prop-770e8400-e29b-41d4-a716-446655442222",
    "status": "saved",
    "prompt_version": "v2.1.0",
    "created_at": "2026-05-26T05:35:40+08:00",
    "updated_at": "2026-05-26T05:40:00+08:00",
    "saved_at": "2026-05-26T05:40:00+08:00",
    "applied_at": null,
    "discarded_at": null,
    "plan": { "...": "objeto TransportAgentPlan completo" },
    "audit": null
  }
}
```

### Exemplo de resposta de conflito (409)

Quando a sugestão não pode ser salva por estar em estado incompatível:

```json
{
  "ok": false,
  "run_key": "ai-run-550e8400-e29b-41d4-a716-446655440000",
  "service_date": "2026-05-26",
  "route_kind": "home_to_work",
  "status": "applied",
  "message": "A sugestão do Transport AI não pode mais ser salva.",
  "message_key": "ai.changesSaveFailed",
  "error_code": "transport_ai_suggestion_save_conflict",
  "..."  : "..."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                              |
|--------|------------------------------------------------------------------------------------------|
| `200`  | Sugestão salva com sucesso (ou já estava salva — idempotente).                           |
| `401`  | Sessão de transporte ausente ou inválida.                                                |
| `403`  | Sessão sem permissão de transporte.                                                      |
| `404`  | Sugestão não encontrada. `error_code`: `transport_ai_suggestion_not_found`               |
| `409`  | Conflito de estado: sugestão não pode ser salva no estado atual. O corpo de resposta possui `ok: false` e inclui o estado atual da execução. `error_code`: `transport_ai_suggestion_save_conflict` ou `transport_ai_suggestion_payload_invalid` |

---

## Side effects

- Atualiza `TransportAISuggestion.status` para `"saved"` e registra `saved_at`.
- Atualiza `TransportAIRun.status` para `"saved"`.
- Registra um evento de ciclo de vida via `record_transport_ai_lifecycle_transition` (stage: `suggestion_saved`).
- Chama `notify_admin_data_changed("event")` para notificar o painel admin via SSE.
- Emite um evento de reavaliação de transporte via `emit_transport_reevaluation_event` (tipo: `transport_operational_review_changed`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -b "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/transport/ai/suggestions/sug-660e8400-e29b-41d4-a716-446655441111/save"
```
