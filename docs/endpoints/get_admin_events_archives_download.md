# `GET /api/admin/events/archives/{file_name}`

## Visão Geral

Baixa um arquivo CSV de archive de eventos específico, identificado pelo seu nome de arquivo. O nome é obtido a partir do campo `file_name` retornado pela listagem de archives (`GET /api/admin/events/archives`) ou pela resposta de criação (`POST /api/admin/events/archive`).

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/events/archives/{file_name}`       |
| **Autenticação** | Sessão administrativa completa (cookie)        |
| **Content-Type** | `text/csv` (resposta)                          |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

### Path Parameters

| Parâmetro   | Tipo     | Descrição                                                                   |
|-------------|----------|-----------------------------------------------------------------------------|
| `file_name` | `string` | Nome exato do arquivo CSV (ex.: `events_2026-01-01_to_2026-05-24.csv`). Obtido via `GET /api/admin/events/archives`. |

---

## Resposta

**HTTP 200 — Sucesso**

Arquivo CSV binário com os eventos do período arquivado.

| Header                | Valor                                                       |
|-----------------------|-------------------------------------------------------------|
| `Content-Type`        | `text/csv`                                                  |
| `Content-Disposition` | `attachment; filename="events_2026-01-01_to_2026-05-24.csv"` |

O CSV contém uma linha de cabeçalho e uma linha por evento arquivado, cobrindo os campos da tabela `check_events`.

**HTTP 404 — Arquivo não encontrado**

```json
{
  "detail": "Archived event log not found"
}
```

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso. Arquivo CSV retornado como stream.                          |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |
| `404`  | Arquivo de archive com o nome informado não existe no servidor.      |

---

## Side effects

- **Grava** um evento em `check_events` com `action="event_archive"` e `status="downloaded"` (ou `"failed"` em caso de 404), contendo `file_name` e `chave` do administrador no campo `details`.

---

## Exemplo cURL (ambiente local)

```bash
# Baixar um archive específico pelo nome do arquivo
curl -s -b cookies.txt \
  -o eventos_jan_mai_2026.csv \
  "http://127.0.0.1:8000/api/admin/events/archives/events_2026-01-01_to_2026-05-24.csv"
```
