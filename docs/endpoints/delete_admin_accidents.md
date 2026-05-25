# `DELETE /api/admin/accidents/{accident_id}`

## Visão Geral

Remove permanentemente um acidente encerrado e todos os seus dados associados (relatórios de usuários, vídeos, archive). Também remove os objetos correspondentes no armazenamento remoto (DO Spaces). Operação irreversível — restrita ao super admin (`perfil=9`).

| Atributo         | Valor                                               |
|------------------|-----------------------------------------------------|
| **Método**       | `DELETE`                                            |
| **Path**         | `/api/admin/accidents/{accident_id}`                |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`). Adicionalmente, apenas usuários com `perfil=9` (super admin) podem executar esta operação — outros perfis recebem `403`.

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo      | Descrição                           |
|---------------|-----------|-------------------------------------|
| `accident_id` | `integer` | ID do acidente encerrado a remover. |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Acidente removido com sucesso."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                               |
|--------|-------------------------------------------------------------------------------------------|
| `200`  | Acidente removido com sucesso.                                                            |
| `401`  | Sessão ausente ou inválida.                                                               |
| `403`  | Perfil insuficiente — apenas `perfil=9` pode remover acidentes; ou escopo limitado.       |
| `404`  | Acidente não encontrado.                                                                  |
| `409`  | Acidente ainda está em curso (não encerrado). Encerre o Modo Acidente antes de deletar.  |

---

## Side effects

- Remove o registro de `accidents` do banco (cascade remove: `accident_user_reports`, `accident_video_uploads`, `accident_archives`, `accident_call_logs`, `accident_call_notifications`).
- Remove o prefixo `accidents/{accident_number_label}/` do armazenamento remoto (DO Spaces) ou local.
- Grava evento em `check_events` com `action="accident_delete"` e `source="admin"`.
- Notifica painel admin e Check Web via SSE com `reason="accident_closed"` e `deleted_accident_id`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X DELETE http://127.0.0.1:8000/api/admin/accidents/5
```
