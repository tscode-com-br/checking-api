# `GET /api/admin/locations/audit`

## Visão Geral

Executa uma auditoria geométrica de todas as localizações cadastradas, identificando problemas como polígonos com auto-intersecção, coordenadas duplicadas, área zero, poucos vértices ou vértice de fechamento redundante. Retorna um sumário agregado e um relatório detalhado por localização.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/locations/audit`                   |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Query Parameters

| Parâmetro       | Tipo      | Obrigatório | Padrão  | Descrição                                                           |
|-----------------|-----------|-------------|---------|---------------------------------------------------------------------|
| `include_valid` | `boolean` | Não         | `false` | Se `true`, inclui localizações sem problemas no array `rows`       |

---

## Resposta

```json
{
  "summary": {
    "total_locations": 5,
    "checkout_zone_locations": 3,
    "valid_polygon_locations": 4,
    "locations_with_errors": 1,
    "locations_with_warnings_only": 0,
    "locations_without_issues": 4,
    "locations_requiring_manual_review": 1,
    "issue_counts": {
      "self_intersection": 1
    }
  },
  "rows": [
    {
      "location_id": 2,
      "local": "co80",
      "projects": ["PROJ-A"],
      "is_checkout_zone": true,
      "tolerance_meters": 100,
      "coordinate_count": 4,
      "effective_vertex_count": 4,
      "unique_coordinate_count": 4,
      "polygon_area_square_meters": 0.0,
      "has_errors": true,
      "has_warnings": false,
      "needs_manual_review": true,
      "issues": [
        {
          "code": "self_intersection",
          "severity": "error",
          "message": "O poligono possui auto-interseccao"
        }
      ]
    }
  ]
}
```

### Campos do sumário (`summary`)

| Campo                              | Tipo      | Descrição                                           |
|------------------------------------|-----------|-----------------------------------------------------|
| `total_locations`                  | `integer` | Total de localizações auditadas                     |
| `checkout_zone_locations`          | `integer` | Localizações marcadas como zona de check-out        |
| `valid_polygon_locations`          | `integer` | Localizações com polígono geometricamente válido    |
| `locations_with_errors`            | `integer` | Localizações com pelo menos um erro                 |
| `locations_with_warnings_only`     | `integer` | Localizações apenas com avisos (sem erros)          |
| `locations_without_issues`         | `integer` | Localizações sem nenhum problema                    |
| `locations_requiring_manual_review`| `integer` | Localizações que requerem revisão manual            |
| `issue_counts`                     | `object`  | Contagem de ocorrências por código de problema      |

### Campos de cada item em `rows`

| Campo                         | Tipo             | Descrição                                                       |
|-------------------------------|------------------|-----------------------------------------------------------------|
| `location_id`                 | `integer`        | ID da localização                                               |
| `local`                       | `string`         | Código/nome da localização                                      |
| `projects`                    | `array[string]`  | Projetos vinculados                                             |
| `is_checkout_zone`            | `boolean`        | Se é uma zona de check-out                                      |
| `tolerance_meters`            | `integer`        | Raio de tolerância configurado                                  |
| `coordinate_count`            | `integer`        | Total de coordenadas no JSON                                    |
| `effective_vertex_count`      | `integer`        | Vértices efetivos (excluindo vértice de fechamento redundante)  |
| `unique_coordinate_count`     | `integer`        | Coordenadas únicas                                              |
| `polygon_area_square_meters`  | `float \| null`  | Área do polígono em metros quadrados (null se inválido)         |
| `has_errors`                  | `boolean`        | Presença de problemas nível `error`                             |
| `has_warnings`                | `boolean`        | Presença de problemas nível `warning`                           |
| `needs_manual_review`         | `boolean`        | Requer revisão manual                                           |
| `issues`                      | `array`          | Lista de problemas encontrados                                  |

### Campos de cada item em `issues`

| Campo      | Tipo                            | Descrição                             |
|------------|---------------------------------|---------------------------------------|
| `code`     | `string`                        | Código do problema (ex: `"self_intersection"`) |
| `severity` | `"error" \| "warning" \| "info"`| Severidade do problema                |
| `message`  | `string`                        | Descrição legível do problema         |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Auditoria executada com sucesso                      |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |

---

## Side effects

Nenhum. Este endpoint é somente leitura — nenhuma localização é modificada.

---

## Exemplo cURL (ambiente local)

```bash
# Apenas localizações com problemas (padrão)
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/locations/audit

# Incluindo localizações válidas
curl -s \
  -H "Cookie: admin_session=<token>" \
  "http://127.0.0.1:8000/api/admin/locations/audit?include_valid=true"
```
