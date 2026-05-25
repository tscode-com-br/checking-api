# `GET /api/admin/accidents/wizard/projects`

## Visão Geral

Retorna a lista de projetos disponíveis para uso no wizard de abertura de acidente. O frontend usa este endpoint para popular o seletor de projeto no modal de abertura do Modo Acidente.

| Atributo         | Valor                                              |
|------------------|----------------------------------------------------|
| **Método**       | `GET`                                              |
| **Path**         | `/api/admin/accidents/wizard/projects`             |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`).

---

## Parâmetros

Nenhum.

---

## Resposta

**HTTP 200**

```json
[
  { "id": 1, "name": "P80" },
  { "id": 2, "name": "P83" },
  { "id": 3, "name": "ESCRITORIO" }
]
```

| Campo  | Tipo      | Descrição               |
|--------|-----------|-------------------------|
| `id`   | `integer` | ID do projeto.          |
| `name` | `string`  | Nome normalizado (maiúsculas). |

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia).             |
| `401`  | Sessão ausente ou inválida.                               |
| `403`  | Sessão com escopo limitado — acesso negado.               |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/accidents/wizard/projects
```
