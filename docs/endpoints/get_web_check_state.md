# `GET /api/web/check/state`

## Visão Geral

Retorna o estado atual de check-in/check-out do usuário identificado pela chave informada. Inclui informações sobre o último check-in, último check-out e a ação pendente esperada pelo sistema.

| Atributo         | Valor                      |
|------------------|----------------------------|
| **Método**       | `GET`                      |
| **Path**         | `/api/web/check/state`     |
| **Autenticação** | Cookie de sessão obrigatório (chave na sessão deve corresponder ao parâmetro `chave`) |
| **Content-Type** | N/A                        |

---

## Autenticação

Requer sessão ativa via cookie **e** que a chave armazenada na sessão seja idêntica ao parâmetro `chave` informado na query. Se a sessão estiver ausente, a chave for diferente da sessão ativa ou o usuário não tiver senha cadastrada, retorna HTTP 401.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo   | Obrigatório | Descrição                                                           |
|-----------|--------|-------------|---------------------------------------------------------------------|
| `chave`   | string | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12` |

**Regras de validação da chave:**
- Comprimento exato de 4 caracteres após normalização
- Apenas letras e dígitos
- Retorna HTTP 422 se inválida
- Retorna HTTP 401 se diferente da chave na sessão ativa

---

## Resposta

### HTTP 200 — Estado retornado com sucesso

**Usuário com check-in ativo (aguardando check-out):**
```json
{
  "found": true,
  "chave": "AB12",
  "projeto": "Projeto Alpha",
  "current_action": "checkout",
  "current_local": "Escritório Principal",
  "has_current_day_checkin": true,
  "last_checkin_at": "2024-03-15T08:30:00",
  "last_checkout_at": "2024-03-14T17:45:00",
  "transport_enabled": true
}
```

**Usuário sem check-in no dia (aguardando check-in):**
```json
{
  "found": true,
  "chave": "AB12",
  "projeto": "Projeto Alpha",
  "current_action": "checkin",
  "current_local": null,
  "has_current_day_checkin": false,
  "last_checkin_at": "2024-03-14T08:15:00",
  "last_checkout_at": "2024-03-14T17:30:00",
  "transport_enabled": false
}
```

### Campos da resposta

| Campo                   | Tipo            | Descrição                                                                                     |
|-------------------------|-----------------|-----------------------------------------------------------------------------------------------|
| `found`                 | boolean         | `true` se o usuário foi encontrado no banco de dados                                          |
| `chave`                 | string          | Chave normalizada do usuário                                                                  |
| `projeto`               | string\|null    | Projeto ativo do usuário; `null` se não definido                                              |
| `current_action`        | string\|null    | Próxima ação esperada: `"checkin"` (para entrar) ou `"checkout"` (para sair); `null` se indeterminado |
| `current_local`         | string\|null    | Local do último evento; `null` se não disponível                                              |
| `has_current_day_checkin` | boolean       | `true` se o usuário realizou check-in no dia atual (horário do projeto)                       |
| `last_checkin_at`       | datetime\|null  | Timestamp ISO 8601 do último check-in; `null` se nunca realizou check-in                     |
| `last_checkout_at`      | datetime\|null  | Timestamp ISO 8601 do último check-out; `null` se nunca realizou check-out                   |
| `transport_enabled`     | boolean         | `true` se o módulo de transporte está habilitado para o projeto ativo do usuário              |

---

## Códigos de status HTTP

| Código | Significado                                                         |
|--------|---------------------------------------------------------------------|
| `200`  | Estado retornado com sucesso                                        |
| `401`  | Sessão ausente, inválida, expirada ou chave não corresponde à sessão |
| `422`  | Chave com formato inválido                                          |

### Exemplos de erros

```json
// HTTP 401 — sem sessão ou sessão expirada
{"detail": "Sessao do usuario invalida ou expirada"}

// HTTP 401 — chave diferente da sessão ativa
{"detail": "A chave informada nao corresponde a sessao atual"}
```

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
# Requer cookie de sessão obtido via POST /api/web/auth/login com a mesma chave
curl -s "http://127.0.0.1:8000/api/web/check/state?chave=AB12" \
  -b cookies.txt
```
