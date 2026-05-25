# `PUT /api/admin/projects/{project_id}`

## Visão Geral

Atualiza os dados de um projeto existente. Campos não enviados no body são ignorados (patch semântico via `model_fields_set`). Se o nome for alterado, o sistema propaga a renomeação em cascata para usuários, localizações e escopos de administradores vinculados.

| Atributo         | Valor                                            |
|------------------|--------------------------------------------------|
| **Método**       | `PUT`                                            |
| **Path**         | `/api/admin/projects/{project_id}`               |
| **Autenticação** | Sessão administrativa com identidade de admin    |
| **Content-Type** | `application/json`                               |

---

## Autenticação

Requer cookie de sessão administrativa com perfil de admin e resolução da identidade de admin (`require_admin_identity`). Internamente, além da validação `require_full_admin_session`, este endpoint garante a existência do par `User`/`AdminUser` para operações de auditoria em colunas FK→`admin_users.id`. Retorna `401` se sessão inválida, `403` se sem permissão.

---

## Parâmetros

### Path Parameters

| Parâmetro    | Tipo      | Descrição              |
|--------------|-----------|------------------------|
| `project_id` | `integer` | ID interno do projeto  |

### Request Body

Todos os campos são opcionais. Somente os campos presentes no body serão atualizados.

```json
{
  "name": "PROJ-A-RENAMED",
  "country_code": "SG",
  "country_name": "Singapore",
  "timezone_name": "Asia/Singapore",
  "address": "1 Marina Boulevard",
  "zip_code": "018989",
  "forms_enabled": true,
  "transport_enabled": true,
  "emergency_phone": "+6512345678",
  "twilio_account_sid": "ACxxxxxxxxxxxxxxx",
  "twilio_auth_token": "xxxxxxxxxxxxxxxx",
  "twilio_phone_number": "+6599887766",
  "mobile_admin": "+6599001122",
  "email_local_emergency": "emergency@empresa.com",
  "emergency_call_message": "Acidente reportado. Por favor, responda imediatamente.",
  "inactivity_days_threshold": 60,
  "mixed_zone_interval_minutes": 30,
  "minimum_checkout_distance_meters": 1500
}
```

### Campos do body

| Campo                               | Tipo             | Padrão | Descrição                                                                      |
|-------------------------------------|------------------|--------|--------------------------------------------------------------------------------|
| `name`                              | `string \| null` | omitir | Novo nome do projeto (2–120 chars). Propaga renomeação em cascata.             |
| `country_code`                      | `string \| null` | omitir | Código ISO alpha-2                                                             |
| `country_name`                      | `string \| null` | omitir | Nome do país                                                                   |
| `timezone_name`                     | `string \| null` | omitir | Nome do fuso horário IANA                                                      |
| `address`                           | `string`         | `""`   | Endereço (até 255 chars)                                                       |
| `zip_code`                          | `string`         | `""`   | CEP (até 32 chars)                                                             |
| `forms_enabled`                     | `boolean \| null`| omitir | Ativa/desativa módulo de formulários                                           |
| `transport_enabled`                 | `boolean \| null`| omitir | Ativa/desativa módulo de transporte                                            |
| `emergency_phone`                   | `string \| null` | omitir | Telefone de emergência (até 32 chars)                                          |
| `twilio_account_sid`                | `string \| null` | omitir | SID da conta Twilio (até 64 chars)                                             |
| `twilio_auth_token`                 | `string \| null` | omitir | Auth token Twilio (até 64 chars)                                               |
| `twilio_phone_number`               | `string \| null` | omitir | Número Twilio (até 32 chars)                                                   |
| `mobile_admin`                      | `string \| null` | omitir | Número do admin mobile (até 32 chars)                                          |
| `email_local_emergency`             | `string \| null` | omitir | E-mail de emergência local                                                     |
| `emergency_call_message`            | `string \| null` | omitir | Mensagem TTS para chamada de emergência                                        |
| `inactivity_days_threshold`         | `integer \| null`| omitir | Dias para inatividade (1–3650)                                                 |
| `mixed_zone_interval_minutes`       | `integer \| null`| omitir | Intervalo zona mista em minutos (1–1440)                                       |
| `minimum_checkout_distance_meters`  | `integer \| null`| omitir | Distância checkout automático em metros (1–999999)                             |

---

## Resposta

Objeto `ProjectRow` atualizado (mesma estrutura de `GET /api/admin/projects`).

---

## Códigos de status HTTP

| Código | Significado                                            |
|--------|--------------------------------------------------------|
| `200`  | Projeto atualizado com sucesso                         |
| `401`  | Sessão administrativa inválida ou expirada             |
| `403`  | Usuário não possui permissão de administrador          |
| `404`  | Projeto não encontrado                                 |
| `409`  | Já existe outro projeto com o novo nome               |
| `422`  | Erro de validação do payload                           |

---

## Side effects

- Atualiza o registro em `projects`.
- **Se o nome mudou:** atualiza `users.projeto`, `managed_locations.projects_json` e limpa `admin_monitored_projects_json` de admins com escopo explícito para o projeto renomeado.
- Se `forms_enabled` mudou de `true` para `false`: grava evento de auditoria `proj_forms_off`.
- Se `transport_enabled` mudou de `true` para `false`: grava evento de auditoria `proj_trans_off` e emite SSE para o Check Web.
- Emite notificação SSE para o painel admin e grava evento em `check_events`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X PUT \
  -H "Cookie: admin_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "minimum_checkout_distance_meters": 1500,
    "mixed_zone_interval_minutes": 45
  }' \
  http://127.0.0.1:8000/api/admin/projects/1
```
