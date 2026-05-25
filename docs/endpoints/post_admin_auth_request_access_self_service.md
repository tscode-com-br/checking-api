# `POST /api/admin/auth/request-access/self-service`

## Visão Geral

Solicitação de acesso admin em autoatendimento. O próprio usuário (sem sessão admin) envia o pedido. Dois caminhos são suportados:

1. **Usuário já cadastrado com senha**: apenas envia `chave`, sem os campos opcionais.
2. **Usuário novo**: envia `chave`, `nome_completo`, `projeto`, `senha` e `confirmar_senha` para se cadastrar simultaneamente.

A solicitação fica pendente até aprovação por um administrador ativo.

| Atributo         | Valor                                                   |
|------------------|---------------------------------------------------------|
| **Método**       | `POST`                                                  |
| **Path**         | `/api/admin/auth/request-access/self-service`           |
| **Autenticação** | Nenhuma (endpoint público)                              |
| **Content-Type** | `application/json`                                      |

---

## Autenticação

Endpoint público.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "nome_completo": "João da Silva",
  "projeto": "P80",
  "senha": "abc123",
  "confirmar_senha": "abc123"
}
```

| Campo            | Tipo            | Obrigatório                          | Validação                                                        |
|------------------|-----------------|--------------------------------------|------------------------------------------------------------------|
| `chave`          | `string`        | Sim                                  | 4 caracteres alfanuméricos (A-Z, 0-9). Convertido para maiúsculas. |
| `nome_completo`  | `string\|null`  | Obrigatório para usuário novo        | 3–180 caracteres. Nome normalizado (títulos).                    |
| `projeto`        | `string\|null`  | Obrigatório para usuário novo        | 2–120 caracteres. Nome de projeto normalizado.                   |
| `senha`          | `string\|null`  | Obrigatório para usuário novo        | 3–10 caracteres.                                                 |
| `confirmar_senha`| `string\|null`  | Obrigatório junto com `senha`        | Deve ser idêntica a `senha`.                                     |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Solicitacao enviada para aprovacao de um administrador."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                                          |
|--------|------------------------------------------------------------------------------------------------------|
| `200`  | Solicitação criada com sucesso.                                                                       |
| `409`  | Chave já pertence a um administrador, já existe solicitação pendente, ou usuário sem senha cadastrada. |
| `422`  | Dados inválidos (campos ausentes para cadastro novo, senhas não conferem, etc.).                      |

---

## Side effects

- Se o usuário não existe, cria um novo registro em `users` com `perfil=0` e a senha fornecida.
- Cria um registro em `admin_access_requests` com `requested_profile=1`.
- Grava evento em `check_events` com `action="admin_request"`.
- Notifica o painel admin via SSE (`reason="admin"` e `reason="event"`).

---

## Exemplo cURL (ambiente local)

```bash
# Usuário já cadastrado
curl -s -X POST http://127.0.0.1:8000/api/admin/auth/request-access/self-service \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12"}'

# Usuário novo
curl -s -X POST http://127.0.0.1:8000/api/admin/auth/request-access/self-service \
  -H "Content-Type: application/json" \
  -d '{"chave": "CD34", "nome_completo": "Maria Souza", "projeto": "P80", "senha": "abc123", "confirmar_senha": "abc123"}'
```
