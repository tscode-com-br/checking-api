# `GET /api/admin/events`

## Visão Geral

Retorna os últimos 200 eventos de sistema registrados na tabela `check_events`, excluindo entradas do tipo `event_archive` (que representam o próprio processo de arquivamento). Os eventos são filtrados de acordo com o escopo de projetos do administrador autenticado e ordenados do mais recente para o mais antigo.

| Atributo         | Valor                                  |
|------------------|----------------------------------------|
| **Método**       | `GET`                                  |
| **Path**         | `/api/admin/events`                    |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | —                                      |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

Nenhum. A listagem não aceita filtros via query string; para consulta avançada com filtros e paginação, utilize `GET /api/admin/database-events`.

---

## Resposta

**HTTP 200 — Sucesso**

Array de até 200 objetos `EventRow`, ordenados por `id` decrescente.

```json
[
  {
    "id": 4201,
    "source": "web",
    "rfid": "04AB12CD",
    "chave": "AB12",
    "device_id": null,
    "local": "main",
    "action": "checkin",
    "status": "done",
    "message": "Check-in realizado",
    "details": "chave=AB12",
    "project": "PROJ-A",
    "ontime": true,
    "request_path": "/api/web/check/checkin",
    "http_status": 200,
    "retry_count": 0,
    "event_time": "2026-05-25T08:30:00Z",
    "event_date_label": "25/05/2026",
    "event_time_label": "08:30:00",
    "timezone_name": "Asia/Singapore",
    "timezone_label": "SGT (UTC+8)"
  }
]
```

| Campo               | Tipo              | Descrição                                                                 |
|---------------------|-------------------|---------------------------------------------------------------------------|
| `id`                | `integer`         | ID sequencial do evento.                                                  |
| `source`            | `string`          | Origem: `web`, `device`, `admin`, `system`, `provider`.                   |
| `rfid`              | `string \| null`  | Código RFID da tag lida, se disponível.                                   |
| `chave`             | `string \| null`  | Chave de 4 caracteres do usuário, se resolvida.                           |
| `device_id`         | `string \| null`  | Identificador do dispositivo ESP32, se aplicável.                         |
| `local`             | `string \| null`  | Local físico do evento (ex.: `main`, `co80`).                             |
| `action`            | `string`          | Ação registrada. Máximo 16 caracteres. Exemplos: `checkin`, `checkout`, `accident_open`, `accident_close`, `login`, `register`. |
| `status`            | `string`          | Status da operação: `done`, `failed`, `blocked`, `created`, etc.          |
| `message`           | `string`          | Mensagem legível descrevendo o resultado.                                  |
| `details`           | `string \| null`  | Texto adicional de depuração (pares `chave=valor` separados por `;`).     |
| `project`           | `string \| null`  | Projeto ao qual o evento pertence.                                         |
| `ontime`            | `boolean \| null` | `true` = horário regular; `false` = retroativo; `null` = não aplicável.   |
| `request_path`      | `string \| null`  | Caminho HTTP que originou o evento.                                        |
| `http_status`       | `integer \| null` | Código HTTP retornado pela operação originadora.                           |
| `retry_count`       | `integer`         | Número de tentativas de reenvio (dispositivo).                             |
| `event_time`        | `datetime \| null`| Timestamp ISO 8601 UTC do evento. `null` se o administrador não tem permissão para ver horários. |
| `event_date_label`  | `string`          | Data formatada no fuso do projeto: `DD/MM/YYYY`.                          |
| `event_time_label`  | `string \| null`  | Horário formatado: `HH:MM:SS`. `null` para admins sem permissão de horário. |
| `timezone_name`     | `string`          | Nome IANA do fuso (ex.: `Asia/Singapore`).                                |
| `timezone_label`    | `string`          | Rótulo legível do fuso (ex.: `SGT (UTC+8)`).                              |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso. Array retornado (pode ser vazio `[]`).                      |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/events
```
