# `GET /api/transport/ai/runs`

## Visão Geral

Retorna uma lista paginada de execuções de cálculo de rotas do Transport AI (`TransportAIRun`) com informações de diagnóstico, incluindo status, provedor e modelo LLM utilizados, código de erro, métricas de tokens e custo aproximado. Suporta filtros por data de serviço e status. Destinado principalmente ao painel de diagnóstico e auditoria das execuções de IA.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/transport/ai/runs`                       |
| **Autenticação** | Sessão de transporte obrigatória (cookie)      |
| **Content-Type** | N/A (sem corpo de requisição)                  |

---

## Autenticação

Requer sessão de transporte ativa. O cookie de sessão é verificado pela dependência `require_transport_session`. Sem sessão válida, o servidor retorna `401 Unauthorized` ou `403 Forbidden`.

---

## Parâmetros

### Query Parameters

| Parâmetro      | Tipo             | Obrigatório | Padrão | Descrição                                                          |
|----------------|------------------|-------------|--------|--------------------------------------------------------------------|
| `service_date` | `string` (date)  | Não         | null   | Filtra execuções pela data de serviço no formato `YYYY-MM-DD`      |
| `status`       | `string` (lista) | Não         | null   | Filtra pelo(s) status. Pode ser repetido: `?status=running&status=failed` |
| `limit`        | `integer`        | Não         | `20`   | Número máximo de execuções a retornar (1 a 100)                   |

**Valores válidos para `status`:**
`requested`, `baseline_saved`, `passengers_reset`, `running`, `proposed`, `saved`, `applied`, `cancelled`, `failed`

Os resultados são ordenados por `created_at` decrescente (mais recentes primeiro).

---

## Resposta

Retorna um objeto `TransportAIRunDiagnosticsResponse`.

```json
{
  "runs": [
    {
      "run_key": "ai-run-550e8400-e29b-41d4-a716-446655440000",
      "service_date": "2026-05-26",
      "route_kind": "home_to_work",
      "status": "applied",
      "llm_provider": "openai",
      "llm_model": "o3",
      "llm_reasoning_effort": "high",
      "openai_model": "o3",
      "route_provider": "here",
      "suggestion_key": "sug-660e8400-e29b-41d4-a716-446655441111",
      "suggestion_status": "applied",
      "prompt_version": "v2.1.0",
      "created_at": "2026-05-26T05:30:00+08:00",
      "updated_at": "2026-05-26T05:35:42+08:00",
      "completed_at": "2026-05-26T05:35:42+08:00",
      "duration_seconds": 342,
      "error_code": null,
      "error_message": null,
      "message_key": null,
      "message_params": {},
      "preflight_issue_codes": [],
      "validation_issue_codes": [],
      "blocking_issue_count": 0,
      "approximate_model_call_cost": 0.0142,
      "approximate_model_call_cost_currency": "USD",
      "prompt_tokens": 18432,
      "completion_tokens": 2841,
      "total_tokens": 21273,
      "has_raw_model_response": true,
      "observability": null
    }
  ],
  "count": 1,
  "service_date": "2026-05-26",
  "statuses": [],
  "limit": 20
}
```

### Campos da resposta raiz

| Campo          | Tipo              | Descrição                                          |
|----------------|-------------------|----------------------------------------------------|
| `runs`         | `array`           | Lista de entradas de diagnóstico                   |
| `count`        | `integer`         | Quantidade de execuções retornadas                 |
| `service_date` | `string \| null`  | Data de serviço usada como filtro (se fornecida)   |
| `statuses`     | `array[string]`   | Lista de status usados como filtro (se fornecidos) |
| `limit`        | `integer`         | Limite aplicado à consulta                         |

### Campos de `TransportAIRunDiagnosticsEntry`

| Campo                                | Tipo              | Descrição                                                                 |
|--------------------------------------|-------------------|---------------------------------------------------------------------------|
| `run_key`                            | `string`          | Identificador único da execução (UUID ou similar)                        |
| `service_date`                       | `string` (date)   | Data de serviço alvo                                                     |
| `route_kind`                         | `string`          | Direção: `"home_to_work"` ou `"work_to_home"`                            |
| `status`                             | `string`          | Status atual da execução                                                 |
| `llm_provider`                       | `string`          | Provedor LLM utilizado (ex.: `"openai"`)                                 |
| `llm_model`                          | `string`          | Modelo LLM utilizado (ex.: `"o3"`)                                       |
| `llm_reasoning_effort`               | `string`          | Nível de raciocínio (ex.: `"high"`)                                      |
| `openai_model`                       | `string`          | Modelo OpenAI registrado no momento da execução                          |
| `route_provider`                     | `string`          | Provedor de rotas (ex.: `"here"`)                                        |
| `suggestion_key`                     | `string \| null`  | Chave da sugestão mais recente vinculada a esta execução                 |
| `suggestion_status`                  | `string \| null`  | Status da sugestão mais recente                                          |
| `prompt_version`                     | `string \| null`  | Versão do prompt utilizado                                               |
| `created_at`                         | `datetime`        | Timestamp de criação da execução                                         |
| `updated_at`                         | `datetime`        | Timestamp da última atualização                                          |
| `completed_at`                       | `datetime \| null`| Timestamp de conclusão (falha ou sucesso)                                |
| `duration_seconds`                   | `integer \| null` | Duração total da execução em segundos                                    |
| `error_code`                         | `string \| null`  | Código de erro (quando a execução falhou)                                |
| `error_message`                      | `string \| null`  | Mensagem de erro (máx. 500 chars)                                        |
| `message_key`                        | `string \| null`  | Chave de i18n da mensagem de erro                                        |
| `message_params`                     | `object`          | Parâmetros de interpolação da mensagem i18n                              |
| `preflight_issue_codes`              | `array[string]`   | Códigos de problemas detectados na fase de preflight                     |
| `validation_issue_codes`             | `array[string]`   | Códigos de problemas de validação da sugestão                            |
| `blocking_issue_count`               | `integer`         | Quantidade de problemas bloqueantes                                      |
| `approximate_model_call_cost`        | `float \| null`   | Custo aproximado da chamada ao LLM                                       |
| `approximate_model_call_cost_currency` | `string \| null` | Moeda do custo (ex.: `"USD"`)                                           |
| `prompt_tokens`                      | `integer \| null` | Total de tokens de entrada                                               |
| `completion_tokens`                  | `integer \| null` | Total de tokens de saída                                                 |
| `total_tokens`                       | `integer \| null` | Total de tokens (entrada + saída)                                        |
| `has_raw_model_response`             | `boolean`         | `true` se há resposta bruta do modelo armazenada                        |
| `observability`                      | `object \| null`  | Métricas detalhadas de observabilidade (partições, fases, geocodificação) |

---

## Códigos de status HTTP

| Código | Significado                                                             |
|--------|-------------------------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia se nenhum run existir).     |
| `401`  | Sessão de transporte ausente ou inválida.                               |
| `403`  | Sessão sem permissão de transporte.                                     |
| `422`  | Valor de `status` inválido ou parâmetro mal formatado.                  |

---

## Side effects

Nenhum. O endpoint apenas lê dados.

---

## Exemplo cURL (ambiente local)

```bash
# Listar as 10 execuções mais recentes para a data 2026-05-26
curl -s \
  -b "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/transport/ai/runs?service_date=2026-05-26&limit=10"

# Filtrar apenas execuções com falha ou canceladas
curl -s \
  -b "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/transport/ai/runs?status=failed&status=cancelled"
```
