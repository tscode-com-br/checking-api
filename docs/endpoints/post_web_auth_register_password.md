# `POST /api/web/auth/register-password`

## Visão Geral

Cadastra uma senha para um usuário que já existe no sistema mas ainda não possui senha definida. Após o cadastro bem-sucedido, a sessão do usuário é iniciada automaticamente via cookie.

| Atributo         | Valor              |
|------------------|--------------------|
| **Método**       | `POST`             |
| **Path**         | `/api/web/auth/register-password` |
| **Autenticação** | Nenhuma obrigatória — o usuário ainda não tem senha |
| **Content-Type** | `application/json` |

---

## Autenticação

Nenhuma autenticação é necessária para chamar este endpoint. O pré-requisito é que a chave informada exista na tabela `users` e que o usuário ainda **não possua** senha cadastrada. Após o cadastro, um cookie de sessão é emitido automaticamente.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "senha": "minhasenha",
  "projeto": "Projeto Alpha"
}
```

| Campo    | Tipo   | Obrigatório | Descrição                                                                      |
|----------|--------|-------------|--------------------------------------------------------------------------------|
| `chave`  | string | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12`        |
| `senha`  | string | Sim         | Nova senha — entre 3 e 10 caracteres. Não pode conter apenas espaços em branco |
| `projeto`| string | Não         | Nome do projeto para associar ao usuário. Ignorado se `null` ou vazio          |

**Regras de validação:**
- `chave`: exatamente 4 caracteres alfanuméricos após `.strip().upper()`
- `senha`: comprimento entre 3 e 10 caracteres
- Se `projeto` for informado, deve ter entre 2 e 120 caracteres

---

## Resposta

### HTTP 200 — Senha cadastrada com sucesso

```json
{
  "ok": true,
  "authenticated": true,
  "has_password": true,
  "message": "Senha cadastrada com sucesso."
}
```

### Campos da resposta

| Campo           | Tipo    | Descrição                                                  |
|-----------------|---------|------------------------------------------------------------|
| `ok`            | boolean | Sempre `true` em caso de sucesso                           |
| `authenticated` | boolean | Sempre `true` após cadastro bem-sucedido                   |
| `has_password`  | boolean | Sempre `true` após cadastro bem-sucedido                   |
| `message`       | string  | Mensagem de confirmação para exibição na interface          |

---

## Códigos de status HTTP

| Código | Significado                                                              |
|--------|--------------------------------------------------------------------------|
| `200`  | Senha cadastrada com sucesso; cookie de sessão emitido                   |
| `404`  | Chave não cadastrada no sistema (`"A chave do usuario nao esta cadastrada"`) |
| `409`  | Usuário já possui senha cadastrada (`"Esta chave ja possui uma senha cadastrada"`) |
| `422`  | Chave com formato inválido ou campos com valores fora dos limites         |

### Exemplos de erros

```json
// HTTP 404 — chave não encontrada
{"detail": "A chave do usuario nao esta cadastrada"}

// HTTP 409 — usuário já tem senha
{"detail": "Esta chave ja possui uma senha cadastrada"}

// HTTP 422 — chave inválida
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "chave"],
      "msg": "Value error, A chave deve ter 4 caracteres alfanumericos"
    }
  ]
}
```

---

## Side effects

- Atualiza o campo `senha` do usuário na tabela `users` com o hash bcrypt da senha informada.
- Inicia sessão do usuário gravando a chave no cookie de sessão (`web_user_chave`).
- Não envia notificações SSE.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST "http://127.0.0.1:8000/api/web/auth/register-password" \
  -H "Content-Type: application/json" \
  -c cookies.txt -b cookies.txt \
  -d '{"chave": "AB12", "senha": "senha123"}'
```
