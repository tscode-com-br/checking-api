# `GET /api/transport/ai/suggestions/latest`

## Visão Geral

Retorna o status da sugestão de rotas mais recente e ativa para uma combinação de data de serviço e tipo de rota (`route_kind`). É utilizado pelo frontend para verificar se já existe uma sugestão salva que pode ser revisada ou aplicada, sem que seja necessário conhecer antecipadamente o `run_key` ou `suggestion_key` correspondente.

| Atributo         | Valor                                               |
|------------------|-----------------------------------------------------|
| **Método**       | `GET`                                               |
| **Path**         | `/api/transport/ai/suggestions/latest`              |
| **Autenticação** | Sessão de transporte obrigatória (cookie)           |
| **Content-Type** | N/A (sem corpo de requisição)                       |

---

## Autenticação

Requer sessão de transporte ativa. O cookie de sessão é verificado pela dependência `require_transport_session`. Sem sessão válida, o servidor retorna `401 Unauthorized` ou `403 Forbidden`.

---

## Parâmetros

### Query Parameters

| Parâmetro      | Tipo            | Obrigatório | Descrição                                               |
|----------------|-----------------|-------------|---------------------------------------------------------|
| `service_date` | `string` (date) | Sim         | Data de serviço no formato `YYYY-MM-DD`                 |
| `route_kind`   | `string`        | Sim         | Direção da rota: `"home_to_work"` ou `"work_to_home"`  |

A sugestão "mais recente ativa" é a que possui status `"shown"` ou `"saved"` para a data e tipo de rota informados, ordenada por `updated_at` decrescente.

---

## Resposta

Retorna um objeto `TransportAgentRunStatusResponse` (mesmo formato do `GET /api/transport/ai/route-calculations/{run_key}`).

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

Para a descrição completa dos campos, consulte a documentação de [`GET /api/transport/ai/route-calculations/{run_key}`](get_transport_ai_route_calculations.md).

---

## Códigos de status HTTP

| Código | Significado                                                                               |
|--------|-------------------------------------------------------------------------------------------|
| `200`  | Sugestão ativa encontrada e retornada com sucesso.                                        |
| `401`  | Sessão de transporte ausente ou inválida.                                                 |
| `403`  | Sessão sem permissão de transporte.                                                       |
| `404`  | Nenhuma sugestão ativa encontrada para os parâmetros informados. `error_code`: `transport_ai_suggestion_not_found` ou `transport_ai_run_not_found` |
| `422`  | Parâmetros ausentes ou inválidos (ex.: `service_date` em formato incorreto).             |

### Estrutura do corpo de erro 404

```json
{
  "message": "Sugestão do Transport AI não encontrada.",
  "message_key": "ai.noSavedSuggestion",
  "message_params": {},
  "error_code": "transport_ai_suggestion_not_found",
  "issues": [
    {
      "code": "transport_ai_suggestion_not_found",
      "message": "Sugestão do Transport AI não encontrada.",
      "service_date": "2026-05-26",
      "route_kind": "home_to_work"
    }
  ],
  "technical_detail": "Transport AI suggestion not found."
}
```

---

## Side effects

Nenhum. O endpoint apenas lê dados.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -b "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/transport/ai/suggestions/latest?service_date=2026-05-26&route_kind=home_to_work"
```
