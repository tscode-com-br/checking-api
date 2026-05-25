# `POST /api/admin/events/archive`

## Visão Geral

Arquiva todos os eventos atuais da tabela `check_events` em um arquivo CSV compactado no servidor, apaga os registros da tabela e retorna os metadados do archive criado junto com a lista atualizada de archives disponíveis. Eventos do tipo `event_archive` (auto-registros do processo de arquivamento) são expurgados sem ser incluídos no arquivo.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `POST`                                  |
| **Path**         | `/api/admin/events/archive`             |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | — (sem corpo de requisição)             |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

Nenhum. O endpoint não aceita corpo de requisição nem query parameters.

---

## Resposta

**HTTP 200 — Sucesso (archive criado)**

```json
{
  "created": true,
  "cleared_count": 3842,
  "archive": {
    "file_name": "events_2026-01-01_to_2026-05-24.csv",
    "period": "2026-01-01 a 2026-05-24",
    "record_count": 3842,
    "size_bytes": 512048,
    "created_at": "2026-05-25T02:00:00Z"
  },
  "archives": {
    "items": [
      {
        "file_name": "events_2026-01-01_to_2026-05-24.csv",
        "period": "2026-01-01 a 2026-05-24",
        "record_count": 3842,
        "size_bytes": 512048,
        "created_at": "2026-05-25T02:00:00Z"
      }
    ],
    "total": 1,
    "total_size_bytes": 512048,
    "page": 1,
    "page_size": 8,
    "total_pages": 1,
    "query": ""
  }
}
```

**HTTP 200 — Sem eventos para arquivar (noop)**

```json
{
  "created": false,
  "cleared_count": 0,
  "archive": null,
  "archives": {
    "items": [],
    "total": 0,
    "total_size_bytes": 0,
    "page": 1,
    "page_size": 8,
    "total_pages": 1,
    "query": ""
  }
}
```

### Campos da resposta

| Campo           | Tipo                         | Descrição                                                                     |
|-----------------|------------------------------|-------------------------------------------------------------------------------|
| `created`       | `boolean`                    | `true` se um arquivo foi gerado; `false` se não havia eventos a arquivar.     |
| `cleared_count` | `integer`                    | Quantidade de eventos removidos da tabela `check_events`.                     |
| `archive`       | `EventArchiveRow \| null`    | Metadados do arquivo criado, ou `null` se nenhum arquivo foi gerado.          |
| `archives`      | `EventArchiveListResponse`   | Lista paginada (primeira página) de todos os archives disponíveis no servidor.|

### Campos de `EventArchiveRow`

| Campo          | Tipo       | Descrição                                             |
|----------------|------------|-------------------------------------------------------|
| `file_name`    | `string`   | Nome do arquivo CSV (usado como chave para download). |
| `period`       | `string`   | Período coberto pelo arquivo (rótulo legível).        |
| `record_count` | `integer`  | Total de eventos incluídos no arquivo.                |
| `size_bytes`   | `integer`  | Tamanho do arquivo em bytes.                          |
| `created_at`   | `datetime` | Timestamp ISO 8601 de criação do arquivo.             |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso (com ou sem arquivo gerado — verificar o campo `created`).  |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

- **Apaga** todos os registros de `check_events` (exceto `action="event_archive"` que já é filtrado) após o arquivo ser gerado.
- **Grava** um novo evento em `check_events` com `action="event_archive"` e `status="created"` (ou `"noop"` se não havia dados), contendo os metadados do archive no campo `details`.
- O arquivo CSV fica armazenado no servidor e pode ser baixado via `GET /api/admin/events/archives/{file_name}`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/events/archive
```
