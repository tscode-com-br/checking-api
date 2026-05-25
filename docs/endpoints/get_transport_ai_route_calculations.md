# `GET /api/transport/ai/route-calculations/{run_key}`

## Visão Geral

Retorna o status detalhado de uma execução de cálculo de rotas específica, identificada por seu `run_key`. Inclui o estado atual do run, informações do LLM utilizado, mensagem de status, lista de problemas (issues), e, quando disponível, a sugestão mais recente gerada pela IA com o plano de rotas completo.

| Atributo         | Valor                                               |
|------------------|-----------------------------------------------------|
| **Método**       | `GET`                                               |
| **Path**         | `/api/transport/ai/route-calculations/{run_key}`    |
| **Autenticação** | Sessão de transporte obrigatória (cookie)           |
| **Content-Type** | N/A (sem corpo de requisição)                       |

---

## Autenticação

Requer sessão de transporte ativa. O cookie de sessão é verificado pela dependência `require_transport_session`. Sem sessão válida, o servidor retorna `401 Unauthorized` ou `403 Forbidden`.

---

## Parâmetros

### Path Parameters

| Parâmetro | Tipo     | Descrição                                          |
|-----------|----------|----------------------------------------------------|
| `run_key` | `string` | Identificador único da execução de cálculo de rotas (obtido ao iniciar um cálculo via `POST /api/transport/ai/route-calculations`) |

---

## Resposta

Retorna um objeto `TransportAgentRunStatusResponse`.

### Exemplo — execução em andamento

```json
{
  "ok": true,
  "run_key": "ai-run-550e8400-e29b-41d4-a716-446655440000",
  "service_date": "2026-05-26",
  "route_kind": "home_to_work",
  "status": "running",
  "llm_provider": "openai",
  "llm_model": "o3",
  "llm_reasoning_effort": "high",
  "message": "Cálculo de rotas em andamento.",
  "message_key": "ai.routeCalculationRunning",
  "message_params": {},
  "error_code": null,
  "failure_category": null,
  "review_state": "unavailable",
  "issues": [],
  "suggestion_key": null,
  "suggestion_ready": false,
  "can_save": false,
  "can_apply": false,
  "can_cancel_restore": false,
  "created_at": "2026-05-26T05:30:00+08:00",
  "updated_at": "2026-05-26T05:30:15+08:00",
  "completed_at": null,
  "suggestion": null
}
```

### Exemplo — execução concluída com sugestão disponível

```json
{
  "ok": true,
  "run_key": "ai-run-550e8400-e29b-41d4-a716-446655440000",
  "service_date": "2026-05-26",
  "route_kind": "home_to_work",
  "status": "proposed",
  "llm_provider": "openai",
  "llm_model": "o3",
  "llm_reasoning_effort": "high",
  "message": "Sugestão de rotas gerada com sucesso. Revise e salve para aplicar.",
  "message_key": "ai.suggestionReady",
  "message_params": {},
  "error_code": null,
  "failure_category": null,
  "review_state": "pending_review",
  "issues": [],
  "suggestion_key": "sug-660e8400-e29b-41d4-a716-446655441111",
  "suggestion_ready": true,
  "can_save": true,
  "can_apply": false,
  "can_cancel_restore": false,
  "created_at": "2026-05-26T05:30:00+08:00",
  "updated_at": "2026-05-26T05:35:42+08:00",
  "completed_at": "2026-05-26T05:35:42+08:00",
  "suggestion": {
    "suggestion_key": "sug-660e8400-e29b-41d4-a716-446655441111",
    "proposal_key": "prop-770e8400-e29b-41d4-a716-446655442222",
    "status": "shown",
    "prompt_version": "v2.1.0",
    "created_at": "2026-05-26T05:35:40+08:00",
    "updated_at": "2026-05-26T05:35:42+08:00",
    "saved_at": null,
    "applied_at": null,
    "discarded_at": null,
    "plan": { "...": "objeto TransportAgentPlan completo" },
    "audit": null
  }
}
```

### Campos da resposta

| Campo                | Tipo                      | Descrição                                                                          |
|----------------------|---------------------------|------------------------------------------------------------------------------------|
| `ok`                 | `boolean`                 | `true` se a execução está em estado saudável (não falhou)                          |
| `run_key`            | `string`                  | Identificador único da execução                                                    |
| `service_date`       | `string` (date)           | Data de serviço do cálculo                                                         |
| `route_kind`         | `string`                  | Direção: `"home_to_work"` ou `"work_to_home"`                                     |
| `status`             | `string`                  | Status atual da execução (ver valores válidos abaixo)                              |
| `llm_provider`       | `string`                  | Provedor LLM utilizado                                                             |
| `llm_model`          | `string`                  | Modelo LLM utilizado                                                               |
| `llm_reasoning_effort` | `string`                | Nível de raciocínio                                                                |
| `message`            | `string`                  | Mensagem descritiva do estado atual                                                |
| `message_key`        | `string \| null`          | Chave de i18n da mensagem                                                          |
| `message_params`     | `object`                  | Parâmetros de interpolação da mensagem i18n                                        |
| `error_code`         | `string \| null`          | Código de erro (quando a execução falhou)                                          |
| `failure_category`   | `string \| null`          | Categoria da falha (ex.: `"configuration"`, `"llm_invoke"`, `"geocoding"`)        |
| `review_state`       | `string`                  | Estado de revisão da sugestão: `"unavailable"`, `"pending_review"`, `"reviewed"`  |
| `issues`             | `array[TransportAgentRunIssue]` | Lista de problemas encontrados durante o cálculo                            |
| `suggestion_key`     | `string \| null`          | Chave da sugestão gerada (quando disponível)                                       |
| `suggestion_ready`   | `boolean`                 | `true` se há uma sugestão pronta para revisão                                     |
| `can_save`           | `boolean`                 | `true` se a sugestão pode ser salva pelo usuário                                  |
| `can_apply`          | `boolean`                 | `true` se a sugestão pode ser aplicada diretamente                                |
| `can_cancel_restore` | `boolean`                 | `true` se há uma restauração de baseline que pode ser cancelada                   |
| `created_at`         | `datetime`                | Timestamp de criação da execução                                                   |
| `updated_at`         | `datetime`                | Timestamp da última atualização                                                    |
| `completed_at`       | `datetime \| null`        | Timestamp de conclusão                                                             |
| `suggestion`         | `TransportAgentRunSuggestion \| null` | Objeto completo da sugestão mais recente (quando disponível)         |

**Valores válidos para `status`:**
`requested`, `baseline_saved`, `passengers_reset`, `running`, `proposed`, `saved`, `applied`, `cancelled`, `failed`

**Valores válidos para `failure_category`:**
`configuration`, `empty_scope`, `capacity`, `solver`, `geocoding`, `route_provider`, `llm_invoke`, `llm_response`

---

## Códigos de status HTTP

| Código | Significado                                                                  |
|--------|------------------------------------------------------------------------------|
| `200`  | Status da execução retornado com sucesso.                                    |
| `401`  | Sessão de transporte ausente ou inválida.                                    |
| `403`  | Sessão sem permissão de transporte.                                          |
| `404`  | Execução não encontrada para o `run_key` fornecido. `error_code`: `transport_ai_run_not_found` |

---

## Side effects

Nenhum. O endpoint apenas lê dados.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -b "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/transport/ai/route-calculations/ai-run-550e8400-e29b-41d4-a716-446655440000"
```
