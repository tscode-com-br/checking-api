# `GET /api/admin/locations/auto-checkout-distances`

## Visão Geral

Retorna as distâncias mínimas de check-out automático configuradas por projeto, filtradas pelo escopo de projetos do administrador autenticado. Permite visualizar qual distância GPS cada projeto usa para acionar o check-out automático.

> **Nota:** O path real deste endpoint é `/api/admin/locations/auto-checkout-distances`.

| Atributo         | Valor                                                      |
|------------------|------------------------------------------------------------|
| **Método**       | `GET`                                                      |
| **Path**         | `/api/admin/locations/auto-checkout-distances`             |
| **Autenticação** | Sessão administrativa com perfil de admin                  |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

```json
{
  "items": [
    {
      "project_name": "PROJ-A",
      "minimum_checkout_distance_meters": 1500
    },
    {
      "project_name": "PROJ-B",
      "minimum_checkout_distance_meters": 2000
    }
  ]
}
```

| Campo    | Tipo    | Descrição                                                                      |
|----------|---------|--------------------------------------------------------------------------------|
| `items`  | `array` | Lista de configurações de distância por projeto, filtrada pelo escopo do admin |

### Campos de cada item

| Campo                               | Tipo      | Descrição                                          |
|-------------------------------------|-----------|----------------------------------------------------|
| `project_name`                      | `string`  | Nome do projeto                                    |
| `minimum_checkout_distance_meters`  | `integer` | Distância mínima em metros (1–999999)              |

A lista conterá apenas projetos dentro do escopo do administrador autenticado. Projetos sem configuração explícita não aparecem na lista (o valor padrão é definido no campo `minimum_checkout_distance_meters` do projeto em `GET /api/admin/projects`).

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Dados retornados com sucesso (items pode ser vazio)  |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |

---

## Side effects

Nenhum. Este endpoint é somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/locations/auto-checkout-distances
```
