# `POST /api/web/check`

## Visão Geral

Registra um evento de check-in ou check-out para o usuário autenticado. É o endpoint principal do Check Web para submissão de ponto. Suporta eventos em tempo real (informe `normal`) e retroativos (informe `retroativo`). Implementa idempotência via `client_event_id`.

| Atributo         | Valor              |
|------------------|--------------------|
| **Método**       | `POST`             |
| **Path**         | `/api/web/check`   |
| **Autenticação** | Cookie de sessão obrigatório (chave na sessão deve corresponder ao campo `chave` no body) |
| **Content-Type** | `application/json` |

---

## Autenticação

Requer sessão ativa via cookie **e** que a chave armazenada na sessão seja idêntica ao campo `chave` no body da requisição. Se a sessão estiver ausente, inválida ou a chave não corresponder, retorna HTTP 401.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "projeto": "Projeto Alpha",
  "action": "checkin",
  "local": "Escritório Principal",
  "informe": "normal",
  "event_time": "2024-03-15T08:30:00",
  "client_event_id": "web-AB12-1710492600000"
}
```

| Campo             | Tipo   | Obrigatório | Descrição                                                                      |
|-------------------|--------|-------------|--------------------------------------------------------------------------------|
| `chave`           | string | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12`        |
| `projeto`         | string | Sim         | Nome do projeto — entre 2 e 120 caracteres                                     |
| `action`          | string | Sim         | Tipo do evento: `"checkin"` ou `"checkout"`                                    |
| `local`           | string\|null | Não   | Nome do local onde o evento ocorreu. `null` se localização não identificada. Não pode ser `"Localização não Cadastrada"` |
| `informe`         | string | Sim         | Tipo do informe: `"normal"` (em tempo real) ou `"retroativo"` (lançamento posterior) |
| `event_time`      | datetime | Sim       | Timestamp ISO 8601 do evento. Ex.: `"2024-03-15T08:30:00"`                    |
| `client_event_id` | string | Sim         | Identificador único do evento gerado pelo cliente — entre 8 e 80 caracteres. Usado para idempotência (duplicatas são detectadas e ignoradas) |

**Regras de validação:**
- `chave`: exatamente 4 caracteres alfanuméricos após `.strip().upper()`
- `projeto`: deve corresponder a um projeto cadastrado do usuário
- `action`: apenas `"checkin"` ou `"checkout"` são aceitos
- `informe`: apenas `"normal"` ou `"retroativo"` são aceitos (case-insensitive, normalizado para minúsculas)
- `local`: se informado como `"Localização não Cadastrada"`, retorna HTTP 422 (local não operacional)
- `client_event_id`: mínimo 8, máximo 80 caracteres

---

## Resposta

### HTTP 200 — Evento registrado com sucesso

```json
{
  "ok": true,
  "duplicate": false,
  "queued_forms": true,
  "worker_healthy": true,
  "message": "Check-in registrado.",
  "state": {
    "found": true,
    "chave": "AB12",
    "nome": "Joao da Silva",
    "projeto": "Projeto Alpha",
    "current_action": "checkout",
    "current_event_time": "2024-03-15T08:30:00",
    "current_local": "Escritório Principal",
    "last_checkin_at": "2024-03-15T08:30:00",
    "last_checkout_at": "2024-03-14T17:45:00"
  }
}
```

### HTTP 200 — Evento duplicado (já registrado anteriormente)

```json
{
  "ok": true,
  "duplicate": true,
  "queued_forms": true,
  "worker_healthy": true,
  "message": "Evento ja registrado anteriormente.",
  "state": { ... }
}
```

### Campos da resposta

| Campo           | Tipo    | Descrição                                                                              |
|-----------------|---------|----------------------------------------------------------------------------------------|
| `ok`            | boolean | Sempre `true` em caso de sucesso (incluindo duplicatas)                                |
| `duplicate`     | boolean | `true` se o `client_event_id` já foi registrado anteriormente (idempotência)          |
| `queued_forms`  | boolean | `true` se o worker de processamento de eventos está operacional                        |
| `worker_healthy`| boolean | `true` se o worker interno está saudável                                               |
| `message`       | string  | Mensagem descritiva do resultado                                                       |
| `state`         | object  | Estado atualizado do usuário após o evento (ver campos abaixo)                         |

### Campos do objeto `state`

| Campo                  | Tipo            | Descrição                                                    |
|------------------------|-----------------|--------------------------------------------------------------|
| `found`                | boolean         | Sempre `true` para usuários autenticados                     |
| `chave`                | string          | Chave do usuário                                             |
| `nome`                 | string\|null    | Nome do usuário                                              |
| `projeto`              | string\|null    | Projeto ativo do usuário                                     |
| `current_action`       | string\|null    | Próxima ação esperada: `"checkin"` ou `"checkout"`           |
| `current_event_time`   | datetime\|null  | Timestamp do evento atual                                    |
| `current_local`        | string\|null    | Local do evento atual                                        |
| `last_checkin_at`      | datetime\|null  | Timestamp do último check-in                                 |
| `last_checkout_at`     | datetime\|null  | Timestamp do último check-out                                |

---

## Códigos de status HTTP

| Código | Significado                                                                       |
|--------|-----------------------------------------------------------------------------------|
| `200`  | Evento registrado (ou detectado como duplicata)                                   |
| `401`  | Sessão ausente, inválida, expirada ou chave não corresponde à sessão              |
| `409`  | Projeto informado não pertence aos projetos cadastrados do usuário                |
| `422`  | Campos inválidos (chave, action, informe, local não-operacional, etc.)            |

### Exemplos de erros

```json
// HTTP 401 — chave diferente da sessão
{"detail": "A chave informada nao corresponde a sessao atual"}

// HTTP 409 — projeto inválido para o usuário
{"detail": "O projeto informado nao pertence aos projetos cadastrados do usuario."}

// HTTP 422 — local não-operacional
{"detail": "O estado 'Localização não Cadastrada' nao e um local operacional valido para submit pela Web."}
```

---

## Side effects

- Registra um evento em `check_events` via `log_event()`.
- Atualiza os campos `checkin`, `time`, `local` e `projeto` do usuário na tabela `users`.
- Dispara notificações SSE para o painel admin (`notify_admin_data_changed`) e para o Check Web (`notify_web_check_data_changed`).
- Pode atualizar o estado de membership no Modo Acidente se houver acidente ativo.

---

## Exemplo cURL (ambiente local)

```bash
# Check-in em tempo real
curl -s -X POST "http://127.0.0.1:8000/api/web/check" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "chave": "AB12",
    "projeto": "Projeto Alpha",
    "action": "checkin",
    "local": "Escritório Principal",
    "informe": "normal",
    "event_time": "2024-03-15T08:30:00",
    "client_event_id": "web-AB12-1710492600000"
  }'

# Check-out retroativo (sem local definido)
curl -s -X POST "http://127.0.0.1:8000/api/web/check" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "chave": "AB12",
    "projeto": "Projeto Alpha",
    "action": "checkout",
    "local": null,
    "informe": "retroativo",
    "event_time": "2024-03-14T17:30:00",
    "client_event_id": "web-AB12-retro-1710435000000"
  }'
```
