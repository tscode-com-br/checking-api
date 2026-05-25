# `PUT /api/transport/vehicle-schedules/{schedule_id}`

## Visão Geral

Atualiza a programação (schedule) de um veículo existente. Permite alterar escopo de serviço, sentido de rota, tipo de recorrência, data específica, dia da semana, horário de saída e status ativo/inativo. Este endpoint complementa o `PUT /api/transport/vehicles/{vehicle_id}`, que atualiza apenas os dados base do veículo.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `PUT`                                                             |
| **Path**         | `/api/transport/vehicle-schedules/{schedule_id}`                  |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo  | Descrição                                |
|---------------|-------|------------------------------------------|
| `schedule_id` | `int` | ID do schedule (programação) a atualizar.|

### Request Body

```json
{
  "service_scope": "regular",
  "route_kind": "home_to_work",
  "recurrence_kind": "weekday",
  "service_date": null,
  "weekday": null,
  "departure_time": null,
  "is_active": true
}
```

| Campo             | Tipo           | Obrigatório | Restrições                                  | Descrição                                                                          |
|-------------------|----------------|-------------|---------------------------------------------|------------------------------------------------------------------------------------|
| `service_scope`   | `string`       | Sim         | `regular\|weekend\|extra`                   | Escopo do serviço.                                                                 |
| `route_kind`      | `string`       | Sim         | `home_to_work\|work_to_home`                | Sentido da rota.                                                                   |
| `recurrence_kind` | `string`       | Sim         | `weekday\|matching_weekday\|single_date`    | Tipo de recorrência.                                                               |
| `service_date`    | `date\|null`   | Condicional | `YYYY-MM-DD`; obrigatório para `single_date`| Data específica do serviço.                                                        |
| `weekday`         | `int\|null`    | Condicional | 0–6 (0=seg, 6=dom); obrigatório para `matching_weekday` | Dia da semana.                                                           |
| `departure_time`  | `string\|null` | Condicional | Formato `HH:MM`; obrigatório para `extra`   | Horário de partida. Proibido para `regular` e `weekend`.                           |
| `is_active`       | `bool`         | Não         | —                                           | Se `false`, o schedule é desativado sem ser removido (padrão: `true`).            |

#### Tipos de recorrência

| `recurrence_kind`   | `service_date` | `weekday` | Descrição                                            |
|---------------------|----------------|-----------|------------------------------------------------------|
| `weekday`           | Não usado      | Não usado | Opera em todos os dias do tipo (segunda, terça, etc.)|
| `matching_weekday`  | Não usado      | Obrigatório | Opera apenas no dia da semana especificado (0–6). |
| `single_date`       | Obrigatório    | Não usado | Opera apenas na data específica informada.           |

**Regra adicional**: schedules do tipo `extra` devem usar exclusivamente `recurrence_kind = single_date`.

---

## Resposta

```json
{
  "ok": true,
  "message": "Vehicle schedule updated successfully.",
  "message_key": "status.vehicleUpdated",
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
    "message": "Vehicle schedule not found.",
    "message_key": "status.couldNotUpdateVehicle",
    "error_code": "transport_vehicle_schedule_not_found",
    "issues": [{"code": "transport_vehicle_schedule_not_found"}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Schedule atualizado com sucesso.          |
| `401`  | Sessão de transporte ausente ou inválida. |
| `404`  | Schedule ou veículo não encontrado.       |
| `409`  | Violação de regra de negócio.             |
| `422`  | Corpo inválido.                           |

---

## Side effects

- Persiste as alterações no banco de dados.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_vehicle_schedule_changed`.

---

## Exemplo cURL (ambiente local)

```bash
# Atualizar schedule de veículo regular para operar apenas às segundas
curl -s -b cookies.txt \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "service_scope": "regular",
    "route_kind": "home_to_work",
    "recurrence_kind": "matching_weekday",
    "service_date": null,
    "weekday": 0,
    "departure_time": null,
    "is_active": true
  }' \
  http://127.0.0.1:8000/api/transport/vehicle-schedules/3 | python -m json.tool
```
