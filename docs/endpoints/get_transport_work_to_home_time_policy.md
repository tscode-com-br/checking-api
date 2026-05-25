# `GET /api/transport/work-to-home-time-policy`

## Visão Geral

Resolve e retorna o horário de saída work-to-home efetivo para uma data e workplace específicos, aplicando a hierarquia de prioridade: workplace > date override > global. Também retorna metadados do workplace (grupo, ponto de embarque, janela de transporte, restrições de serviço).

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/work-to-home-time-policy`                         |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (resposta)                                     |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Query Parameters

| Parâmetro      | Tipo     | Obrigatório | Descrição                                                                      |
|----------------|----------|-------------|--------------------------------------------------------------------------------|
| `service_date` | `date`   | **Sim**     | Data do serviço no formato `YYYY-MM-DD`.                                       |
| `workplace`    | `string` | Não         | Nome exato do workplace (campo `workplace` da tabela `workplaces`). Se omitido ou vazio, retorna apenas a política global/date-override sem contexto de workplace. |

---

## Resposta

```json
{
  "service_date": "2026-05-25",
  "workplace": "Escritório Central",
  "resolved_work_to_home_time": "17:00",
  "source": "workplace_context",
  "global_work_to_home_time": "17:30",
  "date_override_work_to_home_time": null,
  "workplace_work_to_home_time": "17:00",
  "transport_group": "Grupo A",
  "boarding_point": "Portaria Principal",
  "transport_window_start": "17:00",
  "transport_window_end": "18:30",
  "service_restrictions": null
}
```

### Campos da resposta

| Campo                          | Tipo           | Descrição                                                                             |
|--------------------------------|----------------|---------------------------------------------------------------------------------------|
| `service_date`                 | `date`         | Data consultada.                                                                      |
| `workplace`                    | `string\|null` | Nome do workplace consultado; `null` se não informado.                                |
| `resolved_work_to_home_time`   | `string`       | Horário efetivo de saída, no formato `HH:MM`.                                         |
| `source`                       | `string`       | Fonte do horário resolvido: `global`, `date_override` ou `workplace_context`.          |
| `global_work_to_home_time`     | `string`       | Horário global configurado em `/api/transport/settings`.                              |
| `date_override_work_to_home_time` | `string\|null` | Horário de sobrescrita por data (se configurado); `null` caso contrário.           |
| `workplace_work_to_home_time`  | `string\|null` | Horário específico do workplace; `null` se não configurado.                           |
| `transport_group`              | `string\|null` | Grupo de transporte do workplace.                                                     |
| `boarding_point`               | `string\|null` | Ponto de embarque do workplace.                                                       |
| `transport_window_start`       | `string\|null` | Início da janela de transporte do workplace, formato `HH:MM`.                         |
| `transport_window_end`         | `string\|null` | Fim da janela de transporte do workplace, formato `HH:MM`.                            |
| `service_restrictions`         | `string\|null` | Restrições de atendimento do workplace (texto livre).                                 |

#### Valores de `source`

| Valor               | Descrição                                                        |
|---------------------|------------------------------------------------------------------|
| `global`            | Horário do `work_to_home_time` global.                           |
| `date_override`     | Horário de sobrescrita configurado para esta data específica.    |
| `workplace_context` | Horário específico configurado no workplace.                     |

---

## Códigos de status HTTP

| Código | Significado                                                    |
|--------|----------------------------------------------------------------|
| `200`  | Política resolvida e retornada.                                |
| `401`  | Sessão de transporte ausente ou inválida.                      |
| `404`  | Workplace não encontrado (quando `workplace` é informado).     |
| `422`  | Parâmetro `service_date` ausente ou inválido.                  |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
# Sem workplace (retorna política global/date-override):
curl -s -b cookies.txt \
  "http://127.0.0.1:8000/api/transport/work-to-home-time-policy?service_date=2026-05-25" \
  | python -m json.tool

# Com workplace específico:
curl -s -b cookies.txt \
  "http://127.0.0.1:8000/api/transport/work-to-home-time-policy?service_date=2026-05-25&workplace=Escrit%C3%B3rio%20Central" \
  | python -m json.tool
```
