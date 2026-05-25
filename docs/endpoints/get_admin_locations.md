# `GET /api/admin/locations`

## Visão Geral

Retorna a lista de localizações gerenciadas cadastradas no sistema (managed locations), incluindo coordenadas GPS, polígono de cobertura, projetos vinculados e raio de tolerância. Também retorna o limiar global de precisão de GPS configurado para o sistema.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/locations`                         |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Objeto `AdminLocationsResponse` contendo a lista de localizações (filtrada pelo escopo do admin) e o limiar global de precisão GPS.

```json
{
  "items": [
    {
      "id": 1,
      "local": "main",
      "latitude": 1.2840302,
      "longitude": 103.8509491,
      "coordinates": [
        {"latitude": 1.2841, "longitude": 103.8508},
        {"latitude": 1.2842, "longitude": 103.8511},
        {"latitude": 1.2838, "longitude": 103.8512},
        {"latitude": 1.2837, "longitude": 103.8507}
      ],
      "projects": ["PROJ-A", "PROJ-B"],
      "tolerance_meters": 100
    }
  ],
  "location_accuracy_threshold_meters": 50
}
```

### Campos da resposta raiz

| Campo                               | Tipo      | Descrição                                                              |
|-------------------------------------|-----------|------------------------------------------------------------------------|
| `items`                             | `array`   | Lista de localizações gerenciadas                                      |
| `location_accuracy_threshold_meters`| `integer` | Limiar global de precisão GPS aceito (1–9999 metros)                  |

### Campos de cada item em `items`

| Campo             | Tipo              | Descrição                                                                        |
|-------------------|-------------------|----------------------------------------------------------------------------------|
| `id`              | `integer`         | ID interno da localização                                                        |
| `local`           | `string`          | Código/nome da localização (ex: `"main"`, `"co80"`)                             |
| `latitude`        | `float`           | Latitude do vértice principal (primeiro vértice do polígono)                    |
| `longitude`       | `float`           | Longitude do vértice principal                                                   |
| `coordinates`     | `array`           | Lista de coordenadas GPS que definem o polígono da área de cobertura            |
| `projects`        | `array[string]`   | Projetos vinculados a esta localização                                           |
| `tolerance_meters`| `integer`         | Raio de tolerância em metros para considerar o usuário dentro da localização    |

### Campos de cada item em `coordinates`

| Campo       | Tipo    | Descrição                   |
|-------------|---------|------------------------------|
| `latitude`  | `float` | Latitude do vértice (-90 a 90) |
| `longitude` | `float` | Longitude do vértice (-180 a 180) |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia)         |
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
  http://127.0.0.1:8000/api/admin/locations
```
