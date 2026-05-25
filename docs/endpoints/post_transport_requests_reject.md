# `POST /api/transport/requests/reject`

## Visão Geral

Rejeita uma solicitação de transporte ativa, criando ou atualizando a alocação com status `rejected` para a data e rota especificadas. Diferente do `POST /api/transport/assignments` com `status: rejected`, este endpoint exige que a solicitação esteja com status `active` e trata toda a lógica de rejeição de forma mais direta.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/requests/reject`                                  |
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
  "response_message": "Veículo indisponível para este trajeto."
}
```

| Campo              | Tipo           | Obrigatório | Restrições                       | Descrição                                                               |
|--------------------|----------------|-------------|----------------------------------|-------------------------------------------------------------------------|
| `request_id`       | `int`          | Sim         | ≥ 1                              | ID da solicitação de transporte ativa a ser rejeitada.                  |
| `service_date`     | `date`         | Sim         | `YYYY-MM-DD`                     | Data do serviço. Deve ser compatível com a solicitação.                 |
| `route_kind`       | `string`       | Sim         | `home_to_work\|work_to_home`     | Sentido da rota a ser rejeitada.                                        |
| `response_message` | `string\|null` | Não         | Máx. 255 chars                   | Mensagem de resposta ao passageiro explicando a rejeição.               |

---

## Resposta

```json
{
  "ok": true,
  "message": "Transport request rejected successfully.",
  "message_key": "status.requestRejected",
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Erros estruturados

**Solicitação não encontrada ou não está ativa:**
```json
{
  "detail": {
    "message": "Transport request not found.",
    "message_key": "status.couldNotRejectSelectedRequest",
    "error_code": "transport_request_not_found",
    "issues": [
      {
        "code": "transport_request_not_found",
        "message": "Transport request not found.",
        "request_id": 10
      }
    ]
  }
}
```

**Data incompatível:**
```json
{
  "detail": {
    "message": "The transport request does not apply to the selected date.",
    "message_key": "status.couldNotRejectSelectedRequest",
    "error_code": "transport_request_date_mismatch",
    "issues": [
      {
        "code": "transport_request_date_mismatch",
        "request_id": 10,
        "service_date": "2026-05-25"
      }
    ]
  }
}
```

---

## Diferença entre este endpoint e `POST /assignments`

| Aspecto                          | `POST /requests/reject`                       | `POST /assignments` com `status: rejected`         |
|----------------------------------|-----------------------------------------------|----------------------------------------------------|
| Verificação de status da request | Exige `status = active`                       | Não verifica o status da request                   |
| `vehicle_id`                     | Não aceita (rejeição não exige veículo)       | Não aceita quando `status ≠ confirmed`             |
| Semântica                        | Operação explícita de rejeição                | Upsert genérico de alocação                        |

---

## Códigos de status HTTP

| Código | Significado                                                         |
|--------|---------------------------------------------------------------------|
| `200`  | Solicitação rejeitada com sucesso.                                  |
| `400`  | Data incompatível com a solicitação.                                |
| `401`  | Sessão de transporte ausente ou inválida.                           |
| `404`  | Solicitação não encontrada ou não está ativa.                       |
| `422`  | Corpo inválido.                                                     |

---

## Side effects

- Cria ou atualiza o registro na tabela `transport_assignments` com `status = rejected`.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_assignment_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 10,
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "response_message": "Sem vagas disponíveis para esta data."
  }' \
  http://127.0.0.1:8000/api/transport/requests/reject | python -m json.tool
```
