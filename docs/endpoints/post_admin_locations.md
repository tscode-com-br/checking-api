# `POST /api/admin/locations`

## Visão Geral

Cria ou atualiza uma localização gerenciada (upsert). Se `location_id` for informado no body, atualiza a localização existente; caso contrário, cria uma nova. A localização é definida por um polígono GPS (mínimo de 3 vértices distintos), projetos vinculados e raio de tolerância.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/admin/locations`                         |
| **Autenticação** | Sessão administrativa com perfil de admin      |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Request Body

```json
{
  "location_id": null,
  "local": "main",
  "coordinates": [
    {"latitude": 1.2841, "longitude": 103.8508},
    {"latitude": 1.2842, "longitude": 103.8511},
    {"latitude": 1.2838, "longitude": 103.8512},
    {"latitude": 1.2837, "longitude": 103.8507}
  ],
  "projects": ["PROJ-A", "PROJ-B"],
  "tolerance_meters": 100
}
```

### Campos do body

| Campo             | Tipo                   | Obrigatório | Descrição                                                                                   |
|-------------------|------------------------|-------------|---------------------------------------------------------------------------------------------|
| `location_id`     | `integer \| null`      | Não         | ID da localização a atualizar. Se omitido ou `null`, cria nova localização.                 |
| `local`           | `string`               | Sim         | Nome/código da localização (2–40 caracteres)                                                |
| `coordinates`     | `array[Coordinate]`    | Sim         | Polígono GPS com mínimo de 3 vértices distintos. Não repita o primeiro vértice no final.    |
| `projects`        | `array[string]`        | Sim         | Ao menos um projeto. Deve existir no catálogo e estar dentro do escopo do admin.            |
| `tolerance_meters`| `integer`              | Sim         | Raio de tolerância em metros (1–9999)                                                       |

**Compatibilidade legada:** é possível enviar `latitude` e `longitude` no lugar de `coordinates` para criar uma localização de ponto único. O sistema converte automaticamente para o formato `coordinates` com um único vértice.

### Campos de cada item em `coordinates`

| Campo       | Tipo    | Obrigatório | Descrição                      |
|-------------|---------|-------------|--------------------------------|
| `latitude`  | `float` | Sim         | Latitude (-90 a 90)            |
| `longitude` | `float` | Sim         | Longitude (-180 a 180)         |

**Validações do polígono:**
- Mínimo de 3 coordenadas distintas.
- Não deve ter o primeiro vértice repetido no final (o polígono é fechado automaticamente).
- Não deve ter coordenadas duplicadas.
- Não deve ter auto-intersecção.
- Deve formar uma área válida (área não-zero).

---

## Resposta

```json
{
  "ok": true,
  "message": "Localizacao salva com sucesso.",
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                 |
|--------|-----------------------------------------------------------------------------|
| `200`  | Localização criada ou atualizada com sucesso                                |
| `401`  | Sessão administrativa inválida ou expirada                                  |
| `403`  | Sem permissão; admin sem projetos vinculados; localização ou projeto fora do escopo |
| `404`  | `location_id` informado não encontrado                                      |
| `422`  | Erro de validação: polígono inválido, projeto inexistente, campos obrigatórios ausentes |

---

## Side effects

- Cria ou atualiza registro em `managed_locations`.
- Emite notificação SSE para o painel admin.
- Grava evento em `check_events` com `action="location"` e `status="created"` ou `"updated"`.

---

## Exemplo cURL (ambiente local)

```bash
# Criar nova localização
curl -s -X POST \
  -H "Cookie: admin_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "local": "main",
    "coordinates": [
      {"latitude": 1.2841, "longitude": 103.8508},
      {"latitude": 1.2842, "longitude": 103.8511},
      {"latitude": 1.2838, "longitude": 103.8512},
      {"latitude": 1.2837, "longitude": 103.8507}
    ],
    "projects": ["PROJ-A"],
    "tolerance_meters": 100
  }' \
  http://127.0.0.1:8000/api/admin/locations

# Atualizar localização existente
curl -s -X POST \
  -H "Cookie: admin_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "location_id": 1,
    "local": "main",
    "coordinates": [
      {"latitude": 1.2841, "longitude": 103.8508},
      {"latitude": 1.2842, "longitude": 103.8511},
      {"latitude": 1.2838, "longitude": 103.8512},
      {"latitude": 1.2837, "longitude": 103.8507}
    ],
    "projects": ["PROJ-A", "PROJ-B"],
    "tolerance_meters": 150
  }' \
  http://127.0.0.1:8000/api/admin/locations
```
