# `POST /api/web/transport/acknowledge`

## Visão Geral

Registra a ciência do usuário em relação a uma atribuição de transporte confirmada pelo admin. Deve ser chamado quando `awareness_required=true` e `awareness_confirmed=false` no estado de transporte. Após registrar a ciência, retorna o estado atualizado.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/transport/acknowledge`               |
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

| Campo        | Tipo   | Obrigatório | Restrições                                | Descrição                                             |
|--------------|--------|-------------|-------------------------------------------|-------------------------------------------------------|
| `chave`      | string | Sim         | 4 caracteres alfanuméricos maiúsculos     | Chave do usuário                                      |
| `request_id` | int    | Sim         | Valor positivo (≥ 1)                      | ID da solicitação de transporte cujo acknowledge se registra |

> A solicitação informada deve pertencer ao usuário autenticado e estar com status `"active"`. Caso contrário, retorna `404`.

---

## Resposta

```json
{
  "ok": true,
  "message": "Ciencia registrada com sucesso.",
  "state": {
    "chave": "AB12",
    "end_rua": "Rua das Flores, 45",
    "zip": "123456",
    "status": "confirmed",
    "request_id": 82,
    "request_kind": "regular",
    "route_kind": "home_to_work",
    "service_date": "2026-05-26",
    "requested_time": "07:30",
    "boarding_time": "07:25",
    "confirmation_deadline_time": "07:00",
    "vehicle_type": "van",
    "vehicle_plate": "ABC1D23",
    "vehicle_color": "Branco",
    "tolerance_minutes": 10,
    "awareness_required": true,
    "awareness_confirmed": true,
    "requests": [...]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                         |
|--------|-------------------------------------------------------------------------------------|
| `200`  | Ciência registrada com sucesso                                                      |
| `401`  | Sessão inválida ou expirada, ou chave não confere                                   |
| `404`  | Solicitação não encontrada, não pertence ao usuário ou não está ativa               |
| `409`  | Nenhuma atribuição de transporte confirmada para o dia atual — ciência prematura    |
| `422`  | Campos inválidos no body                                                            |

---

## Side effects

- Marca as atribuições do dia como `awareness_confirmed=true` em `transport_assignments`.
- Emite notificação SSE admin via `notify_admin_data_changed("event")`.
- Emite notificação SSE de transporte via `notify_transport_data_changed("event")`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "request_id": 82}' \
  "http://127.0.0.1:8000/api/web/transport/acknowledge"
```
