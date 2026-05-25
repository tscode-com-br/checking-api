# `POST /api/web/transport/vehicle-request`

## Visão Geral

**Este endpoint é um alias legado de `POST /api/web/transport/request`.** Ambos compartilham exatamente a mesma implementação interna e aceitam o mesmo payload. Manter por compatibilidade com clientes mais antigos.

Novas integrações devem usar `POST /api/web/transport/request`.

| Atributo         | Valor                                                                   |
|------------------|-------------------------------------------------------------------------|
| **Método**       | `POST`                                                                  |
| **Path**         | `/api/web/transport/vehicle-request`                                    |
| **Autenticação** | Cookie de sessão + chave deve corresponder                              |
| **Content-Type** | `application/json`                                                      |

---

## Autenticação

Idêntica a `POST /api/web/transport/request`.

---

## Request Body

Idêntico a `POST /api/web/transport/request`. Ver documentação completa em [`post_web_transport_request.md`](post_web_transport_request.md).

```json
{
  "chave": "AB12",
  "request_kind": "regular",
  "requested_time": "07:30",
  "selected_weekdays": [0, 1, 2, 3, 4]
}
```

---

## Resposta

Idêntica a `POST /api/web/transport/request`.

---

## Códigos de status HTTP

Idênticos a `POST /api/web/transport/request`.

| Código | Significado                                                               |
|--------|---------------------------------------------------------------------------|
| `200`  | Solicitação criada ou já existente retornada                              |
| `400`  | Endereço não cadastrado, data ausente para `extra`, ou horário ausente para `extra` |
| `401`  | Sessão inválida ou expirada, ou chave não confere                         |
| `409`  | Conflito de solicitação                                                   |
| `422`  | Campos inválidos no body                                                  |

---

## Side effects

Idênticos a `POST /api/web/transport/request`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "request_kind": "extra", "requested_time": "14:00", "requested_date": "2026-05-30"}' \
  "http://127.0.0.1:8000/api/web/transport/vehicle-request"
```
