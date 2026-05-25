# `POST /api/mobile/events/forms-submit`

## Visão Geral

Registra um evento de check-in ou checkout que **já foi submetido ao Google Forms** pelo aplicativo Android. Este endpoint espelha o resultado do Forms de volta ao banco local, análogo ao `POST /api/provider/updaterecords` mas para o canal mobile. Não re-enfileira envio ao Forms.

O campo `informe` indica se o registro foi feito no horário (`"normal"`) ou de forma retroativa (`"retroativo"`).

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/mobile/events/forms-submit`              |
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
  "informe": "normal",
  "local": "Portaria Principal",
  "event_time": "2024-05-25T08:30:00-03:00",
  "client_event_id": "android-forms-AB12-1716652800-ci"
}
```

| Campo             | Tipo       | Obrigatório | Restrições                             | Descrição                                                              |
|-------------------|------------|-------------|----------------------------------------|------------------------------------------------------------------------|
| `chave`           | `string`   | Sim         | Exatamente 4 caracteres alfanuméricos  | Chave do usuário (normalizada para maiúsculas)                         |
| `projeto`         | `string`   | Sim         | 2–120 caracteres                       | Projeto onde o evento ocorre                                           |
| `action`          | `string`   | Sim         | `"checkin"` ou `"checkout"`            | Tipo de evento                                                         |
| `informe`         | `string`   | Sim         | `"normal"` ou `"retroativo"`           | Tipo do registro no Forms (case-insensitive, normalizado para minúsculo) |
| `local`           | `string`   | Não         | —                                      | Local físico; se omitido, usa `"Aplicativo"` como padrão               |
| `event_time`      | `datetime` | Sim         | ISO 8601 com timezone                  | Timestamp do evento registrado no dispositivo                          |
| `client_event_id` | `string`   | Sim         | 8–80 caracteres                        | ID único do evento gerado pelo app (chave de idempotência)             |

---

## Resposta

### Sucesso

```json
{
  "ok": true,
  "duplicate": false,
  "queued_forms": false,
  "worker_healthy": true,
  "message": "Mobile Forms event processed successfully",
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

### Duplicata reconhecida

```json
{
  "ok": true,
  "duplicate": true,
  "queued_forms": false,
  "worker_healthy": true,
  "message": "Mobile Forms event already processed",
  "state": { ... }
}
```

| Campo           | Tipo      | Descrição                                                               |
|-----------------|-----------|-------------------------------------------------------------------------|
| `ok`            | `boolean` | Sempre `true`                                                           |
| `duplicate`     | `boolean` | `true` se `client_event_id` já havia sido processado                   |
| `queued_forms`  | `boolean` | Sempre `false` — este endpoint nunca enfileira Forms                    |
| `worker_healthy`| `boolean` | Status do worker de Forms (informativo)                                 |
| `message`       | `string`  | Descrição do resultado                                                   |
| `state`         | `object`  | Estado atual do usuário (ver `GET /api/mobile/state`)                   |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Evento processado (verificar `duplicate`)            |
| `401`  | Header `X-Mobile-Shared-Key` ausente ou inválido     |
| `422`  | Body inválido (campos ausentes ou com formato errado) |

### Exemplo de erro 422

**`informe` inválido:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "informe"],
      "msg": "Value error, Informe deve ser 'Normal' ou 'Retroativo'",
      "input": "atrasado"
    }
  ]
}
```

---

## Side effects

- Cria o usuário se não existir.
- Cria um `UserSyncEvent` com `source="android_forms"`.
- Atualiza o estado atual do usuário se o evento for o mais recente.
- **Não enfileira** envio ao Google Forms (dados já originam do Forms).
- Chama `notify_admin_data_changed()` via SSE.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/mobile/events/forms-submit \
  -H "Content-Type: application/json" \
  -H "X-Mobile-Shared-Key: minha-chave-mobile" \
  -d '{
    "chave": "AB12",
    "projeto": "Projeto Alpha",
    "action": "checkin",
    "informe": "normal",
    "local": "Portaria Principal",
    "event_time": "2024-05-25T08:30:00-03:00",
    "client_event_id": "android-forms-AB12-1716652800-ci"
  }'
```
