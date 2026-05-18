# `POST /api/web/check/accident/open`

## Visão Geral

Abre um novo acidente a partir do Check Web (origem `web`). O usuário autenticado seleciona projeto e local, informa sua zona e status iniciais, e o sistema registra o acidente. Apenas um acidente pode estar ativo por vez.

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `POST`                                              |
| **Path**          | `/api/web/check/accident/open`                      |
| **Autenticação**  | Sessão web (cookie `web_session_id`) + campo `chave` no body |
| **Content-Type**  | `application/json`                                  |
| **Formato**       | `application/json`                                  |

---

## Autenticação

Requer sessão web válida. O campo `chave` no body deve corresponder ao usuário da sessão ativa.

---

## Request Body

```json
{
  "chave": "APF1",
  "project_id": 5,
  "location_id": null,
  "custom_location_name": "Entrada do Galpão",
  "zone": "safety",
  "status": "ok"
}
```

| Campo                  | Tipo                             | Obrigatório | Descrição                                                         |
|------------------------|----------------------------------|-------------|-------------------------------------------------------------------|
| `chave`                | `string` (4 chars A-Z/0-9)       | ✅           | Código do usuário (normalizado para maiúsculas)                   |
| `project_id`           | `integer`                        | ✅           | ID do projeto onde ocorreu o acidente                             |
| `location_id`          | `integer` \| `null`              | ✅*          | ID de `ManagedLocation` cadastrado                                |
| `custom_location_name` | `string` \| `null`               | ✅*          | Nome livre de local (quando não é registrado)                     |
| `zone`                 | `"safety"` \| `"accident"`       | ✅           | Zona inicial do usuário que está abrindo o acidente               |
| `status`               | `"ok"` \| `"help"`               | ✅           | Status inicial do usuário                                         |

> **Regra XOR:** Exatamente um de `location_id` ou `custom_location_name` deve ser fornecido.

---

## Resposta (200)

Retorna o estado do acidente do ponto de vista do usuário (idêntico a `GET /check/accident/state`).

```json
{
  "is_active": true,
  "accident_number_label": "0004",
  "project_name": "PROJETO ALFA",
  "location_name": "Entrada do Galpão",
  "current_user_report": {
    "zone": "safety",
    "status": "ok",
    "reported_at": "2026-05-18T10:00:00+08:00"
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                        |
|--------|------------------------------------------------------------------------------------|
| `200`  | Acidente aberto com sucesso                                                        |
| `401`  | Sessão ausente, expirada, ou `chave` não coincide com a sessão                     |
| `409`  | Outro usuário já reportou um acidente (`"Outro usuario ja reportou um acidente."`) |
| `422`  | Validação falhou: `chave` inválida, XOR de location violado, ou campos ausentes    |

### Exemplo de erro 409

```json
{ "detail": "Outro usuario ja reportou um acidente." }
```

---

## Side effects

- `notify_admin_data_changed("accident_open")` — atualiza painel admin via SSE (`checking_admin_updates`)
- `notify_web_check_data_changed("accident_open")` — notifica todos os Check Web via SSE (`checking_web_check_updates`)
- `log_event(action="accident_open", source="web", rfid=chave)` — grava evento na aba "Eventos" do admin

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: web_session_id=<sua_sessao_web>" \
  -H "Content-Type: application/json" \
  -d '{
    "chave": "APF1",
    "project_id": 5,
    "location_id": null,
    "custom_location_name": "Bloco Leste",
    "zone": "safety",
    "status": "ok"
  }' \
  http://127.0.0.1:8000/api/web/check/accident/open \
  | python3 -m json.tool
```
