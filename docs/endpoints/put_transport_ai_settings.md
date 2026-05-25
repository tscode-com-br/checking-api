# `PUT /api/transport/ai/settings`

## Visão Geral

Cria ou atualiza as configurações de LLM do Transport AI para um projeto específico. O endpoint suporta configurar o provedor (`openai` ou `deepseek`), a chave de API do LLM e opcionalmente a chave de API do HERE Maps (provedor de rotas). As chaves são criptografadas antes de serem persistidas. Após a atualização, registra um evento de auditoria nos logs de observabilidade e notifica o painel administrativo via SSE.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `PUT`                                          |
| **Path**         | `/api/transport/ai/settings`                   |
| **Autenticação** | Sessão de transporte obrigatória (cookie)      |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer sessão de transporte ativa. O cookie de sessão é verificado pela dependência `require_transport_session`. O usuário autenticado é registrado como ator da alteração (`actor_admin_user`) via `ensure_transport_ai_actor_admin_user`. Sem sessão válida, o servidor retorna `401 Unauthorized` ou `403 Forbidden`.

---

## Parâmetros

### Request Body

```json
{
  "project_id": 42,
  "provider": "openai",
  "api_key": "sk-proj-...",
  "here_api_key": "abc123xyz"
}
```

| Campo         | Tipo             | Obrigatório | Descrição                                                                      |
|---------------|------------------|-------------|--------------------------------------------------------------------------------|
| `project_id`  | `integer`        | Sim         | ID do projeto (≥ 1) para o qual salvar as configurações                        |
| `provider`    | `string`         | Sim         | Provedor de LLM: `"openai"` ou `"deepseek"`                                   |
| `api_key`     | `string \| null` | Condicional | Chave de API do LLM. Obrigatória na primeira configuração ou ao trocar provedor |
| `here_api_key`| `string \| null` | Não         | Chave de API do HERE Maps (provedor de cálculo de rotas). Global para todos os projetos |

**Regras de validação:**
- `api_key` é obrigatória quando ainda não há chave armazenada.
- `api_key` é obrigatória ao mudar de provedor (ex.: de `openai` para `deepseek`).
- Se `api_key` for `null` e já houver uma chave criptografada armazenada, a chave existente é mantida.
- `here_api_key` é opcional; quando fornecida, atualiza a configuração global (não por projeto).

---

## Resposta

Em caso de sucesso, retorna o objeto `TransportAISettingsResponse` com as configurações atualizadas (mesmo formato do `GET /api/transport/ai/settings`).

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

---

## Códigos de status HTTP

| Código | Significado                                                                   |
|--------|-------------------------------------------------------------------------------|
| `200`  | Configurações salvas com sucesso. Retorna as configurações atualizadas.       |
| `401`  | Sessão de transporte ausente ou inválida.                                     |
| `403`  | Sessão sem permissão de transporte.                                           |
| `404`  | Projeto não encontrado. `error_code`: `transport_ai_settings_project_not_found` |
| `409`  | Erro de validação (ex.: chave obrigatória ausente, provedor inválido). `error_code`: `transport_ai_settings_validation_failed` |
| `422`  | Corpo da requisição com estrutura inválida (validação Pydantic).              |
| `503`  | Serviço de criptografia indisponível. `error_code`: `transport_ai_settings_encryption_unavailable` |

### Estrutura do corpo de erro (4xx/5xx)

```json
{
  "message": "A chave de API do Transport AI é obrigatória.",
  "message_key": "ai.settingsKeyRequired",
  "message_params": {},
  "error_code": "transport_ai_settings_validation_failed",
  "issues": [
    {
      "code": "transport_ai_settings_validation_failed",
      "message": "A chave de API do Transport AI é obrigatória."
    }
  ],
  "technical_detail": "Transport AI API key is required."
}
```

---

## Side effects

- Persiste as configurações de LLM criptografadas na tabela `transport_ai_project_llm_settings` (por projeto) ou `transport_ai_llm_settings` (global para HERE key).
- Se `here_api_key` for fornecida, atualiza também o valor em memória (`settings.here_api_key`).
- Registra um evento de auditoria via `record_transport_ai_settings_update` no log de observabilidade.
- Em caso de falha, registra um evento de falha via `record_transport_ai_settings_failure`.
- Chama `notify_admin_data_changed("event")` para notificar o painel admin via SSE.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X PUT \
  -b "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 42, "provider": "openai", "api_key": "sk-proj-...", "here_api_key": null}' \
  http://127.0.0.1:8000/api/transport/ai/settings
```
