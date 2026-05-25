# `POST /api/transport/vehicles`

## Visão Geral

Registra um novo veículo no sistema de transporte com suas programações (schedules). Veículos podem ser do tipo `regular` (segunda a sexta), `weekend` (fim de semana) ou `extra` (avulso para data específica). Para veículos regulares e de fim de semana, os dias de operação são definidos pelos campos `every_*`. Para veículos extras, é obrigatório informar `route_kind` e `departure_time`.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/vehicles`                                         |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Request Body

```json
{
  "placa": "SGP-1234",
  "tipo": "van",
  "color": "branco",
  "lugares": 14,
  "tolerance": 10,
  "service_scope": "regular",
  "service_date": "2026-05-25",
  "route_kind": null,
  "departure_time": null,
  "every_monday": true,
  "every_tuesday": true,
  "every_wednesday": true,
  "every_thursday": true,
  "every_friday": true,
  "every_saturday": false,
  "every_sunday": false,
  "every_weekend": false
}
```

#### Campos base do veículo

| Campo       | Tipo           | Obrigatório | Restrições                              | Descrição                                    |
|-------------|----------------|-------------|------------------------------------------|----------------------------------------------|
| `placa`     | `string\|null` | Não         | Máx. 20 chars, normalizado              | Placa do veículo.                            |
| `tipo`      | `string\|null` | Não         | `carro\|minivan\|van\|onibus`            | Tipo do veículo.                             |
| `color`     | `string\|null` | Não         | Máx. 40 chars                           | Cor do veículo.                              |
| `lugares`   | `int\|null`    | Não         | 1–99                                    | Capacidade de passageiros.                   |
| `tolerance` | `int\|null`    | Não         | 0–240 minutos                           | Tolerância de atraso em minutos.             |

#### Campos de programação

| Campo            | Tipo           | Obrigatório | Restrições                            | Descrição                                                                                   |
|------------------|----------------|-------------|----------------------------------------|---------------------------------------------------------------------------------------------|
| `service_scope`  | `string`       | Sim         | `regular\|weekend\|extra`              | Escopo do serviço.                                                                          |
| `service_date`   | `date`         | Sim         | `YYYY-MM-DD`                           | Data de referência para criação do schedule.                                                |
| `route_kind`     | `string\|null` | Condicional | `home_to_work\|work_to_home`           | Obrigatório apenas para `extra`. **Proibido** para `regular` e `weekend`.                  |
| `departure_time` | `string\|null` | Condicional | Formato `HH:MM`                        | Obrigatório apenas para `extra`. **Proibido** para `regular` e `weekend`.                  |
| `every_monday`   | `bool`         | Condicional | —                                      | Opera às segundas-feiras. Padrão `true` para `regular`.                                    |
| `every_tuesday`  | `bool`         | Condicional | —                                      | Opera às terças-feiras.                                                                     |
| `every_wednesday`| `bool`         | Condicional | —                                      | Opera às quartas-feiras.                                                                    |
| `every_thursday` | `bool`         | Condicional | —                                      | Opera às quintas-feiras.                                                                    |
| `every_friday`   | `bool`         | Condicional | —                                      | Opera às sextas-feiras.                                                                     |
| `every_saturday` | `bool`         | Condicional | —                                      | Opera aos sábados. Apenas para `weekend`.                                                   |
| `every_sunday`   | `bool`         | Condicional | —                                      | Opera aos domingos. Apenas para `weekend`.                                                  |
| `every_weekend`  | `bool`         | Não         | —                                      | Atalho para `every_saturday=true` + `every_sunday=true` em veículos `weekend`.             |

**Regras por escopo:**
- `regular`: pelo menos um dia útil (`every_monday`..`every_friday`) deve ser `true`; campos de fim de semana e `route_kind`/`departure_time` são proibidos. Se nenhum dia for informado, todos os dias úteis são ativados automaticamente.
- `weekend`: pelo menos um de `every_saturday` ou `every_sunday` deve ser `true`; dias úteis e `route_kind`/`departure_time` são proibidos.
- `extra`: `route_kind` e `departure_time` são obrigatórios; campos de recorrência (`every_*`) são proibidos.

---

## Resposta

```json
{
  "ok": true,
  "message": "Vehicle saved successfully.",
  "message_key": "status.vehicleSaved",
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Erros estruturados

```json
{
  "detail": {
    "message": "departure_time is required for extra vehicles",
    "message_key": "warnings.extraDepartureRequired",
    "error_code": "transport_vehicle_extra_departure_required",
    "issues": [{"code": "transport_vehicle_extra_departure_required"}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Veículo criado com sucesso.                               |
| `401`  | Sessão de transporte ausente ou inválida.                 |
| `409`  | Violação de regra de negócio (ex.: extra sem `departure_time`). |
| `422`  | Corpo inválido.                                           |

---

## Side effects

- Persiste o veículo e seus schedules no banco de dados.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_vehicle_supply_changed`.

---

## Exemplo cURL (ambiente local)

```bash
# Veículo regular (segunda a sexta)
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "van",
    "lugares": 14,
    "service_scope": "regular",
    "service_date": "2026-05-25"
  }' \
  http://127.0.0.1:8000/api/transport/vehicles | python -m json.tool

# Veículo extra para uma data específica
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "placa": "SGP-9999",
    "tipo": "carro",
    "lugares": 4,
    "service_scope": "extra",
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "departure_time": "07:00"
  }' \
  http://127.0.0.1:8000/api/transport/vehicles | python -m json.tool
```
