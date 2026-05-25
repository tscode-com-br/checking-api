# `PUT /api/transport/date-settings`

## Visão Geral

Define um horário de saída work-to-home específico para uma data, sobrescrevendo o horário global configurado em `PUT /api/transport/settings`. Útil para dias com expediente diferenciado (ex.: véspera de feriado). A sobrescrita por data tem prioridade sobre a configuração global, mas é superada por configurações específicas de workplace.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `PUT`                                                             |
| **Path**         | `/api/transport/date-settings`                                    |
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
  "service_date": "2026-05-25",
  "work_to_home_time": "16:00"
}
```

| Campo               | Tipo     | Obrigatório | Restrições      | Descrição                                                          |
|---------------------|----------|-------------|------------------|--------------------------------------------------------------------|
| `service_date`      | `date`   | Sim         | Formato `YYYY-MM-DD` | Data para a qual o horário de saída é sobrescrito.             |
| `work_to_home_time` | `string` | Sim         | Formato `HH:MM`  | Horário de saída específico para esta data (ex.: `"16:00"`).       |

---

## Resposta

```json
{
  "service_date": "2026-05-25",
  "work_to_home_time": "16:00"
}
```

| Campo               | Tipo     | Descrição                                        |
|---------------------|----------|--------------------------------------------------|
| `service_date`      | `date`   | Data da configuração criada/atualizada.          |
| `work_to_home_time` | `string` | Horário de saída configurado para esta data.     |

---

## Hierarquia de prioridade para `work_to_home_time`

1. **Workplace** (`workplace_work_to_home_time`) — maior prioridade
2. **Date override** (`date_override_work_to_home_time`) — esta configuração
3. **Global** (`work_to_home_time` em `/api/transport/settings`) — menor prioridade

Para verificar qual horário está em vigor para uma data/workplace, consulte `GET /api/transport/work-to-home-time-policy`.

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Configuração salva com sucesso.           |
| `401`  | Sessão de transporte ausente ou inválida. |
| `422`  | Corpo da requisição inválido.             |

---

## Side effects

- Persiste (cria ou atualiza) a configuração de data no banco de dados.
- Emite evento de reavaliação `transport_timing_policy_changed` para `route_kind = work_to_home`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"service_date": "2026-05-25", "work_to_home_time": "16:00"}' \
  http://127.0.0.1:8000/api/transport/date-settings | python -m json.tool
```
