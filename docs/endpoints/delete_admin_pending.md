# `DELETE /api/admin/pending/{pending_id}`

## Visão Geral

Remove um registro pendente de cadastro RFID da fila. Use este endpoint para descartar RFIDs inválidos, cartões de teste ou apresentações acidentais que não devem resultar em cadastro.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `DELETE`                                       |
| **Path**         | `/api/admin/pending/{pending_id}`              |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Path Parameters

| Parâmetro    | Tipo      | Descrição                                |
|--------------|-----------|------------------------------------------|
| `pending_id` | `integer` | ID do registro pendente a ser removido   |

---

## Resposta

```json
{
  "ok": true,
  "id": 7
}
```

| Campo | Tipo      | Descrição                                |
|-------|-----------|------------------------------------------|
| `ok`  | `boolean` | `true` em caso de sucesso                |
| `id`  | `integer` | ID do registro pendente removido         |

---

## Códigos de status HTTP

| Código | Significado                                                            |
|--------|------------------------------------------------------------------------|
| `200`  | Registro pendente removido com sucesso                                 |
| `401`  | Sessão administrativa inválida ou expirada                             |
| `403`  | Usuário não possui permissão de administrador                          |
| `404`  | Registro pendente não encontrado ou fora do escopo do administrador    |

---

## Side effects

- Remove o registro de `pending_registrations`.
- Emite notificação SSE para o painel admin (`notify_admin_data_changed`).
- Grava evento em `check_events` com `action="pending"`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X DELETE \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/pending/7
```
