# `GET /api/partner/admin/endpoint-keys`

## Visão Geral

Lista todas as chaves de API de endpoints configuradas no sistema, incluindo os valores das chaves secretas. Destinado a administradores com `perfil=9` para gerenciar as credenciais de acesso dos sistemas parceiros.

| Atributo         | Valor                                         |
|------------------|-----------------------------------------------|
| **Método**       | `GET`                                         |
| **Path**         | `/api/partner/admin/endpoint-keys`            |
| **Autenticação** | Sessão administrativa com `perfil=9` (cookie) |
| **Tags**         | `partner`                                     |

---

## Autenticação

Requer sessão administrativa válida no cookie de sessão (`session` ou similar). O usuário deve ter:
- Acesso administrativo (`perfil` >= 1 ou conforme `user_has_admin_access`)
- `perfil == 9` (administrador de endpoints parceiros)

### Resposta em caso de falha de autenticação

**Sem sessão ou sessão expirada:**
```json
{
  "detail": "Sessao administrativa invalida ou expirada"
}
```

**Sessão válida mas sem permissão administrativa:**
```json
{
  "detail": "Este usuario nao possui permissao para esta area do Admin."
}
```

**Sessão administrativa válida mas perfil diferente de 9:**
```json
{
  "detail": "Apenas administradores com perfil 9 podem gerenciar chaves de endpoints."
}
```

---

## Parâmetros

Nenhum parâmetro.

---

## Resposta

### 200 OK

```json
[
  {
    "id": 1,
    "endpoint_name": "checkinginfo",
    "secret_key": "a1b2c3d4e5f67890a1b2c3d4e5f67890",
    "created_at": "2024-01-15T10:00:00+08:00",
    "updated_at": "2024-05-20T14:30:00+08:00"
  }
]
```

Lista de objetos `EndpointApiKeyRow`:

| Campo           | Tipo       | Descrição                                         |
|-----------------|------------|---------------------------------------------------|
| `id`            | `integer`  | Identificador interno da chave                    |
| `endpoint_name` | `string`   | Nome do endpoint (ex.: `"checkinginfo"`)          |
| `secret_key`    | `string`   | Chave secreta em texto claro (32 caracteres hex)  |
| `created_at`    | `datetime` | Data/hora de criação do registro                  |
| `updated_at`    | `datetime` | Data/hora da última rotação da chave              |

> **Atenção**: a `secret_key` é retornada em texto claro. Trafegar este endpoint apenas em conexões HTTPS em produção.

---

## Códigos de status HTTP

| Código | Significado                                               |
|--------|-----------------------------------------------------------|
| `200`  | Sucesso — lista retornada (pode ser lista vazia `[]`)     |
| `401`  | Sessão ausente ou expirada                                |
| `403`  | Usuário sem permissão (sem acesso admin ou perfil != 9)   |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s http://127.0.0.1:8000/api/partner/admin/endpoint-keys \
  -H "Cookie: session=<cookie-de-sessao-admin>"
```
