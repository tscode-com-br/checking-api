# `POST /api/transport/assignments`

## Visão Geral

Cria ou atualiza (upsert) uma alocação individual de transporte para uma solicitação específica, associando-a a um veículo e definindo o status. Diferente do fluxo de propostas (build → validate → approve → apply), este endpoint opera de forma imediata, sem passar por aprovação.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/assignments`                                      |
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
  "request_id": 10,
  "service_date": "2026-05-25",
  "route_kind": "home_to_work",
  "status": "confirmed",
  "vehicle_id": 5,
  "response_message": null
}
```

| Campo              | Tipo           | Obrigatório | Restrições                                   | Descrição                                                                    |
|--------------------|----------------|-------------|----------------------------------------------|------------------------------------------------------------------------------|
| `request_id`       | `int`          | Sim         | ≥ 1                                          | ID da solicitação de transporte (`transport_requests.id`).                   |
| `service_date`     | `date`         | Sim         | `YYYY-MM-DD`                                 | Data do serviço. Deve ser compatível com a solicitação.                      |
| `route_kind`       | `string`       | Sim         | `home_to_work\|work_to_home`                  | Sentido da rota.                                                             |
| `status`           | `string`       | Sim         | `confirmed\|rejected\|cancelled\|pending`     | Status da alocação.                                                          |
| `vehicle_id`       | `int\|null`    | Condicional | ≥ 1; obrigatório quando `status = confirmed` | ID do veículo alocado. **Proibido** para status diferente de `confirmed`.    |
| `response_message` | `string\|null` | Não         | Máx. 255 chars                               | Mensagem de resposta ao passageiro (ex.: motivo da rejeição).                |

**Regras de validação:**
- `vehicle_id` é obrigatório quando `status = confirmed` e proibido nos demais status.
- A `service_date` deve ser válida para a solicitação (baseado no tipo de recorrência da request).
- O veículo deve ter um schedule ativo para a `service_date`, `route_kind` e escopo compatível com a solicitação.

---

## Resposta

```json
{
  "ok": true,
  "message": "Transport assignment saved successfully.",
  "message_key": "status.allocationUpdated",
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Erros estruturados

**Solicitação não encontrada:**
```json
{
  "detail": {
    "message": "Transport request not found.",
    "error_code": "transport_request_not_found",
    "issues": [{"code": "transport_request_not_found", "message": "Transport request not found.", "request_id": 10}]
  }
}
```

**Data incompatível:**
```json
{
  "detail": {
    "message": "The transport request does not apply to the selected date.",
    "error_code": "transport_request_date_mismatch",
    "issues": [{"code": "transport_request_date_mismatch", "request_id": 10, "service_date": "2026-05-25"}]
  }
}
```

**Veículo não disponível para a data/rota:**
```json
{
  "detail": {
    "message": "The selected vehicle is not available for this date and route.",
    "error_code": "transport_vehicle_schedule_unavailable",
    "issues": [{"code": "transport_vehicle_schedule_unavailable", "vehicle_id": 5}]
  }
}
```

**Veículo de lista diferente:**
```json
{
  "detail": {
    "message": "The selected vehicle belongs to a different list.",
    "error_code": "transport_vehicle_scope_conflict",
    "issues": [{"code": "transport_vehicle_scope_conflict", "vehicle_id": 5}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                                       |
|--------|-------------------------------------------------------------------|
| `200`  | Alocação salva com sucesso.                                       |
| `400`  | Data incompatível com a solicitação.                              |
| `401`  | Sessão de transporte ausente ou inválida.                         |
| `404`  | Solicitação ou veículo não encontrado.                            |
| `409`  | Conflito de scope ou veículo não pronto para alocação.            |
| `422`  | Corpo inválido.                                                   |

---

## Side effects

- Cria ou atualiza o registro na tabela `transport_assignments`.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_assignment_changed`.

---

## Exemplo cURL (ambiente local)

```bash
# Confirmar alocação com veículo
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 10,
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "status": "confirmed",
    "vehicle_id": 5
  }' \
  http://127.0.0.1:8000/api/transport/assignments | python -m json.tool

# Marcar como pendente (sem veículo)
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 10,
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "status": "pending",
    "vehicle_id": null
  }' \
  http://127.0.0.1:8000/api/transport/assignments | python -m json.tool
```
