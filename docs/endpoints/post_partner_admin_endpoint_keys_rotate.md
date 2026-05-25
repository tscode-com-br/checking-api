# `POST /api/partner/admin/endpoint-keys/{endpoint_name}/rotate`

## Visão Geral

Gera e armazena uma nova chave secreta para o endpoint especificado, invalidando a chave anterior. A nova chave tem 32 caracteres hexadecimais gerados com `secrets.token_hex(16)`. Destinado a administradores com `perfil=9` para rotação periódica ou emergencial de credenciais.

| Atributo         | Valor                                                              |
|------------------|--------------------------------------------------------------------|
| **Método**       | `POST`                                                             |
| **Path**         | `/api/partner/admin/endpoint-keys/{endpoint_name}/rotate`         |
| **Autenticação** | Sessão administrativa com `perfil=9` (cookie)                     |
| **Content-Type** | Nenhum body necessário                                             |
| **Tags**         | `partner`                                                          |

---

## Autenticação

Requer sessão administrativa válida no cookie de sessão com `perfil == 9`. Mesmas regras do endpoint `GET /api/partner/admin/endpoint-keys`.

### Resposta em caso de falha de autenticação

**Sem sessão ou sessão expirada:**
```json
{
  "detail": "Sessao administrativa invalida ou expirada"
}
```

**Perfil diferente de 9:**
```json
{
  "detail": "Apenas administradores com perfil 9 podem gerenciar chaves de endpoints."
}
```

---

## Parâmetros

### Path Parameters

| Parâmetro       | Tipo     | Descrição                                                                 |
|-----------------|----------|---------------------------------------------------------------------------|
| `endpoint_name` | `string` | Nome do endpoint cuja chave será rotacionada (ex.: `"checkinginfo"`)     |

---

## Resposta

### 200 OK — Chave rotacionada com sucesso

```json
{
  "ok": true,
  "message": "Chave do endpoint 'checkinginfo' atualizada com sucesso.",
  "endpoint_name": "checkinginfo",
  "secret_key": "f3a7b2c1d9e84f5a6b7c8d9e0f1a2b3c"
}
```

| Campo           | Tipo      | Descrição                                              |
|-----------------|-----------|--------------------------------------------------------|
| `ok`            | `boolean` | Sempre `true` em caso de sucesso                       |
| `message`       | `string`  | Confirmação da operação                                |
| `endpoint_name` | `string`  | Nome do endpoint rotacionado                           |
| `secret_key`    | `string`  | Nova chave secreta em texto claro (32 caracteres hex)  |

### 404 Not Found — Endpoint não encontrado

```json
{
  "detail": "Endpoint nao encontrado."
}
```

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Chave rotacionada com sucesso                             |
| `401`  | Sessão ausente ou expirada                                |
| `403`  | Usuário sem permissão (sem acesso admin ou perfil != 9)   |
| `404`  | `endpoint_name` não existe na tabela `endpoint_api_keys`  |

---

## Side effects

- Atualiza o campo `secret_key` do registro em `endpoint_api_keys` com a nova chave gerada.
- Atualiza o campo `updated_at` com o horário atual (SGT).
- A chave anterior é **imediatamente invalidada** — sistemas que ainda usarem a chave antiga receberão HTTP 403 em requisições subsequentes ao endpoint protegido.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/partner/admin/endpoint-keys/checkinginfo/rotate \
  -H "Cookie: session=<cookie-de-sessao-admin>"
```
