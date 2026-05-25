# `POST /api/admin/administrators/{admin_id}/set-password`

## Visão Geral

Define uma nova senha para um administrador que possui reset pendente (senha `null`). Operação para ser usada por um administrador ativo quando outro admin solicitou reset via `POST /api/admin/auth/request-password-reset`.

| Atributo         | Valor                                                    |
|------------------|----------------------------------------------------------|
| **Método**       | `POST`                                                   |
| **Path**         | `/api/admin/administrators/{admin_id}/set-password`      |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |
| **Content-Type** | `application/json`                                       |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`). O admin que executa a operação pode definir senha para qualquer outro admin (exceto para si mesmo via este endpoint — use `POST /api/admin/auth/change-password` para isso).

---

## Parâmetros

### Path Parameters

| Parâmetro  | Tipo      | Descrição                                          |
|------------|-----------|----------------------------------------------------|
| `admin_id` | `integer` | ID (`users.id`) do administrador com reset pendente. |

### Request Body

```json
{
  "nova_senha": "nova_senha_aqui"
}
```

| Campo       | Tipo     | Obrigatório | Validação                |
|-------------|----------|-------------|--------------------------|
| `nova_senha`| `string` | Sim         | 3–20 caracteres.         |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Nova senha cadastrada com sucesso."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                                |
|--------|--------------------------------------------------------------------------------------------|
| `200`  | Senha definida com sucesso.                                                                |
| `401`  | Sessão ausente ou inválida.                                                                |
| `403`  | Sessão com escopo limitado — acesso negado.                                                |
| `404`  | Administrador não encontrado ou não possui perfil admin.                                   |
| `409`  | O administrador alvo não possui reset pendente (sua senha já está definida). Use `change-password` para alterar uma senha ativa. |
| `422`  | Formato inválido (senha muito curta/longa).                                                |

---

## Fluxo completo de reset

1. Admin solicita reset: `POST /api/admin/auth/request-password-reset` com `{"chave": "AB12"}` → senha é removida (`null`).
2. Outro admin visualiza o status `"password_reset_requested"` em `GET /api/admin/administrators`.
3. Outro admin define nova senha: `POST /api/admin/administrators/{id}/set-password`.

---

## Side effects

- Atualiza `users.senha` com o hash bcrypt da nova senha.
- Grava evento em `check_events` com `action="password"` e `status="updated"`.
- Notifica o painel admin via SSE (`reason="admin"` e `reason="event"`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/administrators/7/set-password \
  -H "Content-Type: application/json" \
  -d '{"nova_senha": "nova123"}'
```
