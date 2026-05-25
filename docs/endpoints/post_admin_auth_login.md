# `POST /api/admin/auth/login`

## Visão Geral

Autentica um administrador com chave (4 caracteres) e senha, criando uma sessão HTTP segura via cookie. O ID do usuário é armazenado na chave `admin_user_id` da sessão (nome herdado por compatibilidade — o valor é `users.id`).

| Atributo         | Valor                        |
|------------------|------------------------------|
| **Método**       | `POST`                       |
| **Path**         | `/api/admin/auth/login`      |
| **Autenticação** | Nenhuma (endpoint público)   |
| **Content-Type** | `application/json`           |

---

## Autenticação

Endpoint público. Não requer sessão prévia. Após login bem-sucedido, o servidor define um cookie de sessão assinado que deve ser enviado em todas as requisições subsequentes.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "senha": "minha_senha"
}
```

| Campo  | Tipo     | Obrigatório | Validação                                 |
|--------|----------|-------------|-------------------------------------------|
| `chave` | `string` | Sim         | Exatamente 4 caracteres alfanuméricos (A-Z, 0-9). Convertido para maiúsculas. |
| `senha` | `string` | Sim         | Entre 3 e 20 caracteres.                 |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Login realizado com sucesso."
}
```

| Campo     | Tipo      | Descrição                          |
|-----------|-----------|------------------------------------|
| `ok`      | `boolean` | Sempre `true` em caso de sucesso.  |
| `message` | `string`  | Mensagem descritiva da operação.   |

---

## Códigos de status HTTP

| Código | Significado                                                                                          |
|--------|------------------------------------------------------------------------------------------------------|
| `200`  | Login bem-sucedido. Cookie de sessão definido.                                                       |
| `401`  | Chave não encontrada ou senha incorreta. Mensagem: `"Chave ou senha invalida"`.                      |
| `403`  | Usuário encontrado mas não possui acesso ao painel Admin, ou ainda não tem senha cadastrada.          |
| `422`  | Corpo da requisição inválido (campos ausentes ou fora do formato esperado).                           |

---

## Side effects

- Grava evento em `check_events` com `action="login"` e `source="admin"`, independentemente do resultado (status `"done"`, `"failed"` ou `"blocked"`).
- Em caso de sucesso, sobrescreve qualquer sessão admin anterior via `clear_admin_session`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -c cookies.txt -X POST http://127.0.0.1:8000/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "senha": "segredo"}'
```
