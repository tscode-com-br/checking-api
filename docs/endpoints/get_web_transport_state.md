# `GET /api/web/transport/state`

## Visão Geral

Retorna o estado atual de transporte do usuário autenticado: se há solicitação ativa, confirmação do admin, dados do veículo, endereço cadastrado e a lista completa de solicitações recentes.

| Atributo         | Valor                                           |
|------------------|-------------------------------------------------|
| **Método**       | `GET`                                           |
| **Path**         | `/api/web/transport/state`                      |
| **Autenticação** | Cookie de sessão + chave deve corresponder      |

---

## Autenticação

Requer cookie de sessão `web_user_chave` definido por um login prévio (`POST /api/web/auth/login`). O valor do cookie deve ser igual ao parâmetro `chave` informado na query string. Em caso de falha retorna `401`.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo   | Obrigatório | Descrição                                                   |
|-----------|--------|-------------|-------------------------------------------------------------|
| `chave`   | string | Sim         | Chave do usuário (4 caracteres alfanuméricos, ex.: `"AB12"`) |

---

## Resposta

```json
{
  "chave": "AB12",
  "end_rua": "Rua das Flores, 45",
  "zip": "123456",
  "status": "confirmed",
  "request_id": 77,
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
  "awareness_confirmed": false,
  "requests": [
    {
      "request_id": 77,
      "request_kind": "regular",
      "status": "confirmed",
      "is_active": true,
      "service_date": "2026-05-26",
      "requested_time": "07:30",
      "selected_weekdays": [0, 1, 2, 3, 4],
      "route_kind": "home_to_work",
      "boarding_time": "07:25",
      "confirmation_deadline_time": "07:00",
      "vehicle_type": "van",
      "vehicle_plate": "ABC1D23",
      "vehicle_color": "Branco",
      "tolerance_minutes": 10,
      "awareness_required": true,
      "awareness_confirmed": false,
      "response_message": null,
      "created_at": "2026-05-25T10:00:00+08:00"
    }
  ]
}
```

### Descrição dos campos da resposta

| Campo                        | Tipo                                         | Descrição                                                                  |
|------------------------------|----------------------------------------------|----------------------------------------------------------------------------|
| `chave`                      | string                                       | Chave do usuário                                                           |
| `end_rua`                    | string \| null                               | Endereço residencial cadastrado                                             |
| `zip`                        | string \| null                               | CEP/ZIP (somente dígitos, 6 caracteres)                                    |
| `status`                     | `"available"` \| `"pending"` \| `"confirmed"` \| `"realized"` | Estado geral da solicitação de transporte do dia |
| `request_id`                 | int \| null                                  | ID da solicitação ativa (quando existe)                                    |
| `request_kind`               | `"regular"` \| `"weekend"` \| `"extra"` \| null | Tipo de solicitação ativa                                              |
| `route_kind`                 | `"home_to_work"` \| `"work_to_home"` \| null | Sentido da viagem confirmado                                               |
| `service_date`               | date \| null                                 | Data de serviço (ISO 8601, `YYYY-MM-DD`)                                   |
| `requested_time`             | string \| null                               | Horário solicitado (`HH:MM`)                                               |
| `boarding_time`              | string \| null                               | Horário de embarque confirmado pelo admin (`HH:MM`)                        |
| `confirmation_deadline_time` | string \| null                               | Prazo máximo para confirmar ciência (`HH:MM`)                              |
| `vehicle_type`               | `"carro"` \| `"minivan"` \| `"van"` \| `"onibus"` \| null | Tipo do veículo alocado                                       |
| `vehicle_plate`              | string \| null                               | Placa do veículo                                                           |
| `vehicle_color`              | string \| null                               | Cor do veículo                                                             |
| `tolerance_minutes`          | int \| null                                  | Tolerância de atraso em minutos (0–240)                                    |
| `awareness_required`         | bool                                         | Se o admin exige confirmação de ciência pelo passageiro                    |
| `awareness_confirmed`        | bool                                         | Se o usuário já confirmou ciência da atribuição                            |
| `requests`                   | array                                        | Lista de todas as solicitações ativas do usuário (ver campos acima)        |

---

## Códigos de status HTTP

| Código | Significado                                       |
|--------|---------------------------------------------------|
| `200`  | Sucesso — estado retornado                        |
| `401`  | Sessão inválida ou expirada, ou chave não confere |
| `404`  | Usuário não encontrado na base                    |
| `422`  | Parâmetro `chave` inválido                        |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/web/transport/state?chave=AB12"
```
