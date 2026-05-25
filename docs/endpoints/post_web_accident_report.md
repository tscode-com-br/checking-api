# `POST /api/web/check/accident/report`

## Visão Geral

Atualiza ou cria o relatório de situação do usuário autenticado para o acidente em curso. O usuário informa em qual zona se encontra e qual é seu status de segurança. Se o usuário reportar `status="help"` pela primeira vez, um e-mail de alerta é enviado em background para os responsáveis.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/check/accident/report`               |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no body deve coincidir com o valor no cookie. Em caso de falha retorna `401`.

---

## Request Body

```json
{
  "chave": "AB12",
  "zone": "safety",
  "status": "ok"
}
```

### Campos do request body

| Campo    | Tipo   | Obrigatório | Restrições                       | Descrição                                                   |
|----------|--------|-------------|----------------------------------|-------------------------------------------------------------|
| `chave`  | string | Sim         | 4 caracteres alfanuméricos       | Chave do usuário                                            |
| `zone`   | string | Sim         | `"safety"` ou `"accident"`       | Zona onde o usuário está                                    |
| `status` | string | Sim         | `"ok"` ou `"help"`               | Status de segurança do usuário                              |

### Valores de zona

| Valor       | Significado                                               |
|-------------|-----------------------------------------------------------|
| `"safety"`  | Usuário está em área segura, fora da zona de risco        |
| `"accident"`| Usuário está dentro da zona do acidente                   |

> **Nota:** a zona `"waiting"` (estado inicial antes de qualquer reporte) não pode ser enviada neste endpoint — ela é atribuída automaticamente pelo sistema ao registrar o usuário no acidente.

### Valores de status

| Valor    | Significado                                                           |
|----------|-----------------------------------------------------------------------|
| `"ok"`   | Usuário está bem, não precisa de socorro                              |
| `"help"` | Usuário precisa de socorro — dispara envio de e-mail de alerta em background |

---

## Resposta

A resposta é idêntica a `GET /api/web/check/accident/state` após o reporte.

```json
{
  "is_active": true,
  "accident_id": 5,
  "accident_number_label": "ACC-0005",
  "project_id": 3,
  "project_name": "Projeto Norte",
  "location_name": "Área de Extração B",
  "description": "Acidente com equipamento pesado.",
  "awareness_status": "acknowledged",
  "current_user_report": {
    "zone": "safety",
    "status": "ok",
    "reported_at": "2026-05-25T14:35:00+08:00"
  },
  "active_accidents": [...]
}
```

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Reporte registrado ou atualizado com sucesso              |
| `401`  | Sessão inválida ou expirada, ou chave não confere         |
| `409`  | Nenhum acidente em curso (`is_active=false`)              |
| `422`  | Campos inválidos (zona ou status fora dos valores aceitos) |

---

## Side effects

- Cria ou atualiza o registro em `accident_user_reports` para o par `(accident_id, user_id)`.
- Se `status="help"` e é a primeira vez que o usuário reporta `help` neste acidente: enfileira e-mail de alerta via `queue_help_request_emails` (executado em background após a resposta HTTP).
- Grava evento em `check_events` com `action="accident_report"`.
- Emite notificações SSE admin e web-check.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "zone": "safety", "status": "ok"}' \
  "http://127.0.0.1:8000/api/web/check/accident/report"
```

### Exemplo reportando necessidade de socorro

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "zone": "accident", "status": "help"}' \
  "http://127.0.0.1:8000/api/web/check/accident/report"
```
