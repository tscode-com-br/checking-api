# `GET /api/transport/ai/settings`

## Visão Geral

Retorna as configurações de LLM do Transport AI associadas a um projeto específico, incluindo o provedor (OpenAI ou DeepSeek), o modelo resolvido, o nível de raciocínio (`reasoning_effort`) e indicadores sobre as chaves de API armazenadas. As chaves em si nunca são retornadas — apenas um hint com os últimos 4 caracteres.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/transport/ai/settings`                   |
| **Autenticação** | Sessão de transporte obrigatória (cookie)      |
| **Content-Type** | N/A (sem corpo de requisição)                  |

---

## Autenticação

Requer sessão de transporte ativa. O cookie de sessão é verificado pela dependência `require_transport_session`. Sem sessão válida, o servidor retorna `401 Unauthorized` ou `403 Forbidden`.

---

## Parâmetros

### Query Parameters

| Parâmetro    | Tipo      | Obrigatório | Descrição                                      |
|--------------|-----------|-------------|------------------------------------------------|
| `project_id` | `integer` | Sim         | ID do projeto (≥ 1) cujas configurações buscar |

---

## Resposta

Retorna um objeto `TransportAISettingsResponse`.

```json
{
  "project_id": 42,
  "project_name": "Projeto Alpha",
  "provider": "openai",
  "resolved_model": "o3",
  "reasoning_effort": "high",
  "has_api_key": true,
  "api_key_hint": "...k9Xz",
  "has_here_api_key": true,
  "here_api_key_hint": "...mR4t"
}
```

### Campos da resposta

| Campo               | Tipo             | Descrição                                                              |
|---------------------|------------------|------------------------------------------------------------------------|
| `project_id`        | `integer \| null` | ID do projeto consultado                                               |
| `project_name`      | `string \| null`  | Nome do projeto (máx. 120 chars)                                       |
| `provider`          | `string`          | Provedor de LLM ativo: `"openai"` ou `"deepseek"`                      |
| `resolved_model`    | `string`          | Nome do modelo LLM resolvido para este projeto                         |
| `reasoning_effort`  | `string`          | Nível de raciocínio configurado (atualmente sempre `"high"`)           |
| `has_api_key`       | `boolean`         | `true` se uma chave de API criptografada está armazenada               |
| `api_key_hint`      | `string \| null`  | Últimos 4 caracteres da chave de API (ex.: `"...k9Xz"`)               |
| `has_here_api_key`  | `boolean`         | `true` se a chave do HERE Maps está armazenada                         |
| `here_api_key_hint` | `string \| null`  | Últimos 4 caracteres da chave HERE Maps                                |

---

## Códigos de status HTTP

| Código | Significado                                                                   |
|--------|-------------------------------------------------------------------------------|
| `200`  | Configurações retornadas com sucesso.                                         |
| `401`  | Sessão de transporte ausente ou inválida.                                     |
| `403`  | Sessão sem permissão de transporte.                                           |
| `404`  | Projeto não encontrado. `error_code`: `transport_ai_settings_project_not_found` |
| `409`  | Configurações inválidas ou inconsistentes. `error_code`: `transport_ai_settings_validation_failed` |
| `503`  | Serviço de criptografia indisponível. `error_code`: `transport_ai_settings_encryption_unavailable` |

### Estrutura do corpo de erro (4xx/5xx)

```json
{
  "message": "Projeto de Transport AI não encontrado.",
  "message_key": "ai.settingsProjectMissing",
  "message_params": {},
  "error_code": "transport_ai_settings_project_not_found",
  "issues": [
    {
      "code": "transport_ai_settings_project_not_found",
      "message": "Projeto de Transport AI não encontrado.",
      "project_id": 42
    }
  ],
  "technical_detail": "Projeto de Transport AI não encontrado."
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
  "http://127.0.0.1:8000/api/transport/ai/settings?project_id=42"
```
