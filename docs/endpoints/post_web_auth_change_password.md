# `POST /api/web/auth/change-password`

## Visão Geral

Altera a senha de um usuário existente. Requer a senha antiga para confirmação. Após a alteração bem-sucedida, a sessão é renovada automaticamente.

| Atributo         | Valor                            |
|------------------|----------------------------------|
| **Método**       | `POST`                           |
| **Path**         | `/api/web/auth/change-password`  |
| **Autenticação** | Nenhuma obrigatória — autenticado via credenciais no body |
| **Content-Type** | `application/json`               |

---

## Autenticação

Nenhuma sessão ativa é verificada. A autenticação ocorre por validação da `senha_antiga` contra o hash armazenado em `users.senha`. Este mecanismo permite que usuários que perderam a sessão alterem sua senha sem precisar fazer login antes.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "senha_antiga": "senhavelha",
  "nova_senha": "senhanova"
}
```

| Campo         | Tipo   | Obrigatório | Descrição                                                                |
|---------------|--------|-------------|--------------------------------------------------------------------------|
| `chave`       | string | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12`  |
| `senha_antiga`| string | Sim         | Senha atual — entre 3 e 10 caracteres                                    |
| `nova_senha`  | string | Sim         | Nova senha — entre 3 e 10 caracteres. Não pode conter apenas espaços     |

**Regras de validação:**
- `chave`: exatamente 4 caracteres alfanuméricos após `.strip().upper()`
- `senha_antiga` e `nova_senha`: comprimento entre 3 e 10 caracteres

---

## Resposta

### HTTP 200 — Senha alterada com sucesso

```json
{
  "ok": true,
  "authenticated": true,
  "has_password": true,
  "message": "Senha alterada com sucesso."
}
```

### Campos da resposta

| Campo           | Tipo    | Descrição                                      |
|-----------------|---------|------------------------------------------------|
| `ok`            | boolean | Sempre `true` em caso de sucesso               |
| `authenticated` | boolean | Sempre `true` após alteração bem-sucedida      |
| `has_password`  | boolean | Sempre `true` após alteração bem-sucedida      |
| `message`       | string  | Mensagem de confirmação                        |

---

## Códigos de status HTTP

| Código | Significado                                                                              |
|--------|------------------------------------------------------------------------------------------|
| `200`  | Senha alterada com sucesso; sessão renovada                                              |
| `401`  | Senha antiga inválida (`"Senha antiga invalida"`)                                        |
| `404`  | Chave não cadastrada (`"A chave do usuario nao esta cadastrada"`) ou usuário sem senha (`"Nao existe senha cadastrada para esta chave"`) |
| `422`  | Campos com formato inválido ou comprimento fora dos limites                              |

### Exemplos de erros

```json
// HTTP 404 — chave não encontrada
{"detail": "A chave do usuario nao esta cadastrada"}

// HTTP 404 — usuário sem senha cadastrada
{"detail": "Nao existe senha cadastrada para esta chave"}

// HTTP 401 — senha antiga incorreta
{"detail": "Senha antiga invalida"}
```

---

## Side effects

- Atualiza o campo `senha` do usuário na tabela `users` com o hash bcrypt da nova senha.
- Renova a sessão do usuário gravando a chave no cookie de sessão (`web_user_chave`).
- Em caso de falha por chave inexistente ou sem senha, o cookie de sessão existente é limpo.
- Não modifica nenhum outro dado do usuário.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST "http://127.0.0.1:8000/api/web/auth/change-password" \
  -H "Content-Type: application/json" \
  -c cookies.txt -b cookies.txt \
  -d '{
    "chave": "AB12",
    "senha_antiga": "senhavelha",
    "nova_senha": "senhanova"
  }'
```
