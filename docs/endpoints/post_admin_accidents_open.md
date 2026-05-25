# `POST /api/admin/accidents/open`

## Visão Geral

Abre um novo acidente (Modo Acidente) a partir do painel admin. Apenas um acidente pode estar ativo por vez no sistema — tentar abrir um segundo retorna `409`.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `POST`                                  |
| **Path**         | `/api/admin/accidents/open`             |
| **Autenticação** | Sessão admin com identidade completa (`require_admin_identity`) |
| **Content-Type** | `application/json`                      |

---

## Autenticação

Requer `require_admin_identity`, que retorna um `AdminActorIdentity` contendo tanto o `User` (FK → `users.id`) quanto o `AdminUser` (FK → `admin_users.id`). Isso garante que a coluna `opened_by_admin_id` receba um valor válido em produção (PostgreSQL com FK enforçada).

---

## Parâmetros

### Request Body

```json
{
  "project_id": 3,
  "location_id": 7,
  "description": "Colisão na plataforma norte"
}
```

ou com local personalizado:

```json
{
  "project_id": 3,
  "custom_location_name": "Ponto de Embarque Sul",
  "description": ""
}
```

| Campo                 | Tipo           | Obrigatório  | Validação                                                                      |
|-----------------------|----------------|--------------|--------------------------------------------------------------------------------|
| `project_id`          | `integer`      | Sim          | ID de um projeto existente.                                                    |
| `location_id`         | `integer\|null`| Condicional  | ID de local cadastrado. Mutuamente exclusivo com `custom_location_name`.       |
| `custom_location_name`| `string\|null` | Condicional  | Nome de local personalizado. Mutuamente exclusivo com `location_id`.           |
| `description`         | `string`       | Não          | Descrição do acidente. Máx. 500 caracteres. Padrão: `""`.                     |

> Um dos dois campos de local (`location_id` ou `custom_location_name`) é obrigatório; fornecer ambos resulta em erro `422`.

---

## Resposta

**HTTP 200 — Sucesso**

Retorna o estado completo do acidente recém-aberto (mesmo formato de `GET /api/admin/accidents/active`):

```json
{
  "is_active": true,
  "active_accidents": [{ "accident": {...}, "situation_rows": [] }],
  "accident": {
    "id": 5,
    "accident_number": 42,
    "accident_number_label": "0042",
    "project_id": 3,
    "project_name": "P80",
    "location_name": "Plataforma Norte",
    "location_is_registered": true,
    "origin": "admin",
    "opened_by_label": "João da Silva",
    "opened_at": "2026-05-25T08:00:00Z",
    "closed_at": null,
    "description": "Colisão na plataforma norte"
  },
  "situation_rows": []
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                              |
|--------|------------------------------------------------------------------------------------------|
| `200`  | Acidente aberto com sucesso.                                                             |
| `401`  | Sessão ausente ou inválida.                                                              |
| `409`  | Já existe um acidente em curso. Feche-o antes de abrir outro.                           |
| `422`  | Dados inválidos: `project_id` ausente, nenhum local fornecido, ambos os locais fornecidos, ou local não pertence ao projeto. |

---

## Side effects

- Cria registro em `accidents` com `origin="admin"`, `opened_by_admin_id` e `opened_by_user_id=null`.
- Grava evento em `check_events` com `action="accident_open"` e `source="admin"`.
- Notifica painel admin e Check Web via SSE.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/accidents/open \
  -H "Content-Type: application/json" \
  -d '{"project_id": 3, "location_id": 7, "description": "Teste"}'
```
