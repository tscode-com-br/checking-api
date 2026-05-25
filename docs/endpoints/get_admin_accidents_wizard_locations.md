# `GET /api/admin/accidents/wizard/locations`

## Visão Geral

Retorna os locais cadastrados associados a um projeto específico, para uso no wizard de abertura de acidente. Apenas locais que têm o projeto informado na sua lista de projetos são incluídos.

| Atributo         | Valor                                              |
|------------------|----------------------------------------------------|
| **Método**       | `GET`                                              |
| **Path**         | `/api/admin/accidents/wizard/locations`            |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`).

---

## Parâmetros

### Query Parameters

| Parâmetro    | Tipo      | Obrigatório | Descrição                                     |
|--------------|-----------|-------------|-----------------------------------------------|
| `project_id` | `integer` | Sim         | ID do projeto para filtrar os locais associados. |

---

## Resposta

**HTTP 200**

```json
[
  { "id": 7, "name": "Plataforma Norte", "registered": true },
  { "id": 12, "name": "Escritório de Campo", "registered": true }
]
```

| Campo        | Tipo      | Descrição                                         |
|--------------|-----------|---------------------------------------------------|
| `id`         | `integer` | ID do local cadastrado (`managed_locations.id`).  |
| `name`       | `string`  | Nome do local.                                    |
| `registered` | `boolean` | Sempre `true` neste endpoint (local cadastrado).  |

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Lista retornada (pode ser vazia `[]`).                    |
| `401`  | Sessão ausente ou inválida.                               |
| `403`  | Sessão com escopo limitado — acesso negado.               |
| `404`  | Projeto não encontrado para o `project_id` informado.     |
| `422`  | Parâmetro `project_id` ausente ou inválido.               |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  "http://127.0.0.1:8000/api/admin/accidents/wizard/locations?project_id=3"
```
