# `POST /api/transport/auth/logout`

## Visão Geral

Encerra a sessão de transporte do usuário atual. Remove o `transport_user_id` do cookie de sessão. Sempre retorna sucesso, independentemente de haver ou não uma sessão ativa.

| Atributo         | Valor                             |
|------------------|-----------------------------------|
| **Método**       | `POST`                            |
| **Path**         | `/api/transport/auth/logout`      |
| **Autenticação** | Nenhuma — pode ser chamado sem sessão ativa |
| **Content-Type** | `application/json` (resposta)     |

---

## Autenticação

Não requer sessão de transporte ativa. O endpoint limpa a sessão se existir; caso contrário, não faz nada. Nunca retorna erro.

---

## Parâmetros

Nenhum parâmetro de query, path ou corpo de requisição.

---

## Resposta

```json
{
  "ok": true,
  "message": "Transport session closed.",
  "message_key": "status.accessReset",
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

### Campos da resposta

| Campo           | Tipo     | Descrição                                                   |
|-----------------|----------|-------------------------------------------------------------|
| `ok`            | `bool`   | Sempre `true`.                                              |
| `message`       | `string` | Mensagem descritiva do resultado.                           |
| `message_key`   | `string` | Chave i18n `"status.accessReset"`.                          |
| `message_params`| `object` | Parâmetros adicionais para a mensagem i18n (sempre vazio).  |
| `error_code`    | `null`   | Sempre `null` neste endpoint.                               |
| `issues`        | `array`  | Sempre vazio neste endpoint.                                |

---

## Códigos de status HTTP

| Código | Significado                   |
|--------|-------------------------------|
| `200`  | Logout realizado com sucesso. |

---

## Side effects

- Remove `transport_user_id` do cookie de sessão (se presente).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -c cookies.txt \
  -X POST \
  http://127.0.0.1:8000/api/transport/auth/logout | python -m json.tool
```
