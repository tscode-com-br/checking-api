# `POST /api/web/transport/cancel`

## Visão Geral

Cancela uma solicitação de transporte ativa do usuário autenticado. Ao cancelar, o admin é notificado em tempo real e o sistema reavalia a demanda de transporte do dia. Retorna o estado de transporte atualizado após o cancelamento.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/transport/cancel`                    |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no body deve coincidir com o valor no cookie. Em caso de falha retorna `401`.

---

## Request Body

```json
{
  "chave": "AB12",
  "request_id": 82
}
```

### Campos do request body

| Campo        | Tipo   | Obrigatório | Restrições                                | Descrição                                            |
|--------------|--------|-------------|-------------------------------------------|------------------------------------------------------|
| `chave`      | string | Sim         | 4 caracteres alfanuméricos maiúsculos     | Chave do usuário                                     |
| `request_id` | int    | Sim         | Valor positivo (≥ 1)                      | ID da solicitação de transporte a cancelar           |

> A solicitação informada deve pertencer ao usuário autenticado e estar com status `"active"`. Caso contrário, retorna `404`.

---

## Resposta

```json
{
  "ok": true,
  "message": "Solicitacao de transporte cancelada.",
  "state": {
    "chave": "AB12",
    "end_rua": "Rua das Flores, 45",
    "zip": "123456",
    "status": "available",
    "request_id": null,
    "request_kind": null,
    "route_kind": null,
    "service_date": null,
    "requested_time": null,
    "boarding_time": null,
    "confirmation_deadline_time": null,
    "vehicle_type": null,
    "vehicle_plate": null,
    "vehicle_color": null,
    "tolerance_minutes": null,
    "awareness_required": false,
    "awareness_confirmed": false,
    "requests": []
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                                        |
|--------|--------------------------------------------------------------------|
| `200`  | Solicitação cancelada com sucesso                                  |
| `401`  | Sessão inválida ou expirada, ou chave não confere                  |
| `404`  | Solicitação não encontrada, não pertence ao usuário ou não está ativa |
| `422`  | Campos inválidos no body                                           |

---

## Side effects

- Marca a solicitação como `"cancelled"` em `transport_requests`.
- Cancela atribuições associadas (`transport_assignments`) que ainda estejam pendentes.
- Emite notificação SSE admin via `notify_admin_data_changed("event")`.
- Emite evento de reavaliação de demanda (`transport_request_changed`) para o sistema de planejamento de rotas.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "request_id": 82}' \
  "http://127.0.0.1:8000/api/web/transport/cancel"
```
