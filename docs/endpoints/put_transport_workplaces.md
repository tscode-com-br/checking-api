# `PUT /api/transport/workplaces/{workplace_id}`

## Visão Geral

Atualiza os dados operacionais de transporte de um workplace existente. **O nome do workplace (`workplace`) não pode ser alterado** — apenas os campos operacionais (endereço, grupo, ponto de embarque, janela de transporte, horário de saída e restrições de serviço) são atualizáveis por este endpoint.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `PUT`                                                             |
| **Path**         | `/api/transport/workplaces/{workplace_id}`                        |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Path Parameters

| Parâmetro      | Tipo  | Descrição                                  |
|----------------|-------|--------------------------------------------|
| `workplace_id` | `int` | ID numérico do workplace a ser atualizado. |

### Request Body

Mesmos campos que `POST /api/transport/workplaces`, exceto `workplace` (nome), que **não deve ser enviado**:

```json
{
  "address": "Av. Paulista, 1000",
  "zip": "01310-200",
  "country": "Brasil",
  "transport_group": "Grupo B",
  "boarding_point": "Portaria Nova",
  "transport_window_start": "16:30",
  "transport_window_end": "18:00",
  "service_restrictions": "Sem serviço nas sextas-feiras",
  "transport_work_to_home_time": "16:30"
}
```

| Campo                        | Tipo           | Obrigatório | Restrições                                   | Descrição                                              |
|------------------------------|----------------|-------------|----------------------------------------------|--------------------------------------------------------|
| `address`                    | `string`       | Sim         | 3–255 chars                                  | Endereço completo.                                     |
| `zip`                        | `string`       | Sim         | 1–10 chars                                   | CEP/Código postal.                                     |
| `country`                    | `string`       | Sim         | 2–80 chars                                   | País.                                                  |
| `transport_group`            | `string\|null` | Não         | Máx. 80 chars                                | Grupo de transporte.                                   |
| `boarding_point`             | `string\|null` | Não         | Máx. 255 chars                               | Ponto de embarque.                                     |
| `transport_window_start`     | `string\|null` | Condicional | Formato `HH:MM`; ambos ou nenhum             | Início da janela de atendimento.                       |
| `transport_window_end`       | `string\|null` | Condicional | Formato `HH:MM`; deve ser posterior ao start | Fim da janela de atendimento.                          |
| `service_restrictions`       | `string\|null` | Não         | Máx. 500 chars                               | Restrições de serviço.                                 |
| `transport_work_to_home_time`| `string\|null` | Não         | Formato `HH:MM`                              | Horário de saída work-to-home específico.              |

---

## Resposta

Retorna o workplace atualizado:

```json
{
  "id": 1,
  "workplace": "Escritório Central",
  "address": "Av. Paulista, 1000",
  "zip": "01310-200",
  "country": "Brasil",
  "transport_group": "Grupo B",
  "boarding_point": "Portaria Nova",
  "transport_window_start": "16:30",
  "transport_window_end": "18:00",
  "service_restrictions": "Sem serviço nas sextas-feiras",
  "transport_work_to_home_time": "16:30"
}
```

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Workplace atualizado com sucesso.         |
| `401`  | Sessão de transporte ausente ou inválida. |
| `404`  | Workplace não encontrado.                 |
| `422`  | Corpo inválido.                           |

---

## Side effects

- Persiste as alterações no banco de dados.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_workplace_context_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Av. Paulista, 1000",
    "zip": "01310-200",
    "country": "Brasil",
    "transport_group": null,
    "boarding_point": null,
    "transport_window_start": null,
    "transport_window_end": null,
    "service_restrictions": null,
    "transport_work_to_home_time": null
  }' \
  http://127.0.0.1:8000/api/transport/workplaces/1 | python -m json.tool
```
