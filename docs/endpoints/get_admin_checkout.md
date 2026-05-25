# `GET /api/admin/checkout`

## Visão Geral

Retorna a lista de usuários que realizaram check-out e não estão presentes no momento. A lista é filtrada pelo escopo de projetos do administrador autenticado. Antes de retornar os dados, o sistema sincroniza o status de inatividade dos usuários.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/checkout`                          |
| **Autenticação** | Sessão administrativa (básica)                 |

---

## Autenticação

Requer cookie de sessão administrativa válido (`require_admin_session`). Este endpoint aceita tanto administradores com acesso completo quanto usuários com sessão administrativa básica. Caso a sessão esteja ausente ou expirada, retorna `401`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Array de objetos `UserRow` representando usuários com checkout (fora do projeto).

```json
[
  {
    "id": 17,
    "rfid": "F1E2D3C4",
    "nome": "Maria Souza",
    "chave": "MS02",
    "projeto": "PROJ-B",
    "projetos": ["PROJ-B"],
    "timezone_name": "Asia/Kuala_Lumpur",
    "timezone_label": "MYT (UTC+8)",
    "local": null,
    "checkin": false,
    "time": "2025-05-24T17:00:00+08:00",
    "activity_date_label": "24/05/2025",
    "activity_time_label": "17:00:00",
    "activity_day_key": "2025-05-24",
    "assiduidade": "Normal",
    "forms_status": null
  }
]
```

### Campos da resposta

| Campo                 | Tipo                   | Descrição                                                           |
|-----------------------|------------------------|---------------------------------------------------------------------|
| `id`                  | `integer`              | ID interno do usuário                                               |
| `rfid`                | `string \| null`       | Código RFID do usuário                                              |
| `nome`                | `string`               | Nome completo                                                       |
| `chave`               | `string`               | Chave de 4 caracteres                                               |
| `projeto`             | `string`               | Projeto ativo do usuário                                            |
| `projetos`            | `array[string]`        | Lista de todos os projetos do usuário                               |
| `timezone_name`       | `string`               | Nome do fuso horário                                                |
| `timezone_label`      | `string`               | Rótulo legível do fuso horário                                      |
| `local`               | `string \| null`       | Local do último check-out (ou `null`)                               |
| `checkin`             | `boolean`              | `false` para usuários com checkout                                  |
| `time`                | `datetime \| null`     | Timestamp do último check-out (UTC)                                 |
| `activity_date_label` | `string`               | Data formatada no fuso do projeto                                   |
| `activity_time_label` | `string \| null`       | Hora formatada; `null` se o admin não tiver permissão para ver hora |
| `activity_day_key`    | `string`               | Data no formato `YYYY-MM-DD`                                        |
| `assiduidade`         | `"Normal" \| "Retroativo"` | Tipo do registro                                                |
| `forms_status`        | `string \| null`       | Status do formulário do provedor (quando aplicável)                 |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia)         |
| `401`  | Sessão administrativa inválida ou expirada           |

---

## Side effects

- Sincroniza o status de inatividade dos usuários antes de retornar (`sync_user_inactivity`).
- Se algum usuário for automaticamente descadastrado por inatividade, emite notificação SSE para o admin e para o Check Web.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/checkout
```
