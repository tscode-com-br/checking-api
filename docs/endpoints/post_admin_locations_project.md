# `POST /api/admin/locations/{location_id}/project`

## Visão Geral

> **Atenção:** Este endpoint específico não existe no roteador atual da API. O gerenciamento de projetos vinculados a uma localização é feito pelo endpoint de upsert `POST /api/admin/locations`, passando `location_id` e a lista atualizada de `projects` no body.

Este arquivo documenta como associar projetos a uma localização existente utilizando o endpoint disponível.

---

## Como vincular projetos a uma localização existente

Para adicionar ou alterar os projetos de uma localização, use `POST /api/admin/locations` com o `location_id` da localização que deseja atualizar:

```bash
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
    "tolerance_meters": 100
  }' \
  http://127.0.0.1:8000/api/admin/locations
```

### Campos obrigatórios para atualização

| Campo          | Tipo            | Descrição                                                            |
|----------------|-----------------|----------------------------------------------------------------------|
| `location_id`  | `integer`       | ID da localização a atualizar                                        |
| `local`        | `string`        | Nome/código atual da localização                                     |
| `coordinates`  | `array`         | Polígono GPS completo (mínimo 3 vértices)                            |
| `projects`     | `array[string]` | Lista completa de projetos (substitui a lista anterior integralmente)|
| `tolerance_meters` | `integer`   | Raio de tolerância em metros                                         |

### Regras de escopo para projetos

- O administrador só pode adicionar projetos dentro do seu escopo.
- Projetos fora do escopo já vinculados à localização são preservados automaticamente (desde que não se tente substituí-los).
- Para remover um projeto do escopo do admin de uma localização, ele precisa remover o projeto da lista `projects` — se o projeto pertencer ao escopo do admin.

---

## Referência

Para documentação completa do endpoint de upsert de localização, consulte [`post_admin_locations.md`](post_admin_locations.md).
