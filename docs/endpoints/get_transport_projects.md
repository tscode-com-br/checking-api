# `GET /api/transport/projects`

## Visão Geral

Retorna a lista de todos os projetos cadastrados no sistema, com seus metadados de localização, fuso horário e configurações. Utilizado pelo painel de transporte para popular filtros, seleções de escopo e referências de projetos.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/projects`                                         |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (resposta)                                     |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

Nenhum parâmetro de query, path ou corpo de requisição.

---

## Resposta

```json
[
  {
    "id": 1,
    "name": "Projeto Alpha",
    "country_code": "SG",
    "country_name": "Singapore",
    "timezone_name": "Asia/Singapore",
    "timezone_label": "Singapore (SGT +08:00)",
    "address": "1 Raffles Place",
    "zip_code": "048616",
    "forms_enabled": true,
    "transport_enabled": true,
    "emergency_phone": "+6512345678",
    "twilio_account_sid": "",
    "twilio_auth_token": "",
    "twilio_phone_number": "",
    "mobile_admin": "",
    "email_local_emergency": "",
    "emergency_call_message": "",
    "inactivity_days_threshold": 60,
    "mixed_zone_interval_minutes": 30,
    "minimum_checkout_distance_meters": 2000
  }
]
```

### Campos de cada projeto

| Campo                              | Tipo     | Descrição                                                         |
|------------------------------------|----------|-------------------------------------------------------------------|
| `id`                               | `int`    | Identificador único do projeto.                                   |
| `name`                             | `string` | Nome do projeto.                                                  |
| `country_code`                     | `string` | Código ISO-2 do país (ex.: `"SG"`, `"BR"`).                       |
| `country_name`                     | `string` | Nome do país.                                                     |
| `timezone_name`                    | `string` | Nome do fuso horário IANA (ex.: `"Asia/Singapore"`).              |
| `timezone_label`                   | `string` | Rótulo formatado para exibição (ex.: `"Singapore (SGT +08:00)"`). |
| `address`                          | `string` | Endereço do projeto.                                              |
| `zip_code`                         | `string` | CEP/Código postal.                                                |
| `forms_enabled`                    | `bool`   | Se formulários estão habilitados.                                 |
| `transport_enabled`                | `bool`   | Se o transporte está habilitado para o projeto.                   |
| `emergency_phone`                  | `string` | Telefone de emergência.                                           |
| `inactivity_days_threshold`        | `int`    | Dias sem atividade antes de marcar usuário como inativo.          |
| `mixed_zone_interval_minutes`      | `int`    | Intervalo em minutos para zone mista.                             |
| `minimum_checkout_distance_meters` | `int`    | Distância mínima para checkout (metros).                          |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia `[]`). |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<valor_do_cookie>" \
  http://127.0.0.1:8000/api/transport/projects | python -m json.tool
```
