# `POST /api/mobile/events/sync`

## Visão Geral

Sincroniza um evento de check-in ou checkout do aplicativo Android com a base local, **sem** tentar enfileirar envio ao Google Forms. Destinado a casos onde o app precisa apenas garantir consistência do estado no servidor (ex.: sincronização em background após reconexão), sem acionar o fluxo completo de submissão ao Forms.

Diferente de `POST /api/mobile/events/submit`, este endpoint não avalia regras de negócio para Forms — sempre atualiza o estado e cria o `UserSyncEvent`.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/mobile/events/sync`                      |
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
  "action": "checkout",
  "local": "Portaria Principal",
  "event_time": "2024-05-25T17:05:00-03:00",
  "client_event_id": "android-AB12-1716681900-co"
}
```

| Campo             | Tipo       | Obrigatório | Restrições                             | Descrição                                                              |
|-------------------|------------|-------------|----------------------------------------|------------------------------------------------------------------------|
| `chave`           | `string`   | Sim         | Exatamente 4 caracteres alfanuméricos  | Chave do usuário (normalizada para maiúsculas)                         |
| `projeto`         | `string`   | Sim         | 2–120 caracteres                       | Projeto onde o evento ocorre                                           |
| `action`          | `string`   | Sim         | `"checkin"` ou `"checkout"`            | Tipo de evento                                                         |
| `local`           | `string`   | Não         | —                                      | Local físico; se omitido, usa `"Aplicativo"` como padrão               |
| `event_time`      | `datetime` | Sim         | ISO 8601 com timezone                  | Timestamp do evento registrado no dispositivo                          |
| `client_event_id` | `string`   | Sim         | 8–80 caracteres                        | ID único do evento gerado pelo app (chave de idempotência)             |

---

## Resposta

### Sucesso — evento sincronizado

```json
{
  "ok": true,
  "duplicate": false,
  "message": "Mobile event synchronized successfully",
  "state": {
    "found": true,
    "chave": "AB12",
    "nome": "João Silva",
    "projeto": "Projeto Alpha",
    "current_action": "checkout",
    "current_event_time": "2024-05-25T17:05:00+08:00",
    "current_local": "Portaria Principal",
    "last_checkin_at": "2024-05-25T08:30:00+08:00",
    "last_checkout_at": "2024-05-25T17:05:00+08:00"
  }
}
```

### Sucesso — duplicata reconhecida

```json
{
  "ok": true,
  "duplicate": true,
  "message": "Mobile event already synchronized",
  "state": { ... }
}
```

| Campo       | Tipo      | Descrição                                                               |
|-------------|-----------|-------------------------------------------------------------------------|
| `ok`        | `boolean` | Sempre `true`                                                           |
| `duplicate` | `boolean` | `true` se `client_event_id` com `source="android"` já foi processado   |
| `message`   | `string`  | Descrição do resultado                                                   |
| `state`     | `object`  | Estado atual do usuário após sincronização (ver `GET /api/mobile/state`) |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Sincronizado (verificar `duplicate`)                 |
| `401`  | Header `X-Mobile-Shared-Key` ausente ou inválido     |
| `422`  | Body inválido                                        |

---

## Side effects

- Cria o usuário se não existir.
- Atualiza o estado atual do usuário (`users.checkin`, `users.time`, `users.local`).
- Cria um `UserSyncEvent` com `source="android"`.
- Grava evento em `check_events` com status `"created"` (novo usuário) ou `"synced"` (usuário existente).
- Chama `notify_admin_data_changed()` via SSE.
- Chama `fire_accident_hook_for_check_event()` para integração com Modo Acidente.
- **Não enfileira** envio ao Google Forms.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/mobile/events/sync \
  -H "Content-Type: application/json" \
  -H "X-Mobile-Shared-Key: minha-chave-mobile" \
  -d '{
    "chave": "AB12",
    "projeto": "Projeto Alpha",
    "action": "checkout",
    "local": "Portaria Principal",
    "event_time": "2024-05-25T17:05:00-03:00",
    "client_event_id": "android-AB12-1716681900-co"
  }'
```
