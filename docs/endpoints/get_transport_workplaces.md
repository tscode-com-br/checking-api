# `GET /api/transport/workplaces`

## Visão Geral

Retorna a lista completa de workplaces (locais de trabalho) cadastrados no sistema, com todos os dados operacionais de transporte: endereço, grupo, ponto de embarque, janela de transporte e horário específico de saída work-to-home.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/workplaces`                                       |
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
    "workplace": "Escritório Central",
    "address": "Rua das Flores, 100",
    "zip": "01310-100",
    "country": "Brasil",
    "transport_group": "Grupo A",
    "boarding_point": "Portaria Principal",
    "transport_window_start": "17:00",
    "transport_window_end": "18:30",
    "service_restrictions": null,
    "transport_work_to_home_time": "17:00"
  }
]
```

### Campos de cada workplace

| Campo                       | Tipo           | Descrição                                                                        |
|-----------------------------|----------------|----------------------------------------------------------------------------------|
| `id`                        | `int`          | Identificador único do workplace.                                                |
| `workplace`                 | `string`       | Nome único do workplace (chave natural — usado em filtros e no painel).           |
| `address`                   | `string`       | Endereço completo.                                                               |
| `zip`                       | `string`       | CEP/Código postal.                                                               |
| `country`                   | `string`       | País.                                                                            |
| `transport_group`           | `string\|null` | Grupo de transporte (agrupa workplaces para rotas compartilhadas).               |
| `boarding_point`            | `string\|null` | Descrição do ponto de embarque/desembarque.                                      |
| `transport_window_start`    | `string\|null` | Início da janela de atendimento de transporte (`HH:MM`).                         |
| `transport_window_end`      | `string\|null` | Fim da janela de atendimento de transporte (`HH:MM`).                            |
| `service_restrictions`      | `string\|null` | Texto livre com restrições de serviço (ex.: "Sem serviço às sextas").            |
| `transport_work_to_home_time`| `string\|null` | Horário de saída work-to-home específico deste workplace (`HH:MM`); `null` usa o horário global. |

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Lista retornada (pode ser vazia `[]`).    |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<valor_do_cookie>" \
  http://127.0.0.1:8000/api/transport/workplaces | python -m json.tool
```
