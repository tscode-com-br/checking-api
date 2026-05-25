# `DELETE /api/admin/locations/{location_id}`

## Visão Geral

Remove permanentemente uma localização gerenciada do sistema. Após a remoção, nenhum check-in ou check-out poderá usar esta localização como referência GPS.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `DELETE`                                       |
| **Path**         | `/api/admin/locations/{location_id}`           |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo      | Descrição                                  |
|---------------|-----------|--------------------------------------------|
| `location_id` | `integer` | ID interno da localização a ser removida   |

---

## Resposta

```json
{
  "ok": true,
  "message": "Localizacao removida com sucesso.",
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Códigos de status HTTP

| Código | Significado                                                              |
|--------|--------------------------------------------------------------------------|
| `200`  | Localização removida com sucesso                                         |
| `401`  | Sessão administrativa inválida ou expirada                               |
| `403`  | Usuário não possui permissão de administrador ou localização fora do escopo |
| `404`  | Localização não encontrada                                               |

---

## Side effects

- Remove o registro de `managed_locations`.
- Emite notificação SSE para o painel admin.
- Grava evento em `check_events` com `action="location"` e `status="removed"`.

> **Atenção:** Eventos históricos de check-in/check-out que referenciam o `local` desta localização não são afetados — o campo `local` em `check_events` é armazenado como string, não como FK.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X DELETE \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/locations/1
```
