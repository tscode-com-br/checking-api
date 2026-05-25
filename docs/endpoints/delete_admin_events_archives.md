# `DELETE /api/admin/events/archives/{file_name}`

## Visão Geral

Remove permanentemente um arquivo CSV de archive de eventos do servidor, identificado pelo seu nome. Operação irreversível — o arquivo é excluído do sistema de arquivos e não pode ser recuperado.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `DELETE`                                       |
| **Path**         | `/api/admin/events/archives/{file_name}`       |
| **Autenticação** | Sessão administrativa completa (cookie)        |
| **Content-Type** | —                                              |

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
| `file_name` | `string` | Nome exato do arquivo CSV a remover (ex.: `events_2025-07-01_to_2025-12-31.csv`). Obtido via `GET /api/admin/events/archives`. |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "file_name": "events_2025-07-01_to_2025-12-31.csv"
}
```

| Campo       | Tipo      | Descrição                                    |
|-------------|-----------|----------------------------------------------|
| `ok`        | `boolean` | Sempre `true` em caso de exclusão bem-sucedida. |
| `file_name` | `string`  | Nome do arquivo removido (eco do parâmetro). |

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
| `200`  | Sucesso. Arquivo removido permanentemente.                           |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |
| `404`  | Arquivo de archive com o nome informado não existe no servidor.      |

---

## Side effects

- **Exclui** o arquivo CSV do sistema de arquivos do servidor. Ação irreversível.
- **Grava** um evento em `check_events` com `action="event_archive"` e `status="removed"` (ou `"failed"` em caso de 404), contendo `file_name` e `chave` do administrador no campo `details`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X DELETE \
  "http://127.0.0.1:8000/api/admin/events/archives/events_2025-07-01_to_2025-12-31.csv"
```
