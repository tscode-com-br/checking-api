# `DELETE /api/admin/projects/{project_id}`

## Visão Geral

Remove permanentemente um projeto do sistema. Antes da remoção, usuários e localizações vinculados ao projeto são reatribuídos ao próximo projeto disponível. Não é possível remover o último projeto cadastrado ou um projeto que possua usuários (não-admin) sem outros projetos.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `DELETE`                                       |
| **Path**         | `/api/admin/projects/{project_id}`             |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Path Parameters

| Parâmetro    | Tipo      | Descrição              |
|--------------|-----------|------------------------|
| `project_id` | `integer` | ID interno do projeto  |

---

## Resposta

```json
{
  "ok": true,
  "message": "Projeto removido com sucesso.",
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
| `200`  | Projeto removido com sucesso                                             |
| `401`  | Sessão administrativa inválida ou expirada                               |
| `403`  | Usuário não possui permissão de administrador                            |
| `404`  | Projeto não encontrado                                                   |
| `409`  | Não é possível remover o último projeto; ou há usuários não-admin vinculados exclusivamente a este projeto |

---

## Side effects

- Remove o registro em `projects`.
- **Usuários vinculados:** reatribuídos ao próximo projeto disponível em ordem alfabética. Usuários exclusivos do projeto removido e sem perfil de admin causam `409` (precisam ser removidos ou migrados manualmente antes).
- **Administradores vinculados:** se um administrador estava exclusivamente no projeto removido, é reatribuído ao projeto de fallback e o escopo `admin_monitored_projects_json` é limpo.
- **Localizações vinculadas:** o projeto é substituído pelo projeto de fallback em `managed_locations.projects_json`.
- Emite notificação SSE para o painel admin e grava evento em `check_events`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X DELETE \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/projects/3
```
