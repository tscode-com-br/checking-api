# `POST /api/admin/projects`

## Visão Geral

Cria um novo projeto no sistema. O administrador que cria o projeto é automaticamente vinculado a ele como membro. O nome do projeto é normalizado para letras maiúsculas.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/admin/projects`                          |
| **Autenticação** | Sessão administrativa com perfil de admin      |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Request Body

```json
{
  "name": "PROJ-C",
  "country_code": "MY",
  "country_name": "Malaysia",
  "timezone_name": "Asia/Kuala_Lumpur",
  "address": "Jalan Ampang, 50450 Kuala Lumpur",
  "zip_code": "50450",
  "forms_enabled": true,
  "transport_enabled": false,
  "emergency_phone": "+60312345678",
  "inactivity_days_threshold": 60,
  "mixed_zone_interval_minutes": 30,
  "minimum_checkout_distance_meters": 2000
}
```

### Campos do body

| Campo                               | Tipo             | Obrigatório | Padrão  | Descrição                                                                              |
|-------------------------------------|------------------|-------------|---------|----------------------------------------------------------------------------------------|
| `name`                              | `string`         | Sim         | —       | Nome do projeto (2–120 caracteres, normalizado para uppercase)                        |
| `country_code`                      | `string \| null` | Não         | `null`  | Código ISO alpha-2 do país (ex: `"MY"`). Inferido de `country_name` se omitido.       |
| `country_name`                      | `string \| null` | Não         | `null`  | Nome do país (ex: `"Malaysia"`). Inferido de `country_code` se omitido.               |
| `timezone_name`                     | `string \| null` | Não         | `null`  | Nome do fuso horário IANA (ex: `"Asia/Kuala_Lumpur"`). Inferido do país se omitido.   |
| `address`                           | `string`         | Não         | `""`    | Endereço (até 255 caracteres)                                                          |
| `zip_code`                          | `string`         | Não         | `""`    | CEP / código postal (até 32 caracteres)                                                |
| `forms_enabled`                     | `boolean`        | Não         | `true`  | Ativa o módulo de formulários                                                          |
| `transport_enabled`                 | `boolean`        | Não         | `true`  | Ativa o módulo de transporte                                                           |
| `emergency_phone`                   | `string`         | Não         | `""`    | Telefone de emergência (até 32 caracteres)                                             |
| `inactivity_days_threshold`         | `integer`        | Não         | `60`    | Dias para inatividade (1–3650)                                                         |
| `mixed_zone_interval_minutes`       | `integer`        | Não         | `30`    | Intervalo da zona mista em minutos (1–1440)                                            |
| `minimum_checkout_distance_meters`  | `integer`        | Não         | `2000`  | Distância mínima para checkout automático em metros (1–999999)                        |

**Inferência de país/fuso:** o sistema infere automaticamente `country_code`, `country_name` e `timezone_name` a partir de qualquer um dos três campos fornecidos. Se nenhum for informado, o projeto é criado sem configuração de país/fuso.

---

## Resposta

Objeto `ProjectRow` com os dados do projeto criado (mesma estrutura de `GET /api/admin/projects`).

```json
{
  "id": 3,
  "name": "PROJ-C",
  "country_code": "MY",
  "country_name": "Malaysia",
  "timezone_name": "Asia/Kuala_Lumpur",
  "timezone_label": "MYT (UTC+8)",
  "address": "Jalan Ampang, 50450 Kuala Lumpur",
  "zip_code": "50450",
  "forms_enabled": true,
  "transport_enabled": false,
  "emergency_phone": "+60312345678",
  "twilio_account_sid": "",
  "twilio_auth_token": "",
  "twilio_phone_number": "",
  "mobile_admin": "",
  "email_local_emergency": "",
  "emergency_call_message": "",
  "inactivity_days_threshold": 60,
  "mixed_zone_interval_minutes": 30,
  "minimum_checkout_distance_meters": 2000
}
```

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Projeto criado com sucesso                           |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |
| `409`  | Já existe um projeto com esse nome                   |
| `422`  | Erro de validação do payload                         |

---

## Side effects

- Cria registro em `projects`.
- Vincula o administrador criador ao projeto como membro.
- Emite notificação SSE para o painel admin e grava evento em `check_events`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: admin_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PROJ-C",
    "country_code": "MY",
    "timezone_name": "Asia/Kuala_Lumpur",
    "forms_enabled": true,
    "transport_enabled": false
  }' \
  http://127.0.0.1:8000/api/admin/projects
```
