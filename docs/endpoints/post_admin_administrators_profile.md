# `POST /api/admin/administrators/{admin_id}/profile`

## Visão Geral

Atualiza o perfil numérico e/ou os projetos associados a um administrador existente. Permite promover, rebaixar ou ajustar o escopo de acesso de outro administrador.

| Atributo         | Valor                                                     |
|------------------|-----------------------------------------------------------|
| **Método**       | `POST`                                                    |
| **Path**         | `/api/admin/administrators/{admin_id}/profile`            |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |
| **Content-Type** | `application/json`                                        |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`). Qualquer admin com escopo completo pode alterar o perfil de outros administradores.

---

## Parâmetros

### Path Parameters

| Parâmetro  | Tipo      | Descrição                          |
|------------|-----------|------------------------------------|
| `admin_id` | `integer` | ID (`users.id`) do administrador a atualizar. |

### Request Body

```json
{
  "perfil": 1,
  "projects": ["P80", "P83"]
}
```

| Campo      | Tipo           | Obrigatório | Validação                                                                             |
|------------|----------------|-------------|---------------------------------------------------------------------------------------|
| `perfil`   | `integer`      | Sim         | Inteiro entre 0 e 999. O valor é normalizado pelo sistema para refletir os dígitos de perfil válidos. |
| `projects` | `string[]\|null` | Não         | Lista de nomes de projetos (mín. 1 item se fornecida). Deve conter projetos existentes no catálogo. |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Configuracoes do administrador atualizadas com sucesso."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                     |
|--------|---------------------------------------------------------------------------------|
| `200`  | Perfil atualizado com sucesso.                                                  |
| `401`  | Sessão ausente ou inválida.                                                     |
| `403`  | Sessão com escopo limitado — acesso negado.                                     |
| `404`  | Administrador não encontrado ou não possui perfil admin.                        |
| `422`  | Dados inválidos: projetos não existem no catálogo, lista de projetos vazia, etc. |

---

## Side effects

- Atualiza `users.perfil` com o perfil normalizado.
- Se `projects` foi fornecido, substitui completamente os registros de memberships em `user_project_memberships`.
- Limpa `admin_monitored_projects_json` (resetando o escopo de monitoramento para todos os projetos do admin).
- Grava evento em `check_events` com `action="admin_access"` e `status="updated"`, incluindo os projetos anteriores e novos nos detalhes.
- Notifica o painel admin via SSE (`reason="admin"` e `reason="event"`).

---

## Exemplo cURL (ambiente local)

```bash
# Atualizar apenas o perfil
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/administrators/7/profile \
  -H "Content-Type: application/json" \
  -d '{"perfil": 1}'

# Atualizar perfil e projetos
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/administrators/7/profile \
  -H "Content-Type: application/json" \
  -d '{"perfil": 1, "projects": ["P80", "P83"]}'
```
