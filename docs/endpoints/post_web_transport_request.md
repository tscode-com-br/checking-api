# `POST /api/web/transport/request`

## Visão Geral

Cria ou reaproveita uma solicitação de transporte para o usuário autenticado. Suporta três modalidades: rotineiro (dias úteis), fim de semana e extra (data/hora específica). O endpoint é idempotente por modalidade: se já existir uma solicitação ativa do mesmo tipo, retorna a solicitação existente sem criar duplicata.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/transport/request`                   |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no corpo deve coincidir com o valor no cookie. Em caso de falha retorna `401`.

**Pré-requisito:** o usuário deve ter endereço e ZIP cadastrados (via `POST /api/web/transport/address`). Caso contrário, retorna `400`.

---

## Request Body

### Transporte Rotineiro (dias úteis)

```json
{
  "chave": "AB12",
  "request_kind": "regular",
  "requested_time": "07:30",
  "selected_weekdays": [0, 1, 2, 3, 4]
}
```

### Transporte Fim de Semana

```json
{
  "chave": "AB12",
  "request_kind": "weekend",
  "requested_time": "08:00",
  "selected_weekdays": [5, 6]
}
```

### Transporte Extra (data e hora específicas)

```json
{
  "chave": "AB12",
  "request_kind": "extra",
  "requested_time": "14:00",
  "requested_date": "2026-05-30"
}
```

### Campos do request body

| Campo              | Tipo            | Obrigatório       | Restrições                                         | Descrição                                                      |
|--------------------|-----------------|-------------------|----------------------------------------------------|----------------------------------------------------------------|
| `chave`            | string          | Sim               | 4 caracteres alfanuméricos maiúsculos              | Chave do usuário                                               |
| `request_kind`     | string          | Sim               | `"regular"`, `"weekend"` ou `"extra"`              | Modalidade da solicitação                                      |
| `requested_time`   | string \| null  | Não               | Formato `HH:MM`                                    | Horário desejado. Se omitido, usa o horário atual (SGT)        |
| `requested_date`   | date \| null    | Sim para `extra`  | Formato `YYYY-MM-DD`. Proibido para `regular`/`weekend` | Data da viagem extra                                      |
| `selected_weekdays`| list[int] \| null | Não             | `regular`: 0–4 (seg–sex). `weekend`: 5–6 (sáb–dom). Proibido para `extra` | Dias da semana. Padrão: todos os dias úteis para `regular`, sáb+dom para `weekend` |

> **Codificação dos dias:** `0`=Segunda, `1`=Terça, `2`=Quarta, `3`=Quinta, `4`=Sexta, `5`=Sábado, `6`=Domingo.

---

## Resposta

```json
{
  "ok": true,
  "message": "Solicitacao de Transporte Rotineiro enviada.",
  "state": {
    "chave": "AB12",
    "end_rua": "Rua das Flores, 45",
    "zip": "123456",
    "status": "pending",
    "request_id": 82,
    "request_kind": "regular",
    "route_kind": null,
    "service_date": null,
    "requested_time": "07:30",
    "boarding_time": null,
    "confirmation_deadline_time": null,
    "vehicle_type": null,
    "vehicle_plate": null,
    "vehicle_color": null,
    "tolerance_minutes": null,
    "awareness_required": false,
    "awareness_confirmed": false,
    "requests": [...]
  }
}
```

> Quando a solicitação já existia (não foi criada agora), a mensagem será `"Ja existe uma solicitacao de Transporte Rotineiro ativa."` e `ok` continua `true`.

---

## Códigos de status HTTP

| Código | Significado                                                               |
|--------|---------------------------------------------------------------------------|
| `200`  | Solicitação criada ou já existente retornada                              |
| `400`  | Endereço não cadastrado, data ausente para `extra`, ou horário ausente para `extra` |
| `401`  | Sessão inválida ou expirada, ou chave não confere                         |
| `409`  | Conflito de solicitação (ex.: já existe uma solicitação incompatível)     |
| `422`  | Campos inválidos no body                                                  |

---

## Side effects

Quando uma nova solicitação é criada:
- Persiste registro na tabela `transport_requests`.
- Emite notificação SSE admin via `notify_admin_data_changed("event")`.
- Emite evento de reavaliação de demanda (`transport_request_changed`) para o sistema de planejamento de rotas.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "request_kind": "regular", "requested_time": "07:30", "selected_weekdays": [0, 1, 2, 3, 4]}' \
  "http://127.0.0.1:8000/api/web/transport/request"
```
