# `DELETE /api/admin/forms`

## Visão Geral

Remove **todos** os registros de formulários de providers da tabela `user_sync_events` (registros com `source="provider"` e `action` em `checkin`/`checkout`). Operação de limpeza administrativa para descartar entradas de formulários que não serão mais processadas ou que já foram processadas e não são mais necessárias.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `DELETE`                                |
| **Path**         | `/api/admin/forms`                      |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | —                                       |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

Nenhum. O endpoint remove todos os registros de formulários sem filtro — não aceita corpo de requisição nem query parameters.

---

## Resposta

**HTTP 200 — Sucesso (registros removidos)**

```json
{
  "ok": true,
  "message": "42 registro(s) de Forms removido(s) com sucesso.",
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

**HTTP 200 — Sem registros para remover**

```json
{
  "ok": true,
  "message": "Nao havia registros de Forms para remover.",
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null
}
```

| Campo              | Tipo              | Descrição                                                                       |
|--------------------|-------------------|---------------------------------------------------------------------------------|
| `ok`               | `boolean`         | Sempre `true` em operação bem-sucedida.                                         |
| `message`          | `string`          | Mensagem descritiva com a quantidade de registros removidos.                    |
| `message_key`      | `string \| null`  | Chave de i18n da mensagem (não utilizado neste endpoint).                       |
| `message_params`   | `object`          | Parâmetros de i18n (não utilizado neste endpoint).                              |
| `error_code`       | `string \| null`  | Código de erro estruturado (não utilizado neste endpoint).                      |
| `issues`           | `list`            | Lista de problemas de validação (não utilizado neste endpoint).                 |
| `technical_detail` | `string \| null`  | Detalhe técnico adicional (não utilizado neste endpoint).                       |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso (com ou sem registros removidos — verificar o campo `ok`).  |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

- **Remove** todos os registros de `user_sync_events` com `source="provider"` e `action` em `checkin`/`checkout`. Operação irreversível.
- **Notifica** o painel admin via SSE (`notify_admin_data_changed("event")`) para atualizar a aba de eventos em tempo real.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X DELETE http://127.0.0.1:8000/api/admin/forms
```
