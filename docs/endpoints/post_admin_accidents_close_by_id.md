# `POST /api/admin/accidents/{accident_id}/close`

## Visão Geral

Encerra um acidente específico pelo seu ID. Versão preferida em relação ao endpoint genérico `/accidents/close`, pois opera de forma explícita e evita ambiguidade quando múltiplos acidentes coexistem.

| Atributo         | Valor                                              |
|------------------|----------------------------------------------------|
| **Método**       | `POST`                                             |
| **Path**         | `/api/admin/accidents/{accident_id}/close`         |
| **Autenticação** | Sessão admin com identidade completa (`require_admin_identity`) |
| **Content-Type** | Nenhum (sem corpo)                                 |

---

## Autenticação

Requer `require_admin_identity`. Apenas administradores autenticados podem encerrar acidentes.

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo      | Descrição                       |
|---------------|-----------|---------------------------------|
| `accident_id` | `integer` | ID do acidente a ser encerrado. |

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

| Código | Significado                                                             |
|--------|-------------------------------------------------------------------------|
| `200`  | Acidente encerrado com sucesso.                                         |
| `401`  | Sessão ausente ou inválida.                                             |
| `409`  | Acidente não encontrado (`accident_id` inexistente) ou já encerrado.   |

---

## Side effects

- Define `accidents.closed_at` com o timestamp atual e `closed_by_admin_id` com o ID do admin.
- Dispara em background a geração do arquivo ZIP + XLSX de archive (`build_and_attach_archive_for_accident`).
- Grava evento em `check_events` com `action="accident_close"` e `source="admin"`.
- Notifica painel admin e Check Web via SSE.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/accidents/5/close
```
