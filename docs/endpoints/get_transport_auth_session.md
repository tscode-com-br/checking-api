# `GET /api/transport/auth/session`

## Visão Geral

Verifica se existe uma sessão de transporte ativa no cookie da requisição. Retorna o estado de autenticação e, quando autenticado, os dados de identidade do usuário logado.

| Atributo         | Valor                                                         |
|------------------|---------------------------------------------------------------|
| **Método**       | `GET`                                                         |
| **Path**         | `/api/transport/auth/session`                                 |
| **Autenticação** | Nenhuma — endpoint público para checar o estado da sessão     |
| **Content-Type** | `application/json` (resposta)                                 |

---

## Autenticação

Não requer autenticação prévia. O endpoint lê o cookie de sessão (gerenciado por Starlette/FastAPI SessionMiddleware) e tenta resolver o `transport_user_id` armazenado nele. Se o ID não existir ou o usuário não tiver acesso de transporte, retorna `authenticated: false`.

---

## Parâmetros

Nenhum parâmetro de query, path ou corpo de requisição.

---

## Resposta

```json
{
  "authenticated": true,
  "user": {
    "id": 42,
    "chave": "AB12",
    "nome_completo": "João da Silva",
    "perfil": 1
  },
  "message": null,
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

Quando não autenticado:

```json
{
  "authenticated": false,
  "user": null,
  "message": null,
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

### Campos da resposta

| Campo              | Tipo            | Descrição                                                             |
|--------------------|-----------------|-----------------------------------------------------------------------|
| `authenticated`    | `bool`          | `true` se há sessão válida de transporte.                             |
| `user`             | `object\|null`  | Identidade do usuário logado; `null` se não autenticado.              |
| `user.id`          | `int`           | ID do registro na tabela `users`.                                     |
| `user.chave`       | `string`        | Chave de 4 caracteres alfanuméricos do usuário.                       |
| `user.nome_completo` | `string`      | Nome completo do usuário.                                             |
| `user.perfil`      | `int`           | Perfil do usuário (1 = admin, 9 = super-admin, etc.).                 |
| `message`          | `string\|null`  | Mensagem de status; normalmente `null` neste endpoint.                |
| `message_key`      | `string\|null`  | Chave i18n da mensagem.                                               |
| `error_code`       | `string\|null`  | Código de erro estruturado; normalmente `null` neste endpoint.        |
| `issues`           | `array`         | Lista de problemas estruturados; normalmente vazia.                   |

---

## Códigos de status HTTP

| Código | Significado                                 |
|--------|---------------------------------------------|
| `200`  | Sempre retornado (autenticado ou não).      |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<valor_do_cookie>" \
  http://127.0.0.1:8000/api/transport/auth/session | python -m json.tool
```
