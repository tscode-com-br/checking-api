# `PUT /api/web/user-projects`

## Visão Geral

Substitui completamente os projetos associados ao usuário autenticado. A lista de projetos informada substitui todas as associações existentes em `user_project_memberships`.

| Atributo         | Valor                      |
|------------------|----------------------------|
| **Método**       | `PUT`                      |
| **Path**         | `/api/web/user-projects`   |
| **Autenticação** | Cookie de sessão obrigatório |
| **Content-Type** | `application/json`         |

---

## Autenticação

Requer sessão ativa via cookie. O servidor verifica a chave armazenada em `web_user_chave` no cookie de sessão e confirma que o usuário possui senha cadastrada. Se a sessão estiver ausente ou inválida, retorna HTTP 401.

---

## Parâmetros

### Request Body

```json
{
  "projects": ["Projeto Alpha", "Projeto Beta"]
}
```

| Campo      | Tipo         | Obrigatório | Descrição                                                                |
|------------|--------------|-------------|--------------------------------------------------------------------------|
| `projects` | list[string] | Sim         | Lista de nomes de projetos — deve conter ao menos 1 projeto              |

**Regras de validação:**
- A lista não pode ser vazia. Se vazia, retorna HTTP 422 com `"Selecione ao menos um projeto para o usuário."`
- Nomes de projetos são normalizados (capitalização e espaços)
- Projetos informados que não existirem no banco são criados automaticamente via `ensure_known_project`

---

## Resposta

### HTTP 200 — Projetos atualizados com sucesso

```json
{
  "ok": true,
  "message": "Projetos atualizados com sucesso.",
  "projects": ["Projeto Alpha", "Projeto Beta"],
  "active_project": "Projeto Alpha"
}
```

### Campos da resposta

| Campo            | Tipo         | Descrição                                                                     |
|------------------|--------------|-------------------------------------------------------------------------------|
| `ok`             | boolean      | Sempre `true` em caso de sucesso                                              |
| `message`        | string       | Mensagem de confirmação                                                       |
| `projects`       | list[string] | Lista normalizada dos projetos após a atualização                             |
| `active_project` | string       | Projeto ativo atual do usuário (campo `users.projeto`, não alterado por este endpoint) |

---

## Códigos de status HTTP

| Código | Significado                                                         |
|--------|---------------------------------------------------------------------|
| `200`  | Projetos atualizados com sucesso                                    |
| `401`  | Sessão ausente, inválida ou expirada                                |
| `422`  | Lista vazia ou campos com formato inválido                          |

### Exemplo de erro

```json
// HTTP 422 — lista vazia
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "projects"],
      "msg": "Value error, Selecione ao menos um projeto para o usuário."
    }
  ]
}
```

---

## Side effects

- Remove todas as associações existentes em `user_project_memberships` para o usuário e as recria com os novos projetos.
- **Não** altera o projeto ativo (`users.projeto`) — use `PUT /api/web/project` para isso.
- Dispara notificação SSE para o painel admin (`notify_admin_data_changed("register")`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X PUT "http://127.0.0.1:8000/api/web/user-projects" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"projects": ["Projeto Alpha", "Projeto Beta"]}'
```
