# `POST /api/admin/auth/verify-current-password`

## Visão Geral

Verifica se a senha atual de um administrador está correta, sem alterar nenhum dado. Usado pelo frontend para validar a senha antes de mostrar o formulário de troca de senha.

| Atributo         | Valor                                           |
|------------------|-------------------------------------------------|
| **Método**       | `POST`                                          |
| **Path**         | `/api/admin/auth/verify-current-password`       |
| **Autenticação** | Nenhuma (endpoint público)                      |
| **Content-Type** | `application/json`                              |

---

## Autenticação

Endpoint público. Não requer sessão ativa.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "senha_atual": "minha_senha"
}
```

| Campo        | Tipo     | Obrigatório | Validação                                                        |
|--------------|----------|-------------|------------------------------------------------------------------|
| `chave`      | `string` | Sim         | 4 caracteres alfanuméricos (A-Z, 0-9). Convertido para maiúsculas. |
| `senha_atual`| `string` | Sim         | 3–20 caracteres.                                                 |

---

## Resposta

**HTTP 200 — Senha correta**

```json
{
  "ok": true,
  "valid": true,
  "message": "Senha atual confirmada."
}
```

**HTTP 200 — Senha incorreta**

```json
{
  "ok": true,
  "valid": false,
  "message": "A senha atual nao confere."
}
```

| Campo     | Tipo      | Descrição                                              |
|-----------|-----------|--------------------------------------------------------|
| `ok`      | `boolean` | Sempre `true` (indica que a operação foi processada).  |
| `valid`   | `boolean` | `true` se a senha confere; `false` caso contrário.     |
| `message` | `string`  | Mensagem descritiva.                                   |

---

## Códigos de status HTTP

| Código | Significado                                                                    |
|--------|--------------------------------------------------------------------------------|
| `200`  | Verificação processada (conferir `valid` no corpo para o resultado).           |
| `403`  | Usuário não tem acesso admin, ou não possui senha cadastrada.                  |
| `404`  | Chave não encontrada.                                                          |
| `422`  | Formato inválido.                                                              |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/admin/auth/verify-current-password \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "senha_atual": "minha_senha"}'
```
