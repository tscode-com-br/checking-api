# `DELETE /api/admin/users/{user_id}`

## Visão Geral

Remove permanentemente um usuário do sistema, incluindo seus eventos de sincronização e, quando aplicável, seus dados de solicitações de transporte. Se o usuário possuía um RFID com registro pendente, este também é excluído.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `DELETE`                                       |
| **Path**         | `/api/admin/users/{user_id}`                   |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Path Parameters

| Parâmetro  | Tipo      | Descrição                    |
|------------|-----------|------------------------------|
| `user_id`  | `integer` | ID interno do usuário a remover |

---

## Resposta

```json
{
  "ok": true,
  "user_id": 42
}
```

| Campo     | Tipo      | Descrição                             |
|-----------|-----------|---------------------------------------|
| `ok`      | `boolean` | `true` em caso de sucesso             |
| `user_id` | `integer` | ID do usuário removido                |

---

## Códigos de status HTTP

| Código | Significado                                                               |
|--------|---------------------------------------------------------------------------|
| `200`  | Usuário removido com sucesso                                              |
| `401`  | Sessão administrativa inválida ou expirada                                |
| `403`  | Sem permissão; administrador sem projetos vinculados; ou usuário possui projetos fora do escopo do admin |
| `404`  | Usuário não encontrado ou fora do escopo do administrador                 |
| `409`  | Não é possível remover o único administrador ativo do sistema             |

---

## Side effects

- Remove o registro do usuário de `users`.
- Remove todos os eventos em `user_sync_events` vinculados ao usuário.
- Remove solicitações de transporte (`transport_requests`) e atribuições (`transport_assignments`) do usuário.
- Remove o registro de `pending_registrations` para o RFID do usuário, se existente.
- Emite notificação SSE para o painel admin e grava evento em `check_events`.

> **Atenção:** Esta operação é irreversível. O histórico de check-in/check-out em `checking_history` é preservado (não é deletado junto com o usuário).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X DELETE \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/users/42
```
