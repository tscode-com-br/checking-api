# `POST /api/web/auth/login`

## Visão Geral

Autentica um usuário com sua chave e senha. Em caso de sucesso, inicia a sessão gravando a chave no cookie de sessão do servidor.

| Atributo         | Valor              |
|------------------|--------------------|
| **Método**       | `POST`             |
| **Path**         | `/api/web/auth/login` |
| **Autenticação** | Nenhuma — credenciais informadas no body |
| **Content-Type** | `application/json` |

---

## Autenticação

Nenhuma autenticação prévia é necessária. As credenciais (`chave` + `senha`) são verificadas contra o hash bcrypt armazenado em `users.senha`. Após autenticação bem-sucedida, o servidor emite um cookie de sessão HTTP-only contendo a chave do usuário (`web_user_chave`).

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "senha": "minhasenha"
}
```

| Campo   | Tipo   | Obrigatório | Descrição                                                                |
|---------|--------|-------------|--------------------------------------------------------------------------|
| `chave` | string | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12`  |
| `senha` | string | Sim         | Senha — entre 1 e 10 caracteres                                          |

**Regras de validação:**
- `chave`: exatamente 4 caracteres alfanuméricos após `.strip().upper()`
- `senha`: comprimento entre 1 e 10 caracteres

---

## Resposta

### HTTP 200 — Login bem-sucedido

```json
{
  "ok": true,
  "authenticated": true,
  "has_password": true,
  "message": "Autenticacao concluida."
}
```

### Campos da resposta

| Campo           | Tipo    | Descrição                                    |
|-----------------|---------|----------------------------------------------|
| `ok`            | boolean | Sempre `true` em caso de sucesso             |
| `authenticated` | boolean | Sempre `true` após login bem-sucedido        |
| `has_password`  | boolean | Sempre `true` após login bem-sucedido        |
| `message`       | string  | Mensagem de confirmação                      |

---

## Códigos de status HTTP

| Código | Significado                                                                  |
|--------|------------------------------------------------------------------------------|
| `200`  | Login bem-sucedido; cookie de sessão emitido                                 |
| `401`  | Chave ou senha inválida (`"Chave ou senha invalida"`)                        |
| `404`  | Chave não cadastrada (`"A chave do usuario nao esta cadastrada"`) ou usuário sem senha (`"Nao existe senha cadastrada para esta chave"`) |
| `422`  | Chave com formato inválido ou campos fora dos limites                        |

### Exemplos de erros

```json
// HTTP 404 — chave não encontrada
{"detail": "A chave do usuario nao esta cadastrada"}

// HTTP 404 — usuário sem senha cadastrada
{"detail": "Nao existe senha cadastrada para esta chave"}

// HTTP 401 — senha incorreta
{"detail": "Chave ou senha invalida"}
```

---

## Side effects

- Grava a chave do usuário no cookie de sessão (`web_user_chave`) em caso de sucesso.
- Em caso de falha (chave inexistente ou sem senha), o cookie de sessão existente é limpo.
- Não modifica nenhum registro no banco de dados.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST "http://127.0.0.1:8000/api/web/auth/login" \
  -H "Content-Type: application/json" \
  -c cookies.txt -b cookies.txt \
  -d '{"chave": "AB12", "senha": "minhasenha"}'

# Após este comando, cookies.txt conterá o cookie de sessão
# que deve ser enviado nas requisições subsequentes.
```
