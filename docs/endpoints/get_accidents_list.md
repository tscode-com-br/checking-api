# `GET /api/admin/accidents`

## Visão Geral

Lista todos os acidentes encerrados em ordem decrescente de número de acidente. Não inclui o acidente ativo (se houver).

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `GET`                                               |
| **Path**          | `/api/admin/accidents`                              |
| **Autenticação**  | Sessão admin nível completo                         |
| **Formato**       | `application/json`                                  |

---

## Autenticação

Requer sessão admin com nível completo. Sem sessão ou com sessão básica, retorna `401`.

---

## Parâmetros

Nenhum parâmetro de query ou body.

---

## Resposta (200)

```json
{
  "rows": [
    {
      "id": 7,
      "accident_number_label": "0003",
      "project_name": "PROJETO ALFA",
      "author_label": "João Admin",
      "opened_at": "2026-05-15T09:30:00+08:00",
      "closed_at": "2026-05-15T11:45:00+08:00",
      "download_url": "/api/admin/accidents/7/archive",
      "download_ready": true,
      "can_delete": false
    },
    {
      "id": 3,
      "accident_number_label": "0002",
      "project_name": "PROJETO BETA",
      "author_label": "Ana Usuária",
      "opened_at": "2026-04-20T14:00:00+08:00",
      "closed_at": "2026-04-20T15:30:00+08:00",
      "download_url": "/api/admin/accidents/3/archive",
      "download_ready": false,
      "can_delete": false
    }
  ]
}
```

### Campos de `rows[*]`

| Campo                   | Tipo               | Descrição                                                         |
|-------------------------|--------------------|-------------------------------------------------------------------|
| `id`                    | `integer`          | ID interno do acidente                                            |
| `accident_number_label` | `string`           | Número formatado com 4 dígitos, ex: `"0003"`                      |
| `project_name`          | `string`           | Nome do projeto no momento da abertura                            |
| `author_label`          | `string`           | Nome do admin ou usuário que abriu o acidente                     |
| `opened_at`             | `string` (ISO 8601)| Data/hora de abertura                                             |
| `closed_at`             | `string` (ISO 8601)| Data/hora de encerramento                                         |
| `download_url`          | `string`           | Path relativo para download do archive ZIP                        |
| `download_ready`        | `boolean`          | `true` quando o ZIP já foi gerado e está disponível para download |
| `can_delete`            | `boolean`          | `true` apenas para admins com `perfil=9`                          |

---

## Códigos de status HTTP

| Código | Significado                                         |
|--------|-----------------------------------------------------|
| `200`  | Sucesso (lista pode estar vazia)                    |
| `401`  | Sessão ausente, expirada ou insuficiente            |

---

## Side effects

Nenhum. Endpoint somente de leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: session_id=<sua_sessao_admin>" \
  http://127.0.0.1:8000/api/admin/accidents \
  | python3 -m json.tool
```
