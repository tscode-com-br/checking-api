# `GET /api/web/projects`

## Visão Geral

Retorna a lista de todos os projetos cadastrados no sistema. Endpoint público — não requer autenticação. Usado pelo Check Web para popular o seletor de projetos nas telas de cadastro.

| Atributo         | Valor                |
|------------------|----------------------|
| **Método**       | `GET`                |
| **Path**         | `/api/web/projects`  |
| **Autenticação** | Nenhuma              |
| **Content-Type** | N/A                  |

---

## Autenticação

Nenhuma autenticação é necessária. Este endpoint é público.

---

## Parâmetros

Nenhum parâmetro é aceito.

---

## Resposta

### HTTP 200 — Lista de projetos

```json
[
  {
    "id": 1,
    "name": "Projeto Alpha",
    "country_code": "MY",
    "country_name": "Malaysia",
    "timezone_name": "Asia/Kuala_Lumpur",
    "timezone_label": "Malaysia (UTC+8)",
    "address": "Jalan Ampang, Kuala Lumpur",
    "zip_code": "50450",
    "forms_enabled": true,
    "transport_enabled": true,
    "emergency_phone": "+60112345678"
  },
  {
    "id": 2,
    "name": "Projeto Beta",
    "country_code": "BR",
    "country_name": "Brazil",
    "timezone_name": "America/Sao_Paulo",
    "timezone_label": "Brazil (UTC-3)",
    "address": "",
    "zip_code": "",
    "forms_enabled": true,
    "transport_enabled": false,
    "emergency_phone": ""
  }
]
```

### Campos de cada item

| Campo                | Tipo    | Descrição                                                                     |
|----------------------|---------|-------------------------------------------------------------------------------|
| `id`                 | integer | Identificador único do projeto                                                |
| `name`               | string  | Nome do projeto                                                               |
| `country_code`       | string  | Código do país (ISO 3166-1 alpha-2). Ex.: `"BR"`, `"MY"`                     |
| `country_name`       | string  | Nome do país por extenso. Ex.: `"Brazil"`, `"Malaysia"`                      |
| `timezone_name`      | string  | Nome da timezone IANA. Ex.: `"America/Sao_Paulo"`, `"Asia/Kuala_Lumpur"`     |
| `timezone_label`     | string  | Label formatada da timezone para exibição. Ex.: `"Malaysia (UTC+8)"`          |
| `address`            | string  | Endereço do projeto (string vazia se não cadastrado)                          |
| `zip_code`           | string  | CEP/código postal (string vazia se não cadastrado)                            |
| `forms_enabled`      | boolean | Indica se o módulo de check-in/check-out está habilitado para o projeto       |
| `transport_enabled`  | boolean | Indica se o módulo de transporte está habilitado para o projeto               |
| `emergency_phone`    | string  | Número de telefone de emergência do projeto (string vazia se não cadastrado)  |

> **Nota:** Os campos `twilio_account_sid`, `twilio_auth_token`, `twilio_phone_number` e `mobile_admin` existem no schema mas são retornados como strings vazias neste endpoint para usuários web.

---

## Códigos de status HTTP

| Código | Significado                            |
|--------|----------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia `[]`) |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s "http://127.0.0.1:8000/api/web/projects"
```
