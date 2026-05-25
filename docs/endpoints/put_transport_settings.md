# `PUT /api/transport/settings`

## Visão Geral

Atualiza as configurações globais de transporte: horários padrão, capacidade padrão de veículos por tipo, tolerâncias e configurações de precificação. Retorna as configurações atualizadas.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `PUT`                                                             |
| **Path**         | `/api/transport/settings`                                         |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Request Body

Todos os campos são **obrigatórios** (sem valores defaults implícitos no request). O schema usa `extra="forbid"` — campos desconhecidos causam erro 422.

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
  "default_bus_price": 250.00
}
```

| Campo                        | Tipo           | Obrigatório | Restrições            | Descrição                                                 |
|------------------------------|----------------|-------------|------------------------|-----------------------------------------------------------|
| `arrive_at_work_time`        | `string`       | Sim         | Formato `HH:MM`        | Horário global de chegada ao trabalho.                    |
| `work_to_home_time`          | `string`       | Sim         | Formato `HH:MM`        | Horário global de saída (work-to-home).                   |
| `last_update_time`           | `string`       | Sim         | Formato `HH:MM`        | Horário limite para atualizações.                         |
| `default_car_seats`          | `int`          | Sim         | 1–99                   | Capacidade padrão de carros.                              |
| `default_minivan_seats`      | `int`          | Sim         | 1–99                   | Capacidade padrão de minivans.                            |
| `default_van_seats`          | `int`          | Sim         | 1–99                   | Capacidade padrão de vans.                                |
| `default_bus_seats`          | `int`          | Sim         | 1–99                   | Capacidade padrão de ônibus.                              |
| `default_tolerance_minutes`  | `int`          | Sim         | 0–240                  | Tolerância padrão em minutos.                             |
| `extra_car_tolerance_minutes`| `int`          | Não         | 0–240 (padrão: 30)     | Tolerância adicional para carros extras.                  |
| `price_currency_code`        | `string\|null` | Não         | 2–12 caracteres        | Código de moeda; deve existir em `available_currencies`.  |
| `price_rate_unit`            | `string`       | Sim         | `hour\|day\|week\|month` | Unidade de precificação.                                |
| `default_car_price`          | `float\|null`  | Não         | 0 – 9.999.999.999,99   | Preço padrão por unidade para carros.                     |
| `default_minivan_price`      | `float\|null`  | Não         | idem                   | Preço padrão por unidade para minivans.                   |
| `default_van_price`          | `float\|null`  | Não         | idem                   | Preço padrão por unidade para vans.                       |
| `default_bus_price`          | `float\|null`  | Não         | idem                   | Preço padrão por unidade para ônibus.                     |

---

## Resposta

Retorna as configurações atualizadas no mesmo formato do `GET /api/transport/settings` (inclui `available_currencies`).

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
    {"code": "SGD", "display_label": "Dólar de Singapura"}
  ]
}
```

---

## Erros estruturados

Em caso de `price_currency_code` inválido (não encontrado em `available_currencies`):

```json
{
  "detail": {
    "message": "The selected currency is not available.",
    "message_key": "warnings.currencyNotAvailable",
    "message_params": {},
    "error_code": "transport_currency_not_available",
    "issues": [{"code": "transport_currency_not_available"}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                                    |
|--------|----------------------------------------------------------------|
| `200`  | Configurações salvas e retornadas.                             |
| `401`  | Sessão de transporte ausente ou inválida.                      |
| `409`  | Conflito (ex.: moeda selecionada não disponível).              |
| `422`  | Corpo da requisição inválido (campo ausente, tipo errado, etc.).|

---

## Side effects

- Persiste as configurações no banco de dados (tabela de location settings).
- Se `arrive_at_work_time`, `work_to_home_time`, `last_update_time` ou `extra_car_tolerance_minutes` foram alterados: emite evento de reavaliação `transport_timing_policy_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "arrive_at_work_time": "08:00",
    "work_to_home_time": "17:30",
    "last_update_time": "16:00",
    "default_car_seats": 4,
    "default_minivan_seats": 7,
    "default_van_seats": 14,
    "default_bus_seats": 40,
    "default_tolerance_minutes": 15,
    "extra_car_tolerance_minutes": 30,
    "price_currency_code": null,
    "price_rate_unit": "day",
    "default_car_price": null,
    "default_minivan_price": null,
    "default_van_price": null,
    "default_bus_price": null
  }' \
  http://127.0.0.1:8000/api/transport/settings | python -m json.tool
```
