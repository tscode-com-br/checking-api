# `POST /api/transport/auth/verify`

## Visão Geral

Autentica um usuário com chave (`chave`) e senha (`senha`). Em caso de sucesso, cria a sessão de transporte no cookie e retorna os dados de identidade do usuário. Em caso de falha, limpa a sessão existente e retorna `authenticated: false` com detalhes do erro.

| Atributo         | Valor                            |
|------------------|----------------------------------|
| **Método**       | `POST`                           |
| **Path**         | `/api/transport/auth/verify`     |
| **Autenticação** | Nenhuma — endpoint de login      |
| **Content-Type** | `application/json`               |

---

## Autenticação

Não requer sessão prévia. Após autenticação bem-sucedida, o servidor grava `transport_user_id` no cookie de sessão (SessionMiddleware). Requisições subsequentes utilizam esse cookie para identificar o usuário.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "senha": "minha_senha_secreta"
}
```

| Campo   | Tipo     | Obrigatório | Regras                                                                 |
|---------|----------|-------------|------------------------------------------------------------------------|
| `chave` | `string` | Sim         | Exatamente 4 caracteres alfanuméricos. Convertido para maiúsculas.     |
| `senha` | `string` | Sim         | Entre 1 e 255 caracteres.                                              |

---

## Resposta

**Sucesso (`authenticated: true`):**

```json
{
  "authenticated": true,
  "user": {
    "id": 42,
    "chave": "AB12",
    "nome_completo": "João da Silva",
    "perfil": 1
  },
  "message": "Transport access granted.",
  "message_key": "status.accessGranted",
  "message_params": {},
  "error_code": null,
  "issues": []
}
```

**Credenciais inválidas:**

```json
{
  "authenticated": false,
  "user": null,
  "message": "Invalid key or password.",
  "message_key": "auth.invalidCredentials",
  "error_code": "transport_auth_invalid_credentials",
  "issues": [
    {"code": "transport_auth_invalid_credentials"}
  ]
}
```

**Usuário sem acesso de transporte:**

```json
{
  "authenticated": false,
  "user": null,
  "message": "This user does not have transport access.",
  "message_key": "auth.noAccess",
  "error_code": "transport_auth_access_denied",
  "issues": [
    {"code": "transport_auth_access_denied"}
  ]
}
```

### Campos da resposta

| Campo              | Tipo           | Descrição                                                    |
|--------------------|----------------|--------------------------------------------------------------|
| `authenticated`    | `bool`         | `true` se o login foi bem-sucedido.                          |
| `user`             | `object\|null` | Dados do usuário autenticado; `null` em caso de falha.       |
| `message`          | `string\|null` | Mensagem legível do resultado.                               |
| `message_key`      | `string\|null` | Chave i18n para tradução no frontend.                        |
| `error_code`       | `string\|null` | Código de erro estruturado em caso de falha.                 |
| `issues`           | `array`        | Lista de problemas com campo `code`.                         |

---

## Códigos de status HTTP

| Código | Significado                                         |
|--------|-----------------------------------------------------|
| `200`  | Sempre retornado (sucesso ou falha de autenticação). O campo `authenticated` indica o resultado. |

---

## Side effects

- Em caso de sucesso: grava `transport_user_id` na sessão (cookie).
- Em caso de falha: limpa qualquer sessão de transporte existente.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -c cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "senha": "minha_senha"}' \
  http://127.0.0.1:8000/api/transport/auth/verify | python -m json.tool
```

O arquivo `cookies.txt` armazena o cookie de sessão para uso nas requisições subsequentes.
