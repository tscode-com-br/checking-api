# `GET /api/mobile/locations`

## Visão Geral

Retorna a lista completa de locais gerenciados (geofences) configurados no sistema, incluindo coordenadas GPS, raio de tolerância e metadados de configuração de distância mínima por projeto. Utilizado pelo aplicativo Android para validar se o usuário está dentro do raio permitido antes de registrar check-in ou checkout.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/mobile/locations`                        |
| **Autenticação** | Header `X-Mobile-Shared-Key`                   |
| **Tags**         | `mobile`                                       |

---

## Autenticação

Requer o header `X-Mobile-Shared-Key` com o valor configurado em `MOBILE_APP_SHARED_KEY`.

```
X-Mobile-Shared-Key: minha-chave-mobile
```

---

## Parâmetros

Nenhum parâmetro.

---

## Resposta

### 200 OK

```json
{
  "items": [
    {
      "id": 1,
      "local": "Portaria Principal",
      "latitude": -3.7172,
      "longitude": -38.5437,
      "coordinates": [
        {
          "latitude": -3.7172,
          "longitude": -38.5437
        }
      ],
      "tolerance_meters": 150,
      "updated_at": "2024-03-10T09:00:00+08:00"
    },
    {
      "id": 2,
      "local": "Refeitório",
      "latitude": -3.7185,
      "longitude": -38.5440,
      "coordinates": [
        {
          "latitude": -3.7185,
          "longitude": -38.5440
        }
      ],
      "tolerance_meters": 80,
      "updated_at": "2024-03-10T09:00:00+08:00"
    }
  ],
  "synced_at": "2024-05-25T10:15:00+08:00",
  "location_accuracy_threshold_meters": 50,
  "minimum_checkout_distance_meters_by_project": {
    "Projeto Alpha": 500,
    "Projeto Beta": 300
  }
}
```

### Campos da resposta raiz

| Campo                                        | Tipo       | Descrição                                                                |
|----------------------------------------------|------------|--------------------------------------------------------------------------|
| `items`                                      | `array`    | Lista de locais gerenciados                                              |
| `synced_at`                                  | `datetime` | Timestamp do momento da consulta (SGT)                                   |
| `location_accuracy_threshold_meters`         | `integer`  | Precisão mínima do GPS exigida pelo sistema (metros)                     |
| `minimum_checkout_distance_meters_by_project`| `object`   | Mapa `projeto → distância mínima (metros)` para checkout por geofence    |

### Campos de cada item em `items`

| Campo              | Tipo       | Descrição                                                       |
|--------------------|------------|-----------------------------------------------------------------|
| `id`               | `integer`  | Identificador interno do local                                  |
| `local`            | `string`   | Nome do local                                                   |
| `latitude`         | `float`    | Latitude principal (primeiro ponto de coordenadas)              |
| `longitude`        | `float`    | Longitude principal (primeiro ponto de coordenadas)             |
| `coordinates`      | `array`    | Lista de pontos de coordenadas (pode ter múltiplos pontos)      |
| `tolerance_meters` | `integer`  | Raio em metros da geofence deste local                          |
| `updated_at`       | `datetime` | Última atualização do local                                     |

### Campos de cada objeto em `coordinates`

| Campo       | Tipo    | Descrição  |
|-------------|---------|------------|
| `latitude`  | `float` | Latitude   |
| `longitude` | `float` | Longitude  |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Sucesso                                              |
| `401`  | Header `X-Mobile-Shared-Key` ausente ou inválido     |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s http://127.0.0.1:8000/api/mobile/locations \
  -H "X-Mobile-Shared-Key: minha-chave-mobile"
```
