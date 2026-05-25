# `POST /api/web/check/accident/open`

## Visão Geral

Abre um novo acidente a partir do Check Web. Qualquer usuário autenticado pode acionar o Modo Acidente. Apenas um acidente pode estar ativo por projeto ao mesmo tempo (índice único parcial na tabela `accidents`). O usuário que abre o acidente já informa imediatamente sua zona e status de segurança.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/check/accident/open`                 |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no body deve coincidir com o valor no cookie. Em caso de falha retorna `401`.

---

## Request Body

### Com local cadastrado (via ID)

```json
{
  "chave": "AB12",
  "project_id": 3,
  "location_id": 12,
  "custom_location_name": null,
  "zone": "safety",
  "status": "ok",
  "description": "Tombamento de veículo na pista C."
}
```

### Com local personalizado (texto livre)

```json
{
  "chave": "AB12",
  "project_id": 3,
  "location_id": null,
  "custom_location_name": "Galpão Sul, portão 3",
  "zone": "accident",
  "status": "help",
  "description": ""
}
```

### Campos do request body

| Campo                  | Tipo            | Obrigatório | Restrições                                             | Descrição                                                             |
|------------------------|-----------------|-------------|--------------------------------------------------------|-----------------------------------------------------------------------|
| `chave`                | string          | Sim         | 4 caracteres alfanuméricos (A-Z, 0-9), maiúsculos      | Chave do usuário                                                      |
| `project_id`           | int             | Sim         |                                                        | ID do projeto onde ocorreu o acidente                                 |
| `location_id`          | int \| null     | Condicional | Exclusivo com `custom_location_name`                   | ID de um local cadastrado (obtido via wizard)                         |
| `custom_location_name` | string \| null  | Condicional | Exclusivo com `location_id`                            | Nome livre do local (quando não há local cadastrado correspondente)   |
| `zone`                 | string          | Sim         | `"safety"` ou `"accident"`                             | Zona do usuário no momento da abertura                                |
| `status`               | string          | Sim         | `"ok"` ou `"help"`                                     | Status de segurança do usuário                                        |
| `description`          | string          | Não         | Máximo 500 caracteres. Padrão: `""`                    | Descrição textual do acidente                                         |

> **Regra de local:** exatamente um de `location_id` ou `custom_location_name` deve ser fornecido — não ambos, não nenhum.

### Valores de zona

| Valor       | Significado                                               |
|-------------|-----------------------------------------------------------|
| `"safety"`  | Usuário está em área segura, fora da zona de risco        |
| `"accident"`| Usuário está dentro da zona do acidente                   |

### Valores de status

| Valor    | Significado                                             |
|----------|---------------------------------------------------------|
| `"ok"`   | Usuário está bem                                        |
| `"help"` | Usuário precisa de socorro (dispara envio de e-mail de alerta) |

---

## Resposta

A resposta é idêntica a `GET /api/web/check/accident/state` após a abertura.

```json
{
  "is_active": true,
  "accident_id": 5,
  "accident_number_label": "ACC-0005",
  "project_id": 3,
  "project_name": "Projeto Norte",
  "location_name": "Galpão Sul, portão 3",
  "description": "",
  "awareness_status": "waiting",
  "current_user_report": {
    "zone": "accident",
    "status": "help",
    "reported_at": "2026-05-25T14:30:00+08:00"
  },
  "active_accidents": [...]
}
```

---

## Códigos de status HTTP

| Código | Significado                                                              |
|--------|--------------------------------------------------------------------------|
| `200`  | Acidente aberto com sucesso                                              |
| `401`  | Sessão inválida ou expirada, ou chave não confere                        |
| `409`  | Já existe um acidente ativo no projeto — apenas um acidente por vez      |
| `422`  | Campos inválidos (ambos `location_id` e `custom_location_name` fornecidos, ou nenhum; campo fora dos valores aceitos etc.) |

---

## Side effects

- Cria registro na tabela `accidents` com `origin="web"`.
- Cria registro inicial em `accident_user_reports` para o usuário que abriu.
- Grava evento em `check_events` com `action="accident_open"`.
- Emite notificações SSE admin e web-check via `notify_admin_data_changed` e `notify_web_check_data_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{
    "chave": "AB12",
    "project_id": 3,
    "location_id": null,
    "custom_location_name": "Galpão Sul, portão 3",
    "zone": "safety",
    "status": "ok",
    "description": "Tombamento de veículo na pista C."
  }' \
  "http://127.0.0.1:8000/api/web/check/accident/open"
```
