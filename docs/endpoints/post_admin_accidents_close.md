# `POST /api/admin/accidents/close`

## Visão Geral

Encerra o primeiro acidente ativo encontrado no sistema. Endpoint de compatibilidade retroativa — para novos clientes, prefira `POST /api/admin/accidents/{accident_id}/close` que opera por ID explícito.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `POST`                                  |
| **Path**         | `/api/admin/accidents/close`            |
| **Autenticação** | Sessão admin com identidade completa (`require_admin_identity`) |
| **Content-Type** | Nenhum (sem corpo)                      |

---

## Autenticação

Requer `require_admin_identity`. Apenas administradores autenticados podem encerrar acidentes.

---

## Parâmetros

Nenhum. Sem query parameters, path parameters ou request body.

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "is_active": false,
  "active_accidents": [],
  "accident": null,
  "situation_rows": []
}
```

---

## Códigos de status HTTP

| Código | Significado                                              |
|--------|----------------------------------------------------------|
| `200`  | Acidente encerrado com sucesso.                          |
| `401`  | Sessão ausente ou inválida.                              |
| `409`  | Nenhum acidente em curso para encerrar.                  |

---

## Side effects

- Define `accidents.closed_at` e `closed_by_admin_id` para o acidente ativo.
- Dispara em background a geração do arquivo ZIP de archive (`build_and_attach_archive_for_accident`).
- Grava evento em `check_events` com `action="accident_close"` e `source="admin"`.
- Notifica painel admin e Check Web via SSE.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/accidents/close
```
