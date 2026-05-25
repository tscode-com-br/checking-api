# `PUT /api/transport/assignments/boarding-time`

## Visão Geral

Atualiza manualmente o horário de embarque (`boarding_time`) de uma alocação de transporte confirmada. Aplicável exclusivamente a solicitações do sentido `home_to_work` que já possuem alocação com status `confirmed`. O horário informado representa a estimativa de chegada (ETA) do veículo ao ponto de embarque do passageiro.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `PUT`                                                             |
| **Path**         | `/api/transport/assignments/boarding-time`                        |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. O usuário logado é resolvido como `AdminUser` e registrado na coluna FK→`admin_users.id` da alocação.

---

## Parâmetros

### Request Body

```json
{
  "request_id": 10,
  "service_date": "2026-05-25",
  "route_kind": "home_to_work",
  "boarding_time": "07:25"
}
```

| Campo           | Tipo           | Obrigatório | Restrições                           | Descrição                                                                           |
|-----------------|----------------|-------------|--------------------------------------|-------------------------------------------------------------------------------------|
| `request_id`    | `int`          | Sim         | ≥ 1                                  | ID da solicitação de transporte.                                                    |
| `service_date`  | `date`         | Sim         | `YYYY-MM-DD`                         | Data do serviço. Deve ser compatível com a solicitação.                             |
| `route_kind`    | `string`       | Sim         | Apenas `home_to_work`                | Sentido da rota. O horário de embarque manual só é permitido para `home_to_work`.   |
| `boarding_time` | `string\|null` | Não         | Formato `HH:MM` ou `null`            | Horário de embarque estimado. Enviar `null` para remover o horário manual.          |

---

## Resposta

```json
{
  "ok": true,
  "message": "Transport boarding time saved successfully.",
  "message_key": "status.boardingTimeSaved",
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Erros estruturados

**Sem alocação confirmada:**
```json
{
  "detail": {
    "message": "A confirmed transport assignment is required to update boarding_time.",
    "message_key": "warnings.boardingTimeRequiresConfirmedAssignment",
    "error_code": "transport_boarding_time_confirmed_required",
    "issues": [{"code": "transport_boarding_time_confirmed_required"}]
  }
}
```

**Tentativa de usar `work_to_home`:**
```json
{
  "detail": {
    "message": "Manual boarding_time is only available for confirmed home_to_work assignments.",
    "message_key": "warnings.boardingTimeEtaOnly",
    "error_code": "transport_boarding_time_eta_only",
    "issues": [{"code": "transport_boarding_time_eta_only"}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Horário de embarque salvo com sucesso.                               |
| `400`  | Data incompatível com a solicitação.                                 |
| `401`  | Sessão de transporte ausente ou inválida.                            |
| `404`  | Solicitação não encontrada.                                          |
| `409`  | Violação de regra (ex.: sem alocação confirmada, `work_to_home`).    |
| `422`  | Corpo inválido.                                                      |

---

## Side effects

- Atualiza `boarding_time` na tabela `transport_assignments`.
- Registra o `admin_user_id` do ator na alocação.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_assignment_changed`.

---

## Exemplo cURL (ambiente local)

```bash
# Definir horário de embarque
curl -s -b cookies.txt \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 10,
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "boarding_time": "07:25"
  }' \
  http://127.0.0.1:8000/api/transport/assignments/boarding-time | python -m json.tool

# Remover horário manual (restaurar automático)
curl -s -b cookies.txt \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 10,
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "boarding_time": null
  }' \
  http://127.0.0.1:8000/api/transport/assignments/boarding-time | python -m json.tool
```
