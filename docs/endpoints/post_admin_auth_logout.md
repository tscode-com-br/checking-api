# `POST /api/admin/auth/logout`

## Visão Geral

Encerra a sessão do administrador autenticado, invalidando o cookie de sessão. Idempotente: se chamado sem sessão ativa, retorna sucesso igualmente.

| Atributo         | Valor                         |
|------------------|-------------------------------|
| **Método**       | `POST`                        |
| **Path**         | `/api/admin/auth/logout`      |
| **Autenticação** | Nenhuma obrigatória (graceful) |
| **Content-Type** | Nenhum (sem corpo)            |

---

## Autenticação

O endpoint funciona com ou sem sessão ativa. Se houver sessão válida, o usuário é identificado para fins de log antes de a sessão ser destruída.

---

## Parâmetros

Nenhum. Sem query parameters, path parameters ou request body.

---

## Resposta

**HTTP 200 — Sucesso (sempre)**

```json
{
  "ok": true,
  "message": "Sessao encerrada com sucesso."
}
```

| Campo     | Tipo      | Descrição                        |
|-----------|-----------|----------------------------------|
| `ok`      | `boolean` | Sempre `true`.                   |
| `message` | `string`  | Confirmação do encerramento.     |

---

## Códigos de status HTTP

| Código | Significado                                                   |
|--------|---------------------------------------------------------------|
| `200`  | Sessão encerrada (ou já estava encerrada — idempotente).      |

---

## Side effects

- Grava evento em `check_events` com `action="logout"` e `source="admin"` se havia uma sessão autenticada.
- Destrói o cookie de sessão via `clear_admin_session`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/auth/logout
```
