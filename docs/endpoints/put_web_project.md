# `PUT /api/web/project`

## Visão Geral

Define o projeto ativo do usuário autenticado. O projeto informado deve estar na lista de projetos cadastrados do usuário. Após a atualização, o campo `users.projeto` é alterado para o novo projeto.

| Atributo         | Valor                |
|------------------|----------------------|
| **Método**       | `PUT`                |
| **Path**         | `/api/web/project`   |
| **Autenticação** | Cookie de sessão obrigatório |
| **Content-Type** | `application/json`   |

---

## Autenticação

Requer sessão ativa via cookie. O servidor verifica a chave armazenada em `web_user_chave` no cookie de sessão e confirma que o usuário possui senha cadastrada. Se a sessão estiver ausente ou inválida, retorna HTTP 401.

---

## Parâmetros

### Request Body

```json
{
  "project": "Projeto Beta"
}
```

| Campo     | Tipo   | Obrigatório | Descrição                                                                     |
|-----------|--------|-------------|-------------------------------------------------------------------------------|
| `project` | string | Sim         | Nome do projeto a ser definido como ativo — entre 2 e 120 caracteres         |

**Regras de validação:**
- `project`: comprimento entre 2 e 120 caracteres; normalizado antes da validação
- O projeto deve existir no banco de dados (`ensure_known_project`)
- O usuário deve ter associação com o projeto em `user_project_memberships`. Caso contrário, retorna HTTP 409

---

## Resposta

### HTTP 200 — Projeto ativo atualizado com sucesso

```json
{
  "ok": true,
  "message": "Projeto ativo atualizado com sucesso.",
  "project": "Projeto Beta",
  "projects": ["Projeto Alpha", "Projeto Beta"],
  "active_project": "Projeto Beta"
}
```

### Campos da resposta

| Campo            | Tipo         | Descrição                                                              |
|------------------|--------------|------------------------------------------------------------------------|
| `ok`             | boolean      | Sempre `true` em caso de sucesso                                       |
| `message`        | string       | Mensagem de confirmação                                                |
| `project`        | string       | Nome do projeto que foi definido como ativo                            |
| `projects`       | list[string] | Lista completa de projetos do usuário (sem alteração)                  |
| `active_project` | string       | Projeto ativo após a atualização (mesmo valor de `project`)            |

---

## Códigos de status HTTP

| Código | Significado                                                                   |
|--------|-------------------------------------------------------------------------------|
| `200`  | Projeto ativo atualizado com sucesso                                          |
| `401`  | Sessão ausente, inválida ou expirada                                          |
| `409`  | O projeto informado não está na lista de projetos do usuário (`"O projeto informado nao pertence aos projetos cadastrados do usuario."`) |
| `422`  | Campo `project` com formato inválido ou comprimento fora dos limites          |

### Exemplos de erros

```json
// HTTP 409 — projeto não pertence ao usuário
{"detail": "O projeto informado nao pertence aos projetos cadastrados do usuario."}

// HTTP 401 — sem sessão ativa
{"detail": "Sessao do usuario invalida ou expirada"}
```

---

## Side effects

- Atualiza o campo `users.projeto` para o nome do projeto informado.
- Dispara notificação SSE para o painel admin (`notify_admin_data_changed("register")`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X PUT "http://127.0.0.1:8000/api/web/project" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"project": "Projeto Beta"}'
```
