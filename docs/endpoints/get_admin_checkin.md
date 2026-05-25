# `GET /api/admin/checkin`

## Visão Geral

Retorna a lista de usuários que realizaram check-in e estão atualmente presentes no projeto. A lista é filtrada pelo escopo de projetos do administrador autenticado. Antes de retornar os dados, o sistema sincroniza o status de inatividade dos usuários.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/checkin`                           |
| **Autenticação** | Sessão administrativa (básica)                 |

---

## Autenticação

Requer cookie de sessão administrativa válido (`require_admin_session`). Este endpoint aceita tanto administradores com acesso completo quanto usuários com sessão administrativa básica (sem exigir perfil de admin completo). Caso a sessão esteja ausente ou expirada, retorna `401`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Array de objetos `UserRow` representando usuários com check-in ativo.

```json
[
  {
    "id": 42,
    "rfid": "A1B2C3D4",
    "nome": "João da Silva",
    "chave": "JS01",
    "projeto": "PROJ-A",
    "projetos": ["PROJ-A"],
    "timezone_name": "Asia/Singapore",
    "timezone_label": "SGT (UTC+8)",
    "local": "main",
    "checkin": true,
    "time": "2025-05-25T08:30:00+08:00",
    "activity_date_label": "25/05/2025",
    "activity_time_label": "08:30:00",
    "activity_day_key": "2025-05-25",
    "assiduidade": "Normal",
    "forms_status": null
  }
]
```

### Campos da resposta

| Campo                 | Tipo                   | Descrição                                                          |
|-----------------------|------------------------|--------------------------------------------------------------------|
| `id`                  | `integer`              | ID interno do usuário                                              |
| `rfid`                | `string \| null`       | Código RFID do usuário                                             |
| `nome`                | `string`               | Nome completo                                                      |
| `chave`               | `string`               | Chave de 4 caracteres                                              |
| `projeto`             | `string`               | Projeto ativo do usuário                                           |
| `projetos`            | `array[string]`        | Lista de todos os projetos do usuário                              |
| `timezone_name`       | `string`               | Nome do fuso horário (ex: `"Asia/Singapore"`)                      |
| `timezone_label`      | `string`               | Rótulo legível do fuso horário (ex: `"SGT (UTC+8)"`)               |
| `local`               | `string \| null`       | Local do último check-in (código de localização)                   |
| `checkin`             | `boolean`              | `true` para usuários com check-in ativo                            |
| `time`                | `datetime \| null`     | Timestamp do último check-in (UTC)                                 |
| `activity_date_label` | `string`               | Data formatada no fuso do projeto (ex: `"25/05/2025"`)             |
| `activity_time_label` | `string \| null`       | Hora formatada; `null` se o admin não tiver permissão para ver hora|
| `activity_day_key`    | `string`               | Data no formato `YYYY-MM-DD` para agrupamento/ordenação            |
| `assiduidade`         | `"Normal" \| "Retroativo"` | Indica se o evento foi registrado em tempo real ou retroativamente |
| `forms_status`        | `string \| null`       | Status do formulário do provedor (quando aplicável)                |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia)         |
| `401`  | Sessão administrativa inválida ou expirada           |

---

## Side effects

- Sincroniza o status de inatividade dos usuários antes de retornar (`sync_user_inactivity`).
- Se algum usuário for automaticamente descadastrado por inatividade (`apply_inactivity_descadastro`), emite notificação SSE para o admin e para o Check Web.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/checkin
```
