# `GET /api/admin/events/archives`

## Visão Geral

Retorna a lista paginada de archives de eventos históricos disponíveis no servidor. Cada archive é um arquivo CSV gerado por `POST /api/admin/events/archive`, representando um snapshot dos eventos de `check_events` de um determinado período.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `GET`                                   |
| **Path**         | `/api/admin/events/archives`            |
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

### Query Parameters

| Parâmetro   | Tipo      | Obrigatório | Padrão | Descrição                                                        |
|-------------|-----------|-------------|--------|------------------------------------------------------------------|
| `q`         | `string`  | Não         | `""`   | Filtro textual por nome de arquivo ou período.                   |
| `page`      | `integer` | Não         | `1`    | Número da página (mínimo `1`).                                   |
| `page_size` | `integer` | Não         | `8`    | Registros por página (mínimo `1`, máximo `100`).                 |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "items": [
    {
      "file_name": "events_2026-01-01_to_2026-05-24.csv",
      "period": "2026-01-01 a 2026-05-24",
      "record_count": 3842,
      "size_bytes": 512048,
      "created_at": "2026-05-25T02:00:00Z"
    },
    {
      "file_name": "events_2025-07-01_to_2025-12-31.csv",
      "period": "2025-07-01 a 2025-12-31",
      "record_count": 7210,
      "size_bytes": 947312,
      "created_at": "2026-01-02T01:00:00Z"
    }
  ],
  "total": 2,
  "total_size_bytes": 1459360,
  "page": 1,
  "page_size": 8,
  "total_pages": 1,
  "query": ""
}
```

| Campo              | Tipo                    | Descrição                                                              |
|--------------------|-------------------------|------------------------------------------------------------------------|
| `items`            | `list[EventArchiveRow]` | Archives da página atual.                                              |
| `total`            | `integer`               | Total de archives disponíveis (considerando o filtro `q`).             |
| `total_size_bytes` | `integer`               | Soma do tamanho de todos os archives (em bytes).                       |
| `page`             | `integer`               | Página atual.                                                          |
| `page_size`        | `integer`               | Registros por página solicitados.                                      |
| `total_pages`      | `integer`               | Total de páginas.                                                      |
| `query`            | `string`                | Filtro textual aplicado (mesmo valor do parâmetro `q`).                |

### Campos de `EventArchiveRow`

| Campo          | Tipo       | Descrição                                                    |
|----------------|------------|--------------------------------------------------------------|
| `file_name`    | `string`   | Nome do arquivo CSV (chave para download e exclusão).        |
| `period`       | `string`   | Período coberto (rótulo legível).                            |
| `record_count` | `integer`  | Total de eventos no arquivo.                                 |
| `size_bytes`   | `integer`  | Tamanho do arquivo em bytes.                                 |
| `created_at`   | `datetime` | Timestamp ISO 8601 UTC de criação.                           |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso. Lista retornada (pode ter `items: []` se não houver archives). |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
# Listar todos os archives (primeira página, sem filtro)
curl -s -b cookies.txt "http://127.0.0.1:8000/api/admin/events/archives"

# Filtrar por nome e navegar para página 2
curl -s -b cookies.txt "http://127.0.0.1:8000/api/admin/events/archives?q=2025&page=2&page_size=10"
```
