# `GET /api/admin/missing-checkout`

## Visão Geral

Retorna a lista de usuários que realizaram check-in mas não fizeram check-out — ou seja, ainda estão marcados como presentes no sistema embora possam ter saído sem registrar a saída. Útil para identificar inconsistências no controle de presença.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/missing-checkout`                  |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Array de objetos `UserRow` representando usuários com check-in sem checkout correspondente.

```json
[
  {
    "id": 55,
    "rfid": "B2C3D4E5",
    "nome": "Carlos Pereira",
    "chave": "CP03",
    "projeto": "PROJ-A",
    "projetos": ["PROJ-A"],
    "timezone_name": "Asia/Singapore",
    "timezone_label": "SGT (UTC+8)",
    "local": "main",
    "checkin": true,
    "time": "2025-05-24T08:15:00+08:00",
    "activity_date_label": "24/05/2025",
    "activity_time_label": "08:15:00",
    "activity_day_key": "2025-05-24",
    "assiduidade": "Normal",
    "forms_status": null
  }
]
```

### Campos da resposta

Mesma estrutura de `UserRow` descrita em `GET /api/admin/checkin`. O campo `checkin` será sempre `true` para registros retornados por este endpoint, e `activity_day_key` será de um dia anterior ao dia atual (indicando que o check-in ficou aberto sem checkout).

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia)         |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |

---

## Side effects

- Sincroniza o status de inatividade dos usuários antes de retornar (`sync_user_inactivity`).
- Se algum usuário for automaticamente descadastrado por inatividade, emite notificação SSE para o admin e para o Check Web.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/missing-checkout
```
