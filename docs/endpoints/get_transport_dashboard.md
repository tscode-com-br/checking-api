# `GET /api/transport/dashboard`

## Visão Geral

Retorna todos os dados necessários para renderizar o painel principal de transporte: solicitações (regular, fim de semana e extra), veículos disponíveis, registro de veículos, projetos e locais de trabalho — tudo filtrado pela data e sentido de rota selecionados.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/dashboard`                                        |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (resposta)                                     |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Query Parameters

| Parâmetro      | Tipo     | Obrigatório | Padrão          | Descrição                                                   |
|----------------|----------|-------------|-----------------|-------------------------------------------------------------|
| `service_date` | `date`   | Não         | Data atual (SGT) | Data do serviço no formato `YYYY-MM-DD`.                   |
| `route_kind`   | `string` | Não         | `home_to_work`  | Sentido da rota: `home_to_work` ou `work_to_home`.          |

---

## Resposta

```json
{
  "selected_date": "2026-05-25",
  "selected_route": "home_to_work",
  "dashboard_generated_at": "2026-05-25T07:30:00+08:00",
  "arrive_at_work_time": "08:00",
  "work_to_home_departure_time": "17:30",
  "projects": [
    {
      "id": 1,
      "name": "Projeto Alpha",
      "country_code": "SG",
      "country_name": "Singapore",
      "timezone_name": "Asia/Singapore",
      "timezone_label": "Singapore (SGT +08:00)",
      "address": "1 Raffles Place",
      "zip_code": "048616",
      "forms_enabled": true,
      "transport_enabled": true,
      "emergency_phone": "+6512345678"
    }
  ],
  "regular_requests": [
    {
      "id": 10,
      "request_kind": "regular",
      "requested_time": "07:30",
      "boarding_time": null,
      "service_date": "2026-05-25",
      "user_id": 42,
      "chave": "AB12",
      "nome": "João da Silva",
      "projeto": "Projeto Alpha",
      "projects": ["Projeto Alpha"],
      "workplace": "Escritório Central",
      "end_rua": "Rua das Flores, 100",
      "zip": "01310-100",
      "assignment_status": "confirmed",
      "awareness_status": "aware",
      "assigned_vehicle": {
        "id": 5,
        "placa": "SGP-1234",
        "tipo": "van",
        "color": "branco",
        "lugares": 14,
        "tolerance": 10,
        "pending_fields": [],
        "is_ready_for_allocation": true,
        "schedule_id": 3,
        "service_scope": "regular",
        "route_kind": "home_to_work",
        "departure_time": null
      },
      "response_message": null
    }
  ],
  "weekend_requests": [],
  "extra_requests": [],
  "regular_vehicles": [],
  "weekend_vehicles": [],
  "extra_vehicles": [],
  "regular_vehicle_registry": [],
  "weekend_vehicle_registry": [],
  "extra_vehicle_registry": [],
  "workplaces": []
}
```

### Campos principais da resposta

| Campo                      | Tipo       | Descrição                                                              |
|----------------------------|------------|------------------------------------------------------------------------|
| `selected_date`            | `date`     | Data do serviço consultado.                                            |
| `selected_route`           | `string`   | Sentido da rota: `home_to_work` ou `work_to_home`.                     |
| `dashboard_generated_at`   | `datetime` | Timestamp de geração do dashboard.                                     |
| `arrive_at_work_time`      | `string`   | Horário global de chegada ao trabalho (formato `HH:MM`).               |
| `work_to_home_departure_time` | `string` | Horário global de saída do trabalho (formato `HH:MM`).                |
| `projects`                 | `array`    | Lista de projetos ativos com transporte habilitado.                    |
| `regular_requests`         | `array`    | Solicitações regulares (segunda a sexta) para a data e rota.           |
| `weekend_requests`         | `array`    | Solicitações de fim de semana para a data e rota.                      |
| `extra_requests`           | `array`    | Solicitações extras (avulsos) para a data e rota.                      |
| `regular_vehicles`         | `array`    | Veículos regulares disponíveis para a data e rota.                     |
| `weekend_vehicles`         | `array`    | Veículos de fim de semana disponíveis para a data e rota.              |
| `extra_vehicles`           | `array`    | Veículos extras disponíveis para a data e rota.                        |
| `regular_vehicle_registry` | `array`    | Registro gerencial de veículos regulares com contagem de alocados.     |
| `weekend_vehicle_registry` | `array`    | Registro gerencial de veículos de fim de semana.                       |
| `extra_vehicle_registry`   | `array`    | Registro gerencial de veículos extras.                                 |
| `workplaces`               | `array`    | Locais de trabalho cadastrados.                                        |

#### Campos de cada `TransportRequestRow`

| Campo               | Tipo           | Descrição                                                          |
|---------------------|----------------|--------------------------------------------------------------------|
| `assignment_status` | `string`       | `pending`, `confirmed`, `rejected` ou `cancelled`.                 |
| `awareness_status`  | `string`       | `pending` ou `aware` (confirmação do passageiro).                  |
| `assigned_vehicle`  | `object\|null` | Veículo alocado; `null` se não confirmado.                         |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Dashboard retornado com sucesso.          |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<valor_do_cookie>" \
  "http://127.0.0.1:8000/api/transport/dashboard?service_date=2026-05-25&route_kind=home_to_work" \
  | python -m json.tool
```
