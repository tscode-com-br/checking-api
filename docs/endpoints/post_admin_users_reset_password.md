# `POST /api/admin/users/{user_id}/reset-password`

## Visão Geral

Remove a senha de acesso web de um usuário, permitindo que ele cadastre uma nova senha no próximo acesso. Útil para situações em que o usuário esqueceu sua senha ou precisa ter o acesso web reestabelecido pelo administrador.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/admin/users/{user_id}/reset-password`    |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Path Parameters

| Parâmetro  | Tipo      | Descrição                                |
|------------|-----------|------------------------------------------|
| `user_id`  | `integer` | ID interno do usuário com senha a resetar |

Este endpoint não requer body na requisição.

---

## Resposta

```json
{
  "ok": true,
  "message": "Senha removida com sucesso. O usuario podera cadastrar uma nova senha.",
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

| Campo              | Tipo             | Descrição                                                             |
|--------------------|------------------|-----------------------------------------------------------------------|
| `ok`               | `boolean`        | `true` em caso de sucesso                                             |
| `message`          | `string`         | Mensagem descritiva do resultado                                      |
| `message_key`      | `string \| null` | Chave i18n da mensagem (quando aplicável)                             |
| `message_params`   | `object`         | Parâmetros para interpolação da mensagem i18n                        |
| `error_code`       | `string \| null` | Código de erro estruturado (quando aplicável)                         |
| `issues`           | `array`          | Lista de problemas de validação (geralmente vazia em sucesso)        |
| `technical_detail` | `string \| null` | Detalhes técnicos adicionais (quando aplicável)                      |

**Variações da mensagem de resposta:**
- Se o usuário possuía senha: `"Senha removida com sucesso. O usuario podera cadastrar uma nova senha."`
- Se o usuário já não possuía senha: `"Esse usuario ja esta sem senha cadastrada e ja pode cadastrar uma nova senha."`

Em ambos os casos, `ok` é `true` e o status HTTP é `200`.

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Operação concluída (senha removida ou já era nula)   |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |
| `404`  | Usuário não encontrado                               |

---

## Side effects

- Remove o campo `senha` (hash) do usuário em `users` (define como `null`), caso existia.
- Emite notificação SSE para o painel admin (`notify_admin_data_changed`).
- Grava evento em `check_events` com `action="password"`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/users/42/reset-password
```
