# `PUT /api/transport/vehicles/{vehicle_id}`

## Visão Geral

Atualiza os dados base de um veículo existente: placa, tipo, cor, capacidade e tolerância. Este endpoint **não** altera os schedules (programações) do veículo — para isso, use `PUT /api/transport/vehicle-schedules/{schedule_id}`.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `PUT`                                                             |
| **Path**         | `/api/transport/vehicles/{vehicle_id}`                            |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Path Parameters

| Parâmetro    | Tipo  | Descrição                            |
|--------------|-------|--------------------------------------|
| `vehicle_id` | `int` | ID do veículo a ser atualizado.      |

### Request Body

```json
{
  "placa": "SGP-5678",
  "tipo": "minivan",
  "color": "prata",
  "lugares": 7,
  "tolerance": 15
}
```

| Campo       | Tipo           | Obrigatório | Restrições                    | Descrição                          |
|-------------|----------------|-------------|--------------------------------|------------------------------------|
| `placa`     | `string\|null` | Não         | Máx. 20 chars                  | Placa do veículo.                  |
| `tipo`      | `string\|null` | Não         | `carro\|minivan\|van\|onibus`  | Tipo do veículo.                   |
| `color`     | `string\|null` | Não         | Máx. 40 chars                  | Cor do veículo.                    |
| `lugares`   | `int\|null`    | Não         | 1–99                           | Capacidade de passageiros.         |
| `tolerance` | `int\|null`    | Não         | 0–240 minutos                  | Tolerância de atraso em minutos.   |

Todos os campos são opcionais (`null` mantém o valor anterior ou deixa em branco).

---

## Resposta

```json
{
  "ok": true,
  "message": "Vehicle updated successfully.",
  "message_key": "status.vehicleUpdated",
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

---

## Erros estruturados

Quando o veículo não é encontrado:

```json
{
  "detail": {
    "message": "Vehicle not found.",
    "message_key": "status.couldNotUpdateVehicle",
    "error_code": "transport_vehicle_not_found",
    "issues": [{"code": "transport_vehicle_not_found"}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Veículo atualizado com sucesso.           |
| `401`  | Sessão de transporte ausente ou inválida. |
| `404`  | Veículo não encontrado.                   |
| `409`  | Violação de regra de negócio.             |
| `422`  | Corpo inválido.                           |

---

## Side effects

- Persiste as alterações no banco de dados.
- Notifica o painel admin via SSE (`notify_admin_data_changed`).
- Emite evento de reavaliação `transport_vehicle_supply_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"placa": "SGP-5678", "tipo": "minivan", "color": "prata", "lugares": 7, "tolerance": 15}' \
  http://127.0.0.1:8000/api/transport/vehicles/5 | python -m json.tool
```
