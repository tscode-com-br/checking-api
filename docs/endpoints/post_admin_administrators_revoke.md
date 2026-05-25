# `POST /api/admin/administrators/{admin_id}/revoke`

## Visão Geral

Revoga o acesso administrativo de um administrador, removendo o dígito de acesso admin do seu perfil numérico. O usuário continua existindo no sistema, mas perde o acesso ao painel admin.

| Atributo         | Valor                                                     |
|------------------|-----------------------------------------------------------|
| **Método**       | `POST`                                                    |
| **Path**         | `/api/admin/administrators/{admin_id}/revoke`             |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |
| **Content-Type** | Nenhum (sem corpo)                                        |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`).

---

## Parâmetros

### Path Parameters

| Parâmetro  | Tipo      | Descrição                           |
|------------|-----------|-------------------------------------|
| `admin_id` | `integer` | ID (`users.id`) do administrador a revogar. |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Administrador revogado com sucesso."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                                   |
|--------|-----------------------------------------------------------------------------------------------|
| `200`  | Acesso revogado com sucesso.                                                                  |
| `401`  | Sessão ausente ou inválida.                                                                   |
| `403`  | Sessão com escopo limitado — acesso negado.                                                   |
| `404`  | Administrador não encontrado ou não possui perfil admin.                                      |
| `409`  | Auto-revogação não permitida (não é possível revogar o próprio acesso); ou é o último administrador ativo do sistema. |

---

## Regras de negócio

- Um administrador **não pode revogar o próprio acesso** (`admin_id == current_admin.id` → `409`).
- O sistema **não permite remover o último administrador ativo** — deve haver sempre ao menos um (`409`).
- A contagem de administradores ativos considera todos os usuários com o dígito de acesso admin no perfil.

---

## Side effects

- Remove o dígito `ADMIN_ACCESS_DIGIT` do campo `users.perfil` (sem deletar o usuário).
- Grava evento em `check_events` com `action="admin_access"` e `status="removed"`.
- Notifica o painel admin via SSE (`reason="admin"` e `reason="event"`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/administrators/7/revoke
```
