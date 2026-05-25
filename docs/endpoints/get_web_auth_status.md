# `GET /api/web/auth/status`

## Visão Geral

Verifica o status de autenticação de um usuário a partir da sua chave de 4 caracteres. Retorna se a chave está cadastrada, se possui senha definida e se a sessão atual já está autenticada.

| Atributo         | Valor                                                  |
|------------------|--------------------------------------------------------|
| **Método**       | `GET`                                                  |
| **Path**         | `/api/web/auth/status`                                 |
| **Autenticação** | Nenhuma obrigatória — lê o cookie de sessão se presente |
| **Content-Type** | N/A                                                    |

---

## Autenticação

Este endpoint não exige autenticação prévia. Ele inspeciona o cookie de sessão `session` (gerenciado pelo servidor via Starlette SessionMiddleware) para determinar se a chave informada já possui sessão ativa. Se a sessão contiver uma chave inválida ou diferente da consultada, o campo `authenticated` retornará `false` e a sessão será limpa.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo   | Obrigatório | Descrição                                                         |
|-----------|--------|-------------|-------------------------------------------------------------------|
| `chave`   | string | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12` |

**Regras de validação da chave:**
- Comprimento exato de 4 caracteres após normalização (`.strip().upper()`)
- Apenas letras e dígitos (`isalnum()`)
- Retorna HTTP 422 se inválida

---

## Resposta

### HTTP 200 — Chave encontrada com senha e sessão ativa

```json
{
  "found": true,
  "chave": "AB12",
  "has_password": true,
  "authenticated": true,
  "message": "Aplicacao liberada."
}
```

### HTTP 200 — Chave encontrada com senha, mas sem sessão ativa

```json
{
  "found": true,
  "chave": "AB12",
  "has_password": true,
  "authenticated": false,
  "message": "Digite sua senha para iniciar."
}
```

### HTTP 200 — Chave encontrada sem senha cadastrada

```json
{
  "found": true,
  "chave": "AB12",
  "has_password": false,
  "authenticated": false,
  "message": "Digite sua chave e crie uma senha."
}
```

### HTTP 200 — Chave não encontrada no sistema

```json
{
  "found": false,
  "chave": "ZZ99",
  "has_password": false,
  "authenticated": false,
  "message": "Digite sua chave e crie uma senha."
}
```

### Campos da resposta

| Campo            | Tipo    | Descrição                                                                          |
|------------------|---------|------------------------------------------------------------------------------------|
| `found`          | boolean | `true` se a chave existe na tabela `users`                                         |
| `chave`          | string  | Chave normalizada (maiúsculas) da consulta                                         |
| `has_password`   | boolean | `true` se o usuário tem senha cadastrada                                           |
| `authenticated`  | boolean | `true` se a sessão atual corresponde a esta chave e o usuário possui senha         |
| `message`        | string  | Mensagem amigável para exibição na interface                                       |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Consulta bem-sucedida (inclui casos onde a chave não foi encontrada) |
| `422`  | Chave com formato inválido (não-alfanumérica ou comprimento incorreto) |

---

## Side effects

- Se a sessão atual contiver esta chave mas o usuário não tiver mais senha cadastrada, a entrada de sessão é removida do cookie.
- Não cria nem modifica nenhum registro no banco de dados.

---

## Exemplo cURL (ambiente local)

```bash
# Verificar status da chave AB12
curl -s "http://127.0.0.1:8000/api/web/auth/status?chave=AB12" \
  -b cookies.txt

# Resposta esperada se chave existir com senha e sessão ativa:
# {"found":true,"chave":"AB12","has_password":true,"authenticated":true,"message":"Aplicacao liberada."}
```
