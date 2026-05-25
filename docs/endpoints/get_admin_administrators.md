# `GET /api/admin/administrators`

## Visão Geral

Retorna a lista unificada de administradores ativos e solicitações de acesso pendentes, com as ações disponíveis para o admin autenticado sobre cada item.

| Atributo         | Valor                                               |
|------------------|-----------------------------------------------------|
| **Método**       | `GET`                                               |
| **Path**         | `/api/admin/administrators`                         |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`). Administradores com escopo limitado recebem `403`.

---

## Parâmetros

Nenhum.

---

## Resposta

**HTTP 200**

```json
[
  {
    "id": 7,
    "row_type": "admin",
    "chave": "AB12",
    "nome": "João da Silva",
    "perfil": 1,
    "projects": ["P80", "P83"],
    "status": "active",
    "status_label": "Ativo",
    "can_revoke": true,
    "can_approve": false,
    "can_reject": false,
    "can_set_password": false
  },
  {
    "id": 99,
    "row_type": "request",
    "chave": "CD34",
    "nome": "Maria Souza",
    "perfil": null,
    "projects": [],
    "status": "pending",
    "status_label": "Aguardando aprovação",
    "can_revoke": false,
    "can_approve": true,
    "can_reject": true,
    "can_set_password": false
  },
  {
    "id": 12,
    "row_type": "admin",
    "chave": "EF56",
    "nome": "Carlos Lima",
    "perfil": 1,
    "projects": ["P80"],
    "status": "password_reset_requested",
    "status_label": "Aguardando nova senha",
    "can_revoke": true,
    "can_approve": false,
    "can_reject": false,
    "can_set_password": true
  }
]
```

### Campos de cada item

| Campo          | Tipo                                       | Descrição                                                               |
|----------------|--------------------------------------------|-------------------------------------------------------------------------|
| `id`           | `integer`                                  | ID do usuário (para `row_type="admin"`) ou da solicitação (para `row_type="request"`). |
| `row_type`     | `"admin"\|"request"`                       | Tipo da linha: administrador ativo ou solicitação pendente.             |
| `chave`        | `string`                                   | Chave de 4 caracteres.                                                  |
| `nome`         | `string`                                   | Nome completo.                                                          |
| `perfil`       | `integer\|null`                            | Perfil numérico (somente para `row_type="admin"`).                      |
| `projects`     | `string[]`                                 | Projetos associados ao administrador.                                   |
| `status`       | `"active"\|"pending"\|"password_reset_requested"` | Status atual.                                                  |
| `status_label` | `string`                                   | Rótulo legível do status.                                               |
| `can_revoke`   | `boolean`                                  | Se o admin atual pode revogar este administrador.                       |
| `can_approve`  | `boolean`                                  | Se o admin atual pode aprovar esta solicitação.                         |
| `can_reject`   | `boolean`                                  | Se o admin atual pode rejeitar esta solicitação.                        |
| `can_set_password` | `boolean`                              | Se o admin atual pode definir nova senha para este admin.               |

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Lista retornada com sucesso.                              |
| `401`  | Sessão ausente ou inválida.                               |
| `403`  | Sessão com escopo limitado — acesso negado.               |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/administrators
```
