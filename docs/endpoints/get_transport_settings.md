# `GET /api/transport/settings`

## Visão Geral

Retorna as configurações globais de transporte: horários padrão, capacidade padrão de veículos por tipo, tolerâncias e configurações de precificação (moeda e preços por tipo de veículo).

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/settings`                                         |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (resposta)                                     |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

Nenhum parâmetro de query, path ou corpo de requisição.

---

## Resposta

```json
{
  "arrive_at_work_time": "08:00",
  "work_to_home_time": "17:30",
  "last_update_time": "16:00",
  "default_car_seats": 4,
  "default_minivan_seats": 7,
  "default_van_seats": 14,
  "default_bus_seats": 40,
  "default_tolerance_minutes": 15,
  "extra_car_tolerance_minutes": 30,
  "price_currency_code": "SGD",
  "price_rate_unit": "day",
  "default_car_price": 50.00,
  "default_minivan_price": 80.00,
  "default_van_price": 120.00,
  "default_bus_price": 250.00,
  "available_currencies": [
    {"code": "SGD", "display_label": "Dólar de Singapura"},
    {"code": "BRL", "display_label": "Real Brasileiro"}
  ]
}
```

### Campos da resposta

| Campo                        | Tipo           | Descrição                                                                    |
|------------------------------|----------------|------------------------------------------------------------------------------|
| `arrive_at_work_time`        | `string`       | Horário global de chegada ao trabalho, formato `HH:MM`.                      |
| `work_to_home_time`          | `string`       | Horário global de saída do trabalho (work-to-home), formato `HH:MM`.         |
| `last_update_time`           | `string`       | Horário limite para atualização da lista, formato `HH:MM`.                   |
| `default_car_seats`          | `int`          | Número padrão de lugares para carros (1–99).                                 |
| `default_minivan_seats`      | `int`          | Número padrão de lugares para minivans.                                      |
| `default_van_seats`          | `int`          | Número padrão de lugares para vans.                                          |
| `default_bus_seats`          | `int`          | Número padrão de lugares para ônibus.                                        |
| `default_tolerance_minutes`  | `int`          | Tolerância padrão em minutos (0–240).                                        |
| `extra_car_tolerance_minutes`| `int`          | Tolerância adicional para carros extras (0–240, padrão: 30).                 |
| `price_currency_code`        | `string\|null` | Código da moeda padrão (ex.: `"SGD"`, `"BRL"`).                              |
| `price_rate_unit`            | `string`       | Unidade de precificação: `hour`, `day`, `week` ou `month`.                   |
| `default_car_price`          | `float\|null`  | Preço padrão por unidade para carros.                                        |
| `default_minivan_price`      | `float\|null`  | Preço padrão por unidade para minivans.                                      |
| `default_van_price`          | `float\|null`  | Preço padrão por unidade para vans.                                          |
| `default_bus_price`          | `float\|null`  | Preço padrão por unidade para ônibus.                                        |
| `available_currencies`       | `array`        | Lista de moedas disponíveis para seleção.                                    |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Configurações retornadas com sucesso.     |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<valor_do_cookie>" \
  http://127.0.0.1:8000/api/transport/settings | python -m json.tool
```
