# `DELETE /api/transport/vehicles/{schedule_id}`

## Visão Geral

Remove o registro de um veículo de uma programação específica (schedule). O parâmetro de path é o `schedule_id`, não o `vehicle_id`. Também é necessário informar a `service_date` como query parameter para que o evento de reavaliação seja emitido corretamente.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `DELETE`                                                          |
| **Path**         | `/api/transport/vehicles/{schedule_id}`                           |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (resposta)                                     |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo  | Descrição                                                   |
|---------------|-------|-------------------------------------------------------------|
| `schedule_id` | `int` | ID do schedule (programação) do veículo a ser removido.     |

### Query Parameters

| Parâmetro      | Tipo   | Obrigatório | Descrição                                                        |
|----------------|--------|-------------|------------------------------------------------------------------|
| `service_date` | `date` | **Sim**     | Data de referência para o evento de reavaliação (`YYYY-MM-DD`).  |

---

## Resposta

```json
{
  "ok": true,
  "message": "Vehicle deleted from the database.",
  "message_key": "status.vehicleDeleted",
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Erros estruturados

Quando o veículo não pode ser removido (ex.: possui alocações confirmadas):

```json
{
  "detail": {
    "message": "This vehicle cannot be removed from the selected route.",
    "message_key": "warnings.vehicleCannotBeRemoved",
    "error_code": "transport_vehicle_remove_forbidden",
    "issues": [{"code": "transport_vehicle_remove_forbidden"}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Schedule removido com sucesso.                                       |
| `400`  | Veículo não pode ser removido (possui alocações ou outras restrições). |
| `401`  | Sessão de transporte ausente ou inválida.                            |
| `422`  | Parâmetro `service_date` ausente ou inválido.                        |

---

## Side effects

- Remove o schedule do banco de dados.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_vehicle_schedule_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X DELETE \
  "http://127.0.0.1:8000/api/transport/vehicles/3?service_date=2026-05-25" \
  | python -m json.tool
```
