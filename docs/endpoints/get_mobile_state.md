# `GET /api/mobile/state`

## Visão Geral

Retorna o estado atual de check-in/checkout de um usuário específico, identificado pela sua `chave`. Utilizado pelo aplicativo Android para sincronizar o estado local com o servidor antes de exibir a tela inicial ou ao retomar o app.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/mobile/state`                            |
| **Autenticação** | Header `X-Mobile-Shared-Key`                   |
| **Tags**         | `mobile`                                       |

---

## Autenticação

Requer o header `X-Mobile-Shared-Key` com o valor configurado em `MOBILE_APP_SHARED_KEY`. Em caso de chave inválida, registra um evento de falha e retorna HTTP 401.

```
X-Mobile-Shared-Key: minha-chave-mobile
```

### Resposta em caso de falha de autenticação

```json
{
  "detail": "Invalid mobile shared key"
}
```

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo     | Obrigatório | Descrição                                                       |
|-----------|----------|-------------|------------------------------------------------------------------|
| `chave`   | `string` | Sim         | Chave de identificação do usuário (4 caracteres alfanuméricos)  |

---

## Resposta

### 200 OK — Usuário encontrado

```json
{
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
```

### 200 OK — Usuário não encontrado

```json
{
  "found": false,
  "chave": "ZZ99",
  "nome": null,
  "projeto": null,
  "current_action": null,
  "current_event_time": null,
  "current_local": null,
  "last_checkin_at": null,
  "last_checkout_at": null
}
```

| Campo                | Tipo              | Descrição                                                       |
|----------------------|-------------------|-----------------------------------------------------------------|
| `found`              | `boolean`         | `true` se o usuário foi encontrado na base                      |
| `chave`              | `string`          | Chave consultada (normalizada para maiúsculas)                  |
| `nome`               | `string\|null`   | Nome completo do usuário                                        |
| `projeto`            | `string\|null`   | Projeto ativo do usuário                                        |
| `current_action`     | `string\|null`   | Última ação registrada: `"checkin"`, `"checkout"` ou `null`     |
| `current_event_time` | `datetime\|null` | Timestamp da última atividade                                   |
| `current_local`      | `string\|null`   | Local da última atividade                                       |
| `last_checkin_at`    | `datetime\|null` | Timestamp do último check-in registrado                         |
| `last_checkout_at`   | `datetime\|null` | Timestamp do último checkout registrado                         |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Sucesso — verificar `found` para saber se usuário existe |
| `401`  | Header `X-Mobile-Shared-Key` ausente ou inválido     |
| `422`  | Query parameter `chave` ausente                      |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s "http://127.0.0.1:8000/api/mobile/state?chave=AB12" \
  -H "X-Mobile-Shared-Key: minha-chave-mobile"
```
