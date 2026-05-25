# `GET /api/admin/projects`

## Visão Geral

Retorna a lista completa de projetos cadastrados no sistema, incluindo configurações de fuso horário, país, transporte, emergência e limiares operacionais.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/projects`                          |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Array de objetos `ProjectRow` com todos os projetos cadastrados (sem filtro por escopo do admin).

```json
[
  {
    "id": 1,
    "name": "PROJ-A",
    "country_code": "SG",
    "country_name": "Singapore",
    "timezone_name": "Asia/Singapore",
    "timezone_label": "SGT (UTC+8)",
    "address": "1 Marina Boulevard, Singapore 018989",
    "zip_code": "018989",
    "forms_enabled": true,
    "transport_enabled": true,
    "emergency_phone": "+6512345678",
    "twilio_account_sid": "",
    "twilio_auth_token": "",
    "twilio_phone_number": "",
    "mobile_admin": "",
    "email_local_emergency": "emergency@empresa.com",
    "emergency_call_message": "Atencao: acidente reportado no projeto PROJ-A",
    "inactivity_days_threshold": 60,
    "mixed_zone_interval_minutes": 30,
    "minimum_checkout_distance_meters": 2000
  }
]
```

### Campos da resposta

| Campo                               | Tipo      | Descrição                                                                                   |
|-------------------------------------|-----------|---------------------------------------------------------------------------------------------|
| `id`                                | `integer` | ID interno do projeto                                                                       |
| `name`                              | `string`  | Nome do projeto (uppercase, normalizado)                                                    |
| `country_code`                      | `string`  | Código ISO 3166-1 alpha-2 do país (ex: `"SG"`)                                             |
| `country_name`                      | `string`  | Nome do país (ex: `"Singapore"`)                                                            |
| `timezone_name`                     | `string`  | Nome do fuso horário IANA (ex: `"Asia/Singapore"`)                                         |
| `timezone_label`                    | `string`  | Rótulo legível do fuso horário (ex: `"SGT (UTC+8)"`)                                       |
| `address`                           | `string`  | Endereço completo do projeto                                                                |
| `zip_code`                          | `string`  | CEP / código postal                                                                         |
| `forms_enabled`                     | `boolean` | Se o módulo de formulários (Forms/provider) está ativo                                     |
| `transport_enabled`                 | `boolean` | Se o módulo de transporte está ativo                                                        |
| `emergency_phone`                   | `string`  | Telefone de emergência do projeto                                                           |
| `twilio_account_sid`                | `string`  | SID da conta Twilio para chamadas de emergência (vazio se não configurado)                  |
| `twilio_auth_token`                 | `string`  | Auth token Twilio (vazio se não configurado)                                                |
| `twilio_phone_number`               | `string`  | Número Twilio para chamadas de voz de emergência                                           |
| `mobile_admin`                      | `string`  | Número do admin mobile para receber chamadas Twilio                                         |
| `email_local_emergency`             | `string`  | E-mail do responsável local de emergência                                                   |
| `emergency_call_message`            | `string`  | Mensagem lida na chamada de emergência Twilio (TTS)                                         |
| `inactivity_days_threshold`         | `integer` | Dias sem atividade para considerar usuário inativo (padrão: 60)                            |
| `mixed_zone_interval_minutes`       | `integer` | Intervalo em minutos para zona mista no Modo Acidente (padrão: 30, máx: 1440)             |
| `minimum_checkout_distance_meters`  | `integer` | Distância mínima em metros para o check-out automático por GPS (padrão: 2000, máx: 999999) |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso                          |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |

---

## Side effects

Nenhum. Este endpoint é somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/projects
```
