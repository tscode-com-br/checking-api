# `POST /api/web/check/accident/report`

## Visão Geral

Atualiza a zona e o status do usuário durante um acidente ativo. Pode ser chamado múltiplas vezes — cada chamada sobrescreve o relatório anterior do mesmo usuário. Se o usuário reportar `status="help"` pela primeira vez, o sistema dispara em background o envio de emails de alerta para os admins.

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `POST`                                              |
| **Path**          | `/api/web/check/accident/report`                    |
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
  "chave": "CEL2",
  "zone": "accident",
  "status": "help"
}
```

| Campo    | Tipo                       | Obrigatório | Descrição                                    |
|----------|----------------------------|-------------|----------------------------------------------|
| `chave`  | `string` (4 chars A-Z/0-9) | ✅           | Código do usuário                            |
| `zone`   | `"safety"` \| `"accident"` | ✅           | Zona onde o usuário se encontra              |
| `status` | `"ok"` \| `"help"`         | ✅           | Estado do usuário                            |

---

## Resposta (200)

Retorna o estado atual do acidente do ponto de vista do usuário.

```json
{
  "is_active": true,
  "accident_number_label": "0004",
  "project_name": "PROJETO ALFA",
  "location_name": "Bloco C",
  "current_user_report": {
    "zone": "accident",
    "status": "help",
    "reported_at": "2026-05-18T10:05:00+08:00"
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Relatório atualizado com sucesso                          |
| `401`  | Sessão ausente, expirada, ou `chave` não coincide         |
| `409`  | Nenhum acidente em curso (`"Nenhum acidente em curso."`)  |
| `422`  | Validação falhou: campos inválidos ou ausentes            |

### Exemplo de erro 409

```json
{ "detail": "Nenhum acidente em curso." }
```

---

## Side effects

- **Emails de alerta (background task):** Se `status="help"` e o usuário ainda não havia reportado `help` neste acidente, `queue_help_request_emails` é chamado em background:
  - Enfileira emails na tabela `email_delivery_logs` para todos os admins configurados
  - `deliver_pending_emails` é executado em seguida via background task
- `notify_admin_data_changed("accident_report")` — atualiza painel admin via SSE
- `notify_web_check_data_changed("accident_report")` — notifica todos os Check Web via SSE
- `log_event(action="accident_report", source="web", rfid=chave)` — grava evento na aba "Eventos"

---

## Exemplo cURL (ambiente local)

```bash
# Usuário reportando que está na zona de acidente e precisa de ajuda
curl -s -X POST \
  -H "Cookie: web_session_id=<sua_sessao_web>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "CEL2", "zone": "accident", "status": "help"}' \
  http://127.0.0.1:8000/api/web/check/accident/report \
  | python3 -m json.tool
```

```bash
# Usuário atualizando para zona de segurança
curl -s -X POST \
  -H "Cookie: web_session_id=<sua_sessao_web>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "CEL2", "zone": "safety", "status": "ok"}' \
  http://127.0.0.1:8000/api/web/check/accident/report \
  | python3 -m json.tool
```
