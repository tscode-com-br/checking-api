# `POST /api/admin/accidents/open`

## Visão Geral

Abre um novo acidente pelo admin. Apenas um acidente pode estar ativo por vez. O admin deve selecionar projeto e local (registrado ou nome livre).

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `POST`                                              |
| **Path**          | `/api/admin/accidents/open`                         |
| **Autenticação**  | Sessão admin nível completo (`require_full_admin_session`) |
| **Content-Type**  | `application/json`                                  |
| **Formato**       | `application/json`                                  |

---

## Autenticação

Requer sessão admin com nível completo (admin verificado com senha). Sem sessão ou com sessão básica, retorna `401`.

---

## Request Body

```json
{
  "project_id": 5,
  "location_id": 12,
  "custom_location_name": null
}
```

| Campo                  | Tipo              | Obrigatório | Descrição                                                      |
|------------------------|-------------------|-------------|----------------------------------------------------------------|
| `project_id`           | `integer`         | ✅           | ID do projeto onde ocorreu o acidente                          |
| `location_id`          | `integer` \| `null` | ✅*        | ID de um `ManagedLocation` já cadastrado                       |
| `custom_location_name` | `string` \| `null` | ✅*        | Nome livre de local (quando não é um local registrado)         |

> **Regra XOR:** Exatamente um de `location_id` ou `custom_location_name` deve ser fornecido — nunca os dois ao mesmo tempo, nem nenhum dos dois.

---

## Resposta (200)

Retorna o estado atual do acidente (idêntico a `GET /accidents/active` com `is_active=true`).

```json
{
  "is_active": true,
  "accident": {
    "id": 8,
    "accident_number": 4,
    "accident_number_label": "0004",
    "project_name": "PROJETO BETA",
    "location_name": "Área de Carga",
    "location_is_registered": false,
    "origin": "admin",
    "opened_by_label": "Maria Admin",
    "opened_at": "2026-05-18T10:00:00+08:00",
    "closed_at": null
  },
  "situation_rows": []
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                     |
|--------|---------------------------------------------------------------------------------|
| `200`  | Acidente aberto com sucesso                                                     |
| `401`  | Sessão ausente, expirada ou insuficiente                                        |
| `409`  | Já existe um acidente em curso (`"Ja existe um acidente em curso."`)            |
| `422`  | Validação falhou: `location_id` e `custom_location_name` ambos ausentes ou ambos preenchidos; ou `location_id` não pertence ao projeto selecionado |

### Exemplo de erro 409

```json
{ "detail": "Ja existe um acidente em curso." }
```

### Exemplo de erro 422 (local inválido)

```json
{ "detail": "O local selecionado nao pertence ao projeto." }
```

---

## Side effects

- `notify_admin_data_changed("accident_open")` — atualiza o painel admin via SSE (`checking_admin_updates`)
- `notify_web_check_data_changed("accident_open")` — notifica todos os Check Web via SSE (`checking_web_check_updates`)
- `log_event(action="accident_open", source="admin")` — grava evento na aba "Eventos" do admin

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: session_id=<sua_sessao_admin>" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 5, "location_id": null, "custom_location_name": "Entrada do Galpão"}' \
  http://127.0.0.1:8000/api/admin/accidents/open \
  | python3 -m json.tool
```
