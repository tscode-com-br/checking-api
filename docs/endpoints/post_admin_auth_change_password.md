# `POST /api/admin/auth/change-password`

## Visão Geral

Permite que um administrador troque sua própria senha, fornecendo a senha atual e a nova senha desejada. Operação de autoatendimento — não requer sessão ativa, apenas conhecimento da senha atual.

| Atributo         | Valor                                    |
|------------------|------------------------------------------|
| **Método**       | `POST`                                   |
| **Path**         | `/api/admin/auth/change-password`        |
| **Autenticação** | Nenhuma obrigatória (valida via senha atual) |
| **Content-Type** | `application/json`                       |

---

## Autenticação

Endpoint público. A autenticação é feita pela combinação de `chave` + `senha_atual`. Não utiliza cookie de sessão.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "senha_atual": "senha_velha",
  "nova_senha": "nova123",
  "confirmar_senha": "nova123"
}
```

| Campo            | Tipo     | Obrigatório | Validação                                                        |
|------------------|----------|-------------|------------------------------------------------------------------|
| `chave`          | `string` | Sim         | 4 caracteres alfanuméricos (A-Z, 0-9). Convertido para maiúsculas. |
| `senha_atual`    | `string` | Sim         | 3–20 caracteres.                                                 |
| `nova_senha`     | `string` | Sim         | 3–10 caracteres. Deve ser diferente de `senha_atual`.            |
| `confirmar_senha`| `string` | Sim         | 3–10 caracteres. Deve ser idêntica a `nova_senha`.               |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Senha alterada com sucesso."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                    |
|--------|--------------------------------------------------------------------------------|
| `200`  | Senha alterada com sucesso.                                                    |
| `401`  | Senha atual incorreta.                                                         |
| `403`  | Usuário não tem perfil admin, ou não possui senha cadastrada (reset pendente). |
| `404`  | Chave não encontrada.                                                          |
| `422`  | Dados inválidos (nova senha igual à atual, confirmação não confere, etc.).     |

---

## Side effects

- Atualiza `users.senha` com o hash bcrypt da nova senha.
- Grava evento em `check_events` com `action="password"` e `status="updated"`.
- Notifica o painel admin via SSE (`reason="event"`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/admin/auth/change-password \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "senha_atual": "senha_velha", "nova_senha": "nova123", "confirmar_senha": "nova123"}'
```
