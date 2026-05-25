# `POST /api/admin/auth/request-password-reset`

## Visão Geral

Solicita redefinição de senha para um administrador: remove a senha atual do registro, deixando-a como `null`. Outro administrador precisará definir a nova senha via `POST /api/admin/administrators/{admin_id}/set-password`.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/admin/auth/request-password-reset`       |
| **Autenticação** | Nenhuma (endpoint público)                     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Endpoint público. Não requer sessão. Permite ao próprio administrador solicitar reset sem estar logado.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12"
}
```

| Campo   | Tipo     | Obrigatório | Validação                                                        |
|---------|----------|-------------|------------------------------------------------------------------|
| `chave` | `string` | Sim         | 4 caracteres alfanuméricos (A-Z, 0-9). Convertido para maiúsculas. |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Sua senha foi removida. Outro administrador devera cadastrar uma nova senha."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                                |
|--------|--------------------------------------------------------------------------------------------|
| `200`  | Senha removida com sucesso. Reset pendente.                                                 |
| `404`  | Chave não encontrada ou não pertence a um administrador.                                    |
| `409`  | Já existe reset pendente (senha já é `null`).                                              |
| `422`  | Formato de chave inválido.                                                                  |

---

## Side effects

- Define `users.senha = null` para o administrador identificado pela chave.
- Grava evento em `check_events` com `action="password"` e `status="pending"`.
- Notifica o painel admin via SSE.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/admin/auth/request-password-reset \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12"}'
```
