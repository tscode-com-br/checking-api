# `GET /api/admin/events/archives/download-all`

## Visão Geral

Baixa todos os archives de eventos históricos disponíveis no servidor empacotados em um único arquivo ZIP. Útil para backup consolidado ou migração.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `GET`                                   |
| **Path**         | `/api/admin/events/archives/download-all` |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | `application/zip` (resposta)            |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

Nenhum.

---

## Resposta

**HTTP 200 — Sucesso**

Arquivo ZIP binário com todos os CSVs de archives presentes no servidor.

| Header                       | Valor                                                    |
|------------------------------|----------------------------------------------------------|
| `Content-Type`               | `application/zip`                                        |
| `Content-Disposition`        | `attachment; filename="all_event_archives_YYYYMMDD.zip"` |

O ZIP contém um arquivo CSV por archive gerado previamente. Cada CSV segue o formato padrão dos archives de eventos (colunas de `check_events` serializadas).

**HTTP 404 — Nenhum archive disponível**

```json
{
  "detail": "No archived event logs found"
}
```

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso. Arquivo ZIP retornado como stream binário.                  |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |
| `404`  | Nenhum archive de eventos encontrado no servidor.                    |

---

## Side effects

- **Grava** um evento em `check_events` com `action="event_archive"` e `status="downloaded"` (ou `"failed"` em caso de 404), contendo o `chave` do administrador no campo `details`.

---

## Exemplo cURL (ambiente local)

```bash
# Baixar todos os archives em um único ZIP
curl -s -b cookies.txt \
  -o todos_os_archives.zip \
  http://127.0.0.1:8000/api/admin/events/archives/download-all
```
