# `POST /api/web/auth/logout`

## Visão Geral

Encerra a sessão do usuário removendo a chave do cookie de sessão. Não requer body. Pode ser chamado mesmo sem sessão ativa — sempre retorna sucesso.

| Atributo         | Valor                  |
|------------------|------------------------|
| **Método**       | `POST`                 |
| **Path**         | `/api/web/auth/logout` |
| **Autenticação** | Nenhuma obrigatória    |
| **Content-Type** | N/A                    |

---

## Autenticação

Nenhuma autenticação é necessária. O endpoint apenas remove a entrada `web_user_chave` do cookie de sessão, independentemente de haver ou não uma sessão ativa.

---

## Parâmetros

Nenhum parâmetro é necessário. O endpoint não aceita query params nem body.

---

## Resposta

### HTTP 200 — Sessão encerrada

```json
{
  "ok": true,
  "authenticated": false,
  "has_password": false,
  "message": "Sessao encerrada."
}
```

### Campos da resposta

| Campo           | Tipo    | Descrição                                          |
|-----------------|---------|----------------------------------------------------|
| `ok`            | boolean | Sempre `true`                                      |
| `authenticated` | boolean | Sempre `false` após logout                         |
| `has_password`  | boolean | Sempre `false` (estado pós-logout, sem significado semântico) |
| `message`       | string  | Confirmação do encerramento de sessão              |

---

## Códigos de status HTTP

| Código | Significado                        |
|--------|------------------------------------|
| `200`  | Logout realizado (sempre bem-sucedido) |

---

## Side effects

- Remove a chave `web_user_chave` do cookie de sessão.
- Não modifica nenhum registro no banco de dados.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST "http://127.0.0.1:8000/api/web/auth/logout" \
  -c cookies.txt -b cookies.txt

# O cookie de sessão em cookies.txt é invalidado após este comando.
```
