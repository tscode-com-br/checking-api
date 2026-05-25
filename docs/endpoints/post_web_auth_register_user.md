# `POST /api/web/auth/register-user`

## Visão Geral

Realiza o auto-cadastro de um novo usuário no sistema. Cria um registro na tabela `users`, associa o usuário aos projetos informados, define sua senha e inicia a sessão automaticamente. Retorna HTTP 201 em caso de sucesso.

| Atributo         | Valor                             |
|------------------|-----------------------------------|
| **Método**       | `POST`                            |
| **Path**         | `/api/web/auth/register-user`     |
| **Autenticação** | Nenhuma — endpoint público de cadastro |
| **Content-Type** | `application/json`                |

---

## Autenticação

Nenhuma autenticação é necessária. A chave informada não pode existir previamente em `users` nem ter uma solicitação de acesso pendente em `admin_access_requests`. Após o cadastro bem-sucedido, um cookie de sessão é emitido automaticamente.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "nome": "João da Silva",
  "projetos": ["Projeto Alpha", "Projeto Beta"],
  "email": "joao@exemplo.com",
  "senha": "minhasenha",
  "confirmar_senha": "minhasenha"
}
```

| Campo             | Tipo         | Obrigatório | Descrição                                                                      |
|-------------------|--------------|-------------|--------------------------------------------------------------------------------|
| `chave`           | string       | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12`        |
| `nome`            | string       | Sim         | Nome completo — entre 3 e 180 caracteres                                       |
| `projetos`        | list[string] | Sim         | Lista de projetos — pelo menos 1 projeto deve ser informado                    |
| `email`           | string\|null | Não         | E-mail do usuário — máximo 255 caracteres; `null` se não informado             |
| `senha`           | string       | Sim         | Senha — entre 3 e 10 caracteres. Não pode conter apenas espaços                |
| `confirmar_senha` | string       | Sim         | Confirmação da senha — deve ser idêntica a `senha`                             |

**Regras de validação:**
- `chave`: exatamente 4 caracteres alfanuméricos após `.strip().upper()`
- `nome`: mínimo 3, máximo 180 caracteres
- `projetos`: mínimo 1 elemento; nomes de projeto são normalizados
- `senha` e `confirmar_senha`: entre 3 e 10 caracteres; devem coincidir
- Se `senha != confirmar_senha`, retorna HTTP 422 com mensagem `"A confirmacao da senha nao confere"`

---

## Resposta

### HTTP 201 — Usuário cadastrado com sucesso

```json
{
  "ok": true,
  "authenticated": true,
  "has_password": true,
  "message": "Cadastro concluido com sucesso.",
  "projects": ["Projeto Alpha", "Projeto Beta"],
  "active_project": "Projeto Alpha"
}
```

### Campos da resposta

| Campo            | Tipo         | Descrição                                                                     |
|------------------|--------------|-------------------------------------------------------------------------------|
| `ok`             | boolean      | Sempre `true` em caso de sucesso                                              |
| `authenticated`  | boolean      | Sempre `true` após cadastro bem-sucedido                                      |
| `has_password`   | boolean      | Sempre `true` após cadastro bem-sucedido                                      |
| `message`        | string       | Mensagem de confirmação                                                       |
| `projects`       | list[string] | Lista normalizada dos projetos associados ao usuário                          |
| `active_project` | string       | Primeiro projeto da lista, definido como projeto ativo                        |

---

## Códigos de status HTTP

| Código | Significado                                                                           |
|--------|---------------------------------------------------------------------------------------|
| `201`  | Usuário cadastrado com sucesso; cookie de sessão emitido                              |
| `409`  | Chave já cadastrada (`"Esta chave ja esta cadastrada"`) ou solicitação pendente existente (`"Ja existe uma solicitacao pendente para essa chave"`) |
| `422`  | Campos inválidos (chave, comprimento de nome, senhas que não coincidem, etc.)         |

### Exemplos de erros

```json
// HTTP 409 — chave já cadastrada
{"detail": "Esta chave ja esta cadastrada"}

// HTTP 409 — solicitação pendente
{"detail": "Ja existe uma solicitacao pendente para essa chave"}

// HTTP 422 — senhas não coincidem
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, A confirmacao da senha nao confere"
    }
  ]
}
```

---

## Side effects

- Cria um novo registro em `users` com `rfid=null`, `checkin=null`, `inactivity_days=0`.
- Cria registros em `user_project_memberships` para cada projeto informado.
- Define `users.projeto` como o primeiro projeto normalizado da lista.
- Inicia sessão do usuário gravando a chave no cookie de sessão (`web_user_chave`).
- Dispara notificações SSE para o painel admin (`notify_admin_data_changed("admin")` e `notify_admin_data_changed("register")`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST "http://127.0.0.1:8000/api/web/auth/register-user" \
  -H "Content-Type: application/json" \
  -c cookies.txt -b cookies.txt \
  -d '{
    "chave": "AB12",
    "nome": "Joao da Silva",
    "projetos": ["Projeto Alpha"],
    "email": "joao@exemplo.com",
    "senha": "senha123",
    "confirmar_senha": "senha123"
  }'
```
