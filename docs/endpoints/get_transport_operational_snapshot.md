# `GET /api/transport/operational-snapshot`

## Visão Geral

Gera e retorna um snapshot operacional completo do estado de transporte para uma data e sentido de rota específicos. O snapshot é a base para construção de propostas de alocação — ele captura o estado atual das solicitações e veículos em um momento determinado, identificado por uma chave única (`snapshot_key`).

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/operational-snapshot`                             |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (resposta)                                     |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Query Parameters

| Parâmetro      | Tipo     | Obrigatório | Padrão           | Descrição                                               |
|----------------|----------|-------------|------------------|---------------------------------------------------------|
| `service_date` | `date`   | Não         | Data atual (SGT) | Data do serviço no formato `YYYY-MM-DD`.                |
| `route_kind`   | `string` | Não         | `home_to_work`   | Sentido da rota: `home_to_work` ou `work_to_home`.      |

---

## Resposta

```json
{
  "snapshot_key": "snapshot:home_to_work:2026-05-25:20260525T073000",
  "service_date": "2026-05-25",
  "route_kind": "home_to_work",
  "captured_at": "2026-05-25T07:30:00+08:00",
  "dashboard_generated_at": "2026-05-25T07:30:00+08:00",
  "arrive_at_work_time": "08:00",
  "work_to_home_departure_time": "17:30",
  "projects": [...],
  "regular_requests": [...],
  "weekend_requests": [],
  "extra_requests": [],
  "regular_vehicles": [...],
  "weekend_vehicles": [],
  "extra_vehicles": [],
  "regular_vehicle_registry": [...],
  "weekend_vehicle_registry": [],
  "extra_vehicle_registry": [],
  "workplaces": [...]
}
```

### Campos adicionais em relação ao dashboard

| Campo              | Tipo       | Descrição                                                                           |
|--------------------|------------|-------------------------------------------------------------------------------------|
| `snapshot_key`     | `string`   | Chave única que identifica este snapshot (formato: `snapshot:{route_kind}:{date}:{ts}`). |
| `captured_at`      | `datetime` | Timestamp exato em que o snapshot foi capturado.                                    |

Os demais campos são idênticos aos do endpoint `/api/transport/dashboard`. Consulte a documentação de `get_transport_dashboard.md` para a descrição completa dos campos de solicitações, veículos, projetos e workplaces.

---

## Diferença entre Dashboard e Snapshot

- **Dashboard** (`/dashboard`): dados para exibição imediata na interface.
- **Snapshot** (`/operational-snapshot`): dados capturados com `snapshot_key` e `captured_at` para uso como base de uma proposta de alocação. Deve ser passado como `snapshot` ao chamar `POST /proposals/build`.

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Snapshot gerado com sucesso.              |
| `401`  | Sessão de transporte ausente ou inválida. |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<valor_do_cookie>" \
  "http://127.0.0.1:8000/api/transport/operational-snapshot?service_date=2026-05-25&route_kind=home_to_work" \
  | python -m json.tool
```
