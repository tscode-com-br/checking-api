# `GET /api/admin/events/{event_id}`

## Visão Geral

> **Atenção:** Este endpoint **não está implementado** na versão atual do roteador `admin.py`. Não existe uma rota `GET /api/admin/events/{event_id}` no código-fonte. Esta documentação descreve o comportamento esperado caso o endpoint seja implementado no futuro, servindo como especificação de referência.

Retornaria os detalhes completos de um único evento de sistema identificado pelo seu `id` na tabela `check_events`.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `GET`                                   |
| **Path**         | `/api/admin/events/{event_id}`          |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | —                                       |

---

## Autenticação

Requereria sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornariam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

### Path Parameters

| Parâmetro   | Tipo      | Descrição                                      |
|-------------|-----------|------------------------------------------------|
| `event_id`  | `integer` | ID numérico do evento na tabela `check_events`. |

---

## Resposta Esperada

**HTTP 200 — Sucesso**

Objeto `EventRow` com os campos do evento solicitado (mesma estrutura da listagem em `GET /api/admin/events`):

```json
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
```

Consulte a tabela de campos em [`get_admin_events.md`](./get_admin_events.md) para a descrição completa de cada campo.

---

## Códigos de status HTTP Esperados

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso. Objeto do evento retornado.                                 |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |
| `404`  | Evento com o `event_id` informado não encontrado.                    |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
# Endpoint ainda não implementado. Exemplo meramente ilustrativo:
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/events/4201
```
