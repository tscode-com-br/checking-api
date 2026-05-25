# `GET /api/web/user-projects`

## Visão Geral

Retorna os projetos associados ao usuário autenticado, incluindo qual é o projeto ativo no momento.

| Atributo         | Valor                      |
|------------------|----------------------------|
| **Método**       | `GET`                      |
| **Path**         | `/api/web/user-projects`   |
| **Autenticação** | Cookie de sessão obrigatório |
| **Content-Type** | N/A                        |

---

## Autenticação

Requer sessão ativa via cookie. O servidor verifica a chave armazenada em `web_user_chave` no cookie de sessão, busca o usuário no banco e confirma que ele possui senha cadastrada. Se a sessão estiver ausente ou inválida, retorna HTTP 401.

---

## Parâmetros

Nenhum parâmetro é aceito. A identidade do usuário é obtida exclusivamente do cookie de sessão.

---

## Resposta

### HTTP 200 — Projetos do usuário

```json
{
  "projects": ["Projeto Alpha", "Projeto Beta"],
  "active_project": "Projeto Alpha"
}
```

### Campos da resposta

| Campo            | Tipo         | Descrição                                                                          |
|------------------|--------------|------------------------------------------------------------------------------------|
| `projects`       | list[string] | Lista de nomes de todos os projetos aos quais o usuário está associado             |
| `active_project` | string       | Nome do projeto atualmente ativo para o usuário (campo `users.projeto`)            |

---

## Códigos de status HTTP

| Código | Significado                                                        |
|--------|--------------------------------------------------------------------|
| `200`  | Projetos retornados com sucesso                                    |
| `401`  | Sessão ausente, inválida ou expirada (`"Sessao do usuario invalida ou expirada"`) |

### Exemplo de erro

```json
// HTTP 401 — sem sessão ativa
{"detail": "Sessao do usuario invalida ou expirada"}
```

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
# Requer cookie de sessão obtido via POST /api/web/auth/login
curl -s "http://127.0.0.1:8000/api/web/user-projects" \
  -b cookies.txt
```
