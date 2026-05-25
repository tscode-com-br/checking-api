# `GET /api/transport/ai/preflight`

## Visão Geral

Verifica se o ambiente de execução do Transport AI está corretamente configurado para realizar cálculos de rotas. O endpoint inspeciona as configurações do LLM (provedor, chave de API, modelo), a disponibilidade do provedor de rotas e outras dependências necessárias para que um cálculo possa ser iniciado com sucesso.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/transport/ai/preflight`                  |
| **Autenticação** | Sessão de transporte obrigatória (cookie)      |
| **Content-Type** | N/A (sem corpo de requisição)                  |

---

## Autenticação

Requer sessão de transporte ativa. O cookie de sessão é verificado pela dependência `require_transport_session`. Sem sessão válida, o servidor retorna `401 Unauthorized` ou `403 Forbidden`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou corpo de requisição.

---

## Resposta

Retorna um objeto `TransportAIPreflightCheckResult` com o resultado geral (`ok`) e a lista de problemas encontrados (`issues`).

```json
{
  "ok": true,
  "issues": []
}
```

### Exemplo com problemas de configuração

```json
{
  "ok": false,
  "issues": [
    {
      "code": "transport_ai_llm_api_key_missing",
      "message": "A chave de API do LLM não está configurada.",
      "message_key": "ai.settingsKeyRequired",
      "message_params": {},
      "blocking": true,
      "setting_name": "api_key"
    },
    {
      "code": "transport_ai_here_api_key_missing",
      "message": "A chave de API do provedor de rotas HERE não está configurada.",
      "message_key": "ai.hereKeyRequired",
      "message_params": {},
      "blocking": false,
      "setting_name": "here_api_key"
    }
  ]
}
```

### Campos da resposta

| Campo    | Tipo                               | Descrição                                                              |
|----------|------------------------------------|------------------------------------------------------------------------|
| `ok`     | `boolean`                          | `true` se nenhum problema bloqueante foi encontrado; `false` caso contrário |
| `issues` | `array[TransportAIPreflightIssue]` | Lista de problemas detectados (pode ser vazia)                         |

### Campos de `TransportAIPreflightIssue`

| Campo           | Tipo              | Descrição                                                                 |
|-----------------|-------------------|---------------------------------------------------------------------------|
| `code`          | `string`          | Código de identificação do problema (ex.: `transport_ai_llm_api_key_missing`) |
| `message`       | `string`          | Mensagem descritiva do problema (máx. 500 chars)                          |
| `message_key`   | `string \| null`  | Chave de i18n para uso no frontend                                        |
| `message_params`| `object`          | Parâmetros de interpolação da mensagem i18n                               |
| `blocking`      | `boolean`         | Se `true`, o problema impede o início de um cálculo de rotas              |
| `setting_name`  | `string \| null`  | Nome da configuração relacionada ao problema (quando aplicável)           |

---

## Códigos de status HTTP

| Código | Significado                                                  |
|--------|--------------------------------------------------------------|
| `200`  | Verificação concluída. O campo `ok` indica se há problemas.  |
| `401`  | Sessão de transporte ausente ou inválida.                    |
| `403`  | Sessão sem permissão de transporte.                          |

---

## Side effects

Nenhum. O endpoint apenas lê as configurações persistidas no banco de dados e no ambiente.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -b "session=<cookie_de_sessao>" \
  http://127.0.0.1:8000/api/transport/ai/preflight
```
