# `POST /api/transport/workplaces`

## Visão Geral

Cria um novo workplace (local de trabalho) com seus dados operacionais de transporte. O nome do workplace é único e imutável após a criação (para alterar apenas os dados operacionais, use `PUT /api/transport/workplaces/{workplace_id}`).

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/workplaces`                                       |
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
```

| Campo                        | Tipo           | Obrigatório | Restrições                              | Descrição                                                                        |
|------------------------------|----------------|-------------|------------------------------------------|----------------------------------------------------------------------------------|
| `workplace`                  | `string`       | Sim         | 2–120 chars                              | Nome único do workplace. Não pode ser alterado após a criação.                   |
| `address`                    | `string`       | Sim         | 3–255 chars                              | Endereço completo.                                                               |
| `zip`                        | `string`       | Sim         | 1–10 chars                               | CEP/Código postal.                                                               |
| `country`                    | `string`       | Sim         | 2–80 chars                               | País.                                                                            |
| `transport_group`            | `string\|null` | Não         | Máx. 80 chars                            | Grupo de transporte.                                                             |
| `boarding_point`             | `string\|null` | Não         | Máx. 255 chars                           | Ponto de embarque.                                                               |
| `transport_window_start`     | `string\|null` | Condicional | Formato `HH:MM`; ambos ou nenhum         | Início da janela de atendimento. Deve ser informado com `transport_window_end`.  |
| `transport_window_end`       | `string\|null` | Condicional | Formato `HH:MM`; deve ser posterior ao start | Fim da janela de atendimento. Deve ser posterior a `transport_window_start`.  |
| `service_restrictions`       | `string\|null` | Não         | Máx. 500 chars                           | Restrições de serviço (texto livre).                                             |
| `transport_work_to_home_time`| `string\|null` | Não         | Formato `HH:MM`                          | Horário de saída work-to-home específico deste workplace.                        |

**Regra**: `transport_window_start` e `transport_window_end` devem ser fornecidos juntos ou ambos omitidos; `transport_window_end` deve ser posterior a `transport_window_start`.

---

## Resposta

Retorna o workplace criado no mesmo formato do `GET /api/transport/workplaces`:

```json
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
```

---

## Códigos de status HTTP

| Código | Significado                                           |
|--------|-------------------------------------------------------|
| `200`  | Workplace criado com sucesso.                         |
| `401`  | Sessão de transporte ausente ou inválida.             |
| `409`  | Já existe um workplace com este nome.                 |
| `422`  | Corpo inválido (campo ausente, tipo errado, regra violada). |

---

## Side effects

- Persiste o novo workplace no banco de dados.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_workplace_context_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "workplace": "Escritório Central",
    "address": "Rua das Flores, 100",
    "zip": "01310-100",
    "country": "Brasil",
    "transport_group": null,
    "boarding_point": null,
    "transport_window_start": null,
    "transport_window_end": null,
    "service_restrictions": null,
    "transport_work_to_home_time": null
  }' \
  http://127.0.0.1:8000/api/transport/workplaces | python -m json.tool
```
