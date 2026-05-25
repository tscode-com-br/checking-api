# `POST /api/provider/updaterecords`

## Visão Geral

Recebe registros de check-in e checkout originados do sistema de ponto externo (provider), sincronizando-os com a base local. Este endpoint espelha dados que já passaram pelo Google Forms no provider — ele **nunca** re-enfileira submissão ao Forms para evitar loop de feedback.

Se o usuário não existir na base, é criado automaticamente. Se o projeto do usuário mudou, ele é atualizado. Requisições idempotentes são identificadas por hash SHA-1 dos campos `chave|projeto|atividade|informe|event_time_iso`.

| Atributo         | Valor                              |
|------------------|------------------------------------|
| **Método**       | `POST`                             |
| **Path**         | `/api/provider/updaterecords`      |
| **Autenticação** | Header `X-Provider-Shared-Key`     |
| **Content-Type** | `application/json`                 |
| **Tags**         | `provider`                         |

---

## Autenticação

Requer o header `X-Provider-Shared-Key` com o valor configurado em `PROVIDER_SHARED_KEY`. Se ausente ou inválido, retorna HTTP 401.

```
X-Provider-Shared-Key: minha-chave-provider
```

### Resposta em caso de falha de autenticação

```json
{
  "detail": "Invalid provider shared key"
}
```

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "nome": "João Silva",
  "projeto": "Projeto Alpha",
  "atividade": "check-in",
  "informe": "normal",
  "data": "25/05/2024",
  "hora": "08:30:00"
}
```

| Campo      | Tipo     | Obrigatório | Restrições                             | Descrição                                                 |
|------------|----------|-------------|----------------------------------------|-----------------------------------------------------------|
| `chave`    | `string` | Sim         | Exatamente 4 caracteres alfanuméricos  | Chave de identificação do usuário (normalizada para maiúsculas) |
| `nome`     | `string` | Sim         | 3–180 caracteres                       | Nome completo do colaborador                              |
| `projeto`  | `string` | Sim         | 2–120 caracteres                       | Nome do projeto (deve existir no catálogo)                |
| `atividade`| `string` | Sim         | `"check-in"` ou `"check-out"`          | Tipo de evento                                            |
| `informe`  | `string` | Sim         | `"normal"` ou `"retroativo"`           | Indica se o registro foi feito no horário ou retroativamente |
| `data`     | `string` | Sim         | Formato `dd/mm/aaaa` (10 caracteres)   | Data do evento                                            |
| `hora`     | `string` | Sim         | Formato `hh:mm:ss` (8 caracteres)      | Hora do evento                                            |

---

## Resposta

### Sucesso — novo registro

```json
{
  "ok": true,
  "duplicate": false,
  "created_user": false,
  "updated_project": false,
  "updated_current_state": true,
  "message": "Provider event processed successfully",
  "chave": "AB12",
  "projeto": "Projeto Alpha",
  "atividade": "check-in",
  "informe": "normal",
  "time": "2024-05-25T08:30:00+08:00"
}
```

### Sucesso — registro duplicado (idempotência)

```json
{
  "ok": true,
  "duplicate": true,
  "created_user": false,
  "updated_project": false,
  "updated_current_state": false,
  "message": "Provider event already processed",
  "chave": "AB12",
  "projeto": "Projeto Alpha",
  "atividade": "check-in",
  "informe": "normal",
  "time": "2024-05-25T08:30:00+08:00"
}
```

| Campo                  | Tipo       | Descrição                                                                     |
|------------------------|------------|-------------------------------------------------------------------------------|
| `ok`                   | `boolean`  | Sempre `true` em caso de sucesso                                              |
| `duplicate`            | `boolean`  | `true` se o evento já havia sido processado anteriormente                     |
| `created_user`         | `boolean`  | `true` se um novo usuário foi criado na base                                  |
| `updated_project`      | `boolean`  | `true` se o projeto ativo do usuário foi atualizado                           |
| `updated_current_state`| `boolean`  | `true` se o estado atual do usuário (`checkin`/`checkout`) foi atualizado     |
| `message`              | `string`   | Descrição do resultado                                                         |
| `chave`                | `string`   | Chave do usuário                                                              |
| `projeto`              | `string`   | Projeto onde o evento foi registrado                                          |
| `atividade`            | `string`   | `"check-in"` ou `"check-out"`                                                |
| `informe`              | `string`   | `"normal"` ou `"retroativo"`                                                 |
| `time`                 | `datetime` | Timestamp do evento com timezone do projeto                                  |

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Evento processado com sucesso (ou duplicata reconhecida)  |
| `401`  | Header `X-Provider-Shared-Key` ausente ou inválido        |
| `422`  | Body inválido (campos ausentes, formato incorreto, etc.)  |

### Exemplos de erro 422

**Formato de data inválido:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "data"],
      "msg": "Value error, A data deve estar no formato dd/mm/aaaa",
      "input": "2024-05-25"
    }
  ]
}
```

**Projeto não encontrado no catálogo:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "projeto"],
      "msg": "Value error, Projeto desconhecido: 'Projeto Inexistente'"
    }
  ]
}
```

---

## Side effects

- Cria um `User` caso não exista (sem RFID, sem senha).
- Atualiza `user.projeto` se o projeto mudou.
- Cria um `UserSyncEvent` com `source="provider"`.
- Atualiza o estado atual do usuário (`users.checkin`, `users.time`, `users.local`) se o evento do provider for o mais recente.
- Chama `notify_admin_data_changed()` via SSE para atualizar o painel admin em tempo real.
- **Não enfileira** envio ao Google Forms (este endpoint espelha dados que já vieram do Forms).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/provider/updaterecords \
  -H "Content-Type: application/json" \
  -H "X-Provider-Shared-Key: minha-chave-provider" \
  -d '{
    "chave": "AB12",
    "nome": "João Silva",
    "projeto": "Projeto Alpha",
    "atividade": "check-in",
    "informe": "normal",
    "data": "25/05/2024",
    "hora": "08:30:00"
  }'
```
