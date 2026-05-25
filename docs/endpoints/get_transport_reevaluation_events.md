# `GET /api/transport/reevaluation-events`

## Visão Geral

Retorna o catálogo de tipos de eventos de reavaliação e os eventos recentes emitidos pelo sistema de transporte. Eventos de reavaliação indicam que algum dado mudou e que o frontend deve tomar ações como atualizar o snapshot, revalidar restrições ou reconstruir a proposta ativa.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/reevaluation-events`                              |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (resposta)                                     |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo  | Obrigatório | Padrão | Restrições | Descrição                                      |
|-----------|-------|-------------|--------|------------|------------------------------------------------|
| `limit`   | `int` | Não         | `20`   | 1–50       | Número máximo de eventos recentes a retornar.  |

---

## Resposta

```json
{
  "catalog": [
    {
      "event_type": "transport_assignment_changed",
      "description": "An assignment decision changed the operational state.",
      "downstream_actions": ["refresh_snapshot", "revalidate_constraints", "rebuild_proposal"]
    },
    {
      "event_type": "transport_vehicle_supply_changed",
      "description": "A vehicle registration changed the available transport supply.",
      "downstream_actions": ["refresh_snapshot", "rebuild_proposal", "regenerate_export"]
    }
  ],
  "recent_events": [
    {
      "event_id": "evt-abc123",
      "event_type": "transport_assignment_changed",
      "reason": "event",
      "source": "transport_admin",
      "message": "A transport assignment decision changed the operational state of the day.",
      "emitted_at": "2026-05-25T07:45:00+08:00",
      "service_date": "2026-05-25",
      "route_kind": "home_to_work",
      "request_id": 10,
      "vehicle_id": 5,
      "schedule_id": null,
      "workplace_id": null,
      "proposal_key": null,
      "downstream_actions": ["refresh_snapshot", "revalidate_constraints", "rebuild_proposal"]
    }
  ]
}
```

### Campos da resposta

| Campo               | Tipo    | Descrição                                                                          |
|---------------------|---------|------------------------------------------------------------------------------------|
| `catalog`           | `array` | Tipos de eventos possíveis com descrição e ações downstream esperadas.             |
| `recent_events`     | `array` | Eventos emitidos recentemente (in-memory, perdidos ao reiniciar o servidor).        |

#### Campos de cada evento em `recent_events`

| Campo                | Tipo           | Descrição                                                                    |
|----------------------|----------------|------------------------------------------------------------------------------|
| `event_id`           | `string`       | Identificador único do evento.                                               |
| `event_type`         | `string`       | Tipo do evento (ex.: `transport_assignment_changed`).                        |
| `reason`             | `string`       | Razão do disparo: `"event"` ou `"settings"`.                                 |
| `source`             | `string`       | Origem: `transport_admin`, `web_transport` ou `transport_proposal`.          |
| `message`            | `string`       | Descrição legível do evento.                                                 |
| `emitted_at`         | `datetime`     | Momento em que o evento foi emitido.                                         |
| `service_date`       | `date\|null`   | Data do serviço afetado (quando aplicável).                                  |
| `route_kind`         | `string\|null` | Sentido da rota afetado (quando aplicável).                                  |
| `downstream_actions` | `array`        | Ações que o frontend deve executar ao receber este evento.                   |

#### Valores possíveis de `downstream_actions`

| Ação                       | Descrição                                                  |
|----------------------------|------------------------------------------------------------|
| `refresh_snapshot`         | Buscar novo snapshot operacional.                          |
| `revalidate_constraints`   | Revalidar as restrições da proposta ativa.                 |
| `rebuild_proposal`         | Reconstruir a proposta operacional.                        |
| `regenerate_export`        | Regenerar o arquivo de exportação.                         |
| `refresh_transport_state`  | Atualizar estado geral de transporte no frontend.          |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Catálogo e eventos retornados com sucesso. |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<valor_do_cookie>" \
  "http://127.0.0.1:8000/api/transport/reevaluation-events?limit=10" \
  | python -m json.tool
```
