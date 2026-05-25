# `GET /api/admin/pending`

## Visão Geral

Retorna a lista de registros pendentes de cadastro — cartões RFID que foram apresentados a um leitor ESP32 mas cujo proprietário ainda não foi cadastrado no sistema. Esses registros ficam em fila até serem cadastrados (via `POST /api/admin/users`) ou descartados (via `DELETE /api/admin/pending/{pending_id}`).

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/pending`                           |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Array de objetos `PendingRow` ordenados por `last_seen_at` decrescente (mais recente primeiro). A lista é filtrada pelo escopo de projetos do administrador — apenas pendências detectadas em localizações vinculadas aos projetos do admin são exibidas.

```json
[
  {
    "id": 7,
    "rfid": "D4E5F6A7",
    "first_seen_at": "2025-05-20T09:10:00+00:00",
    "last_seen_at": "2025-05-25T07:45:00+00:00",
    "attempts": 12
  }
]
```

### Campos da resposta

| Campo            | Tipo       | Descrição                                                                   |
|------------------|------------|-----------------------------------------------------------------------------|
| `id`             | `integer`  | ID do registro pendente                                                     |
| `rfid`           | `string`   | Código RFID do cartão apresentado sem cadastro                              |
| `first_seen_at`  | `datetime` | Primeira vez que o RFID foi detectado (UTC)                                 |
| `last_seen_at`   | `datetime` | Última vez que o RFID foi detectado (UTC)                                   |
| `attempts`       | `integer`  | Número total de vezes que o RFID foi apresentado sem sucesso de check-in    |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia)         |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |

---

## Side effects

Nenhum. Este endpoint é somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/pending
```
