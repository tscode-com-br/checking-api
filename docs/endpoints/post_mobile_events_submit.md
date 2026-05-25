# `POST /api/mobile/events/submit`

## Visão Geral

Registra um evento de check-in ou checkout originado do aplicativo Android (via leitura de QR Code ou manual). Aplica regras de negócio para determinar se deve enfileirar uma nova submissão ao Google Forms ou apenas atualizar o estado local. Implementa idempotência via `client_event_id`.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/mobile/events/submit`                    |
| **Autenticação** | Header `X-Mobile-Shared-Key`                   |
| **Content-Type** | `application/json`                             |
| **Tags**         | `mobile`                                       |

---

## Autenticação

Requer o header `X-Mobile-Shared-Key` com o valor configurado em `MOBILE_APP_SHARED_KEY`.

```
X-Mobile-Shared-Key: minha-chave-mobile
```

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "projeto": "Projeto Alpha",
  "action": "checkin",
  "local": "Portaria Principal",
  "event_time": "2024-05-25T08:30:00-03:00",
  "client_event_id": "android-AB12-1716652800-ci"
}
```

| Campo             | Tipo       | Obrigatório | Restrições                             | Descrição                                                              |
|-------------------|------------|-------------|----------------------------------------|------------------------------------------------------------------------|
| `chave`           | `string`   | Sim         | Exatamente 4 caracteres alfanuméricos  | Chave do usuário (normalizada para maiúsculas)                         |
| `projeto`         | `string`   | Sim         | 2–120 caracteres                       | Projeto onde o evento ocorre (deve existir no catálogo)                |
| `action`          | `string`   | Sim         | `"checkin"` ou `"checkout"`            | Tipo de evento                                                         |
| `local`           | `string`   | Não         | —                                      | Local físico; se omitido, usa `"Aplicativo"` como padrão               |
| `event_time`      | `datetime` | Sim         | ISO 8601 com timezone                  | Timestamp do evento registrado no dispositivo                          |
| `client_event_id` | `string`   | Sim         | 8–80 caracteres                        | ID único do evento gerado pelo app (chave de idempotência)             |

---

## Resposta

### Sucesso — Forms enfileirado

```json
{
  "ok": true,
  "duplicate": false,
  "queued_forms": true,
  "worker_healthy": true,
  "message": "Mobile event accepted and queued for Forms submission",
  "state": {
    "found": true,
    "chave": "AB12",
    "nome": "João Silva",
    "projeto": "Projeto Alpha",
    "current_action": "checkin",
    "current_event_time": "2024-05-25T08:30:00+08:00",
    "current_local": "Portaria Principal",
    "last_checkin_at": "2024-05-25T08:30:00+08:00",
    "last_checkout_at": "2024-05-24T17:05:00+08:00"
  }
}
```

### Sucesso — Forms não enfileirado (update local)

```json
{
  "ok": true,
  "duplicate": false,
  "queued_forms": false,
  "worker_healthy": true,
  "message": "Mobile event accepted without new Forms submission",
  "state": { ... }
}
```

### Sucesso — Evento duplicado

```json
{
  "ok": true,
  "duplicate": true,
  "queued_forms": false,
  "worker_healthy": true,
  "message": "Mobile event already submitted",
  "state": { ... }
}
```

| Campo           | Tipo      | Descrição                                                                     |
|-----------------|-----------|-------------------------------------------------------------------------------|
| `ok`            | `boolean` | Sempre `true`                                                                 |
| `duplicate`     | `boolean` | `true` se `client_event_id` já foi processado anteriormente                  |
| `queued_forms`  | `boolean` | `true` se uma submissão ao Forms foi enfileirada                             |
| `worker_healthy`| `boolean` | `true` se o worker de Forms está operacional no momento                      |
| `message`       | `string`  | Descrição do resultado                                                         |
| `state`         | `object`  | Estado atual do usuário após o processamento (ver `GET /api/mobile/state`)   |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Evento processado (verificar `duplicate` e `queued_forms`) |
| `401`  | Header `X-Mobile-Shared-Key` ausente ou inválido     |
| `422`  | Body inválido                                        |

### Exemplo de erro 422

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "chave"],
      "msg": "Value error, A chave deve ter 4 caracteres alfanumericos",
      "input": "AB1"
    }
  ]
}
```

---

## Side effects

- Cria o usuário se não existir (sem RFID, sem senha).
- Atualiza o estado atual do usuário (`users.checkin`, `users.time`, `users.local`).
- Cria um `UserSyncEvent` com `source="android"`.
- Pode enfileirar `FormsSubmission` dependendo das regras de negócio (mesmo dia, checkin antes de checkout, etc.).
- Grava evento em `check_events`.
- Chama `notify_admin_data_changed()` via SSE.
- Chama `fire_accident_hook_for_check_event()` para integração com Modo Acidente.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/mobile/events/submit \
  -H "Content-Type: application/json" \
  -H "X-Mobile-Shared-Key: minha-chave-mobile" \
  -d '{
    "chave": "AB12",
    "projeto": "Projeto Alpha",
    "action": "checkin",
    "local": "Portaria Principal",
    "event_time": "2024-05-25T08:30:00-03:00",
    "client_event_id": "android-AB12-1716652800-ci"
  }'
```
