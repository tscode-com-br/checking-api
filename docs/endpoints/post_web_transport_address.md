# `POST /api/web/transport/address`

## Visão Geral

Atualiza o endereço residencial e o CEP do usuário autenticado. O endereço é obrigatório para que o usuário possa criar solicitações de transporte. Após a atualização, retorna o estado de transporte atualizado.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/transport/address`                   |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no corpo da requisição deve coincidir com o valor armazenado no cookie. Em caso de falha retorna `401`.

---

## Request Body

```json
{
  "chave": "AB12",
  "end_rua": "Rua das Flores, 45",
  "zip": "123456"
}
```

### Campos do request body

| Campo     | Tipo   | Obrigatório | Restrições                                             | Descrição                                |
|-----------|--------|-------------|--------------------------------------------------------|------------------------------------------|
| `chave`   | string | Sim         | 4 caracteres alfanuméricos maiúsculos                  | Chave do usuário                         |
| `end_rua` | string | Sim         | Mínimo 3, máximo 255 caracteres                        | Endereço completo com rua e número       |
| `zip`     | string | Sim         | Exatamente 6 dígitos (outros caracteres são descartados) | CEP/ZIP code residencial               |

> **Nota sobre `zip`:** O validador extrai apenas os dígitos da string fornecida. Enviar `"123-456"` resulta em `"123456"` armazenado.

---

## Resposta

```json
{
  "ok": true,
  "message": "Endereco atualizado com sucesso.",
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

### Campos da resposta

| Campo     | Tipo                   | Descrição                                   |
|-----------|------------------------|---------------------------------------------|
| `ok`      | bool                   | Sempre `true` em caso de sucesso            |
| `message` | string                 | Mensagem de confirmação                     |
| `state`   | WebTransportStateResponse | Estado de transporte do usuário atualizado (ver `GET /api/web/transport/state`) |

---

## Códigos de status HTTP

| Código | Significado                                       |
|--------|---------------------------------------------------|
| `200`  | Endereço atualizado com sucesso                   |
| `401`  | Sessão inválida ou expirada, ou chave não confere |
| `422`  | Campos inválidos (endereço muito curto, ZIP sem 6 dígitos etc.) |

---

## Side effects

- Persiste `end_rua` e `zip` no registro do usuário (`users`).
- Emite notificação SSE admin via `notify_admin_data_changed("register")`.
- Emite evento de reavaliação de transporte (`transport_user_context_changed`) para o sistema de planejamento de rotas.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "end_rua": "Rua das Flores, 45", "zip": "123456"}' \
  "http://127.0.0.1:8000/api/web/transport/address"
```
