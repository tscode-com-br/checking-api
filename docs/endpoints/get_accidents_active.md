# `GET /api/admin/accidents/active`

## Visão Geral

Retorna o estado atual do Modo Acidente: se há um acidente ativo, devolve os dados do acidente e a tabela de situação de todos os usuários vinculados.

| Atributo          | Valor                                             |
|-------------------|---------------------------------------------------|
| **Método**        | `GET`                                             |
| **Path**          | `/api/admin/accidents/active`                     |
| **Autenticação**  | Sessão admin (cookie `session_id`)                |
| **Formato**       | `application/json`                                |

---

## Autenticação

Requer sessão admin válida (qualquer nível). Sem sessão ativa, retorna `401`.

---

## Parâmetros

Nenhum parâmetro de query ou body.

---

## Resposta

### Sem acidente ativo (`is_active=false`)

```json
{
  "is_active": false,
  "accident": null,
  "situation_rows": []
}
```

### Com acidente ativo

```json
{
  "is_active": true,
  "accident": {
    "id": 7,
    "accident_number": 3,
    "accident_number_label": "0003",
    "project_name": "PROJETO ALFA",
    "location_name": "Bloco C",
    "location_is_registered": true,
    "origin": "admin",
    "opened_by_label": "João Admin",
    "opened_at": "2026-05-18T09:30:00+08:00",
    "closed_at": null
  },
  "situation_rows": [
    {
      "user_id": 42,
      "event_time": "2026-05-18T09:31:05+08:00",
      "name": "Ana Paula",
      "chave": "APF1",
      "projects": ["PROJETO ALFA"],
      "local": "co83",
      "zone": "Segurança",
      "status": "OK",
      "phone": "+55 11 91234-5678",
      "videos": [],
      "priority": 4,
      "row_color": "light-green"
    },
    {
      "user_id": 55,
      "event_time": "2026-05-18T09:32:10+08:00",
      "name": "Carlos Lima",
      "chave": "CEL2",
      "projects": ["PROJETO ALFA"],
      "local": null,
      "zone": "Acidente",
      "status": "AJUDA",
      "phone": null,
      "videos": [
        {
          "video_id": 3,
          "public_url": "https://cdn.example.com/accidents/0003/CEL2/clip.webm",
          "captured_at": "2026-05-18T09:31:50+08:00",
          "content_type": "video/webm",
          "size_bytes": 2048000
        }
      ],
      "priority": 1,
      "row_color": "blinking-red"
    }
  ]
}
```

### Campos de `accident`

| Campo                    | Tipo                       | Descrição                                         |
|--------------------------|----------------------------|---------------------------------------------------|
| `id`                     | `integer`                  | ID interno do acidente                            |
| `accident_number`        | `integer`                  | Número sequencial (≥ 0)                           |
| `accident_number_label`  | `string`                   | Número formatado com 4 dígitos, ex: `"0003"`      |
| `project_name`           | `string`                   | Nome do projeto no momento da abertura            |
| `location_name`          | `string`                   | Nome do local (registrado ou livre)               |
| `location_is_registered` | `boolean`                  | `true` se o local é um `ManagedLocation`          |
| `origin`                 | `"admin"` \| `"web"`       | Quem abriu o acidente                             |
| `opened_by_label`        | `string`                   | Nome do admin ou usuário que abriu                |
| `opened_at`              | `string` (ISO 8601)        | Data/hora de abertura                             |
| `closed_at`              | `string` \| `null`         | Data/hora de encerramento (null se ativo)         |

### Campos de `situation_rows[*]`

| Campo        | Tipo                                               | Descrição                                     |
|--------------|----------------------------------------------------|-----------------------------------------------|
| `user_id`    | `integer`                                          | ID do usuário                                 |
| `event_time` | `string` (ISO 8601)                                | Última atualização do relatório               |
| `name`       | `string`                                           | Nome do usuário                               |
| `chave`      | `string`                                           | Código único de 4 chars                       |
| `projects`   | `string[]`                                         | Projetos do usuário (snapshot)                |
| `local`      | `string` \| `null`                                 | Local do último check-in                      |
| `zone`       | `"Aguardando"` \| `"Segurança"` \| `"Acidente"`    | Zona informada pelo usuário                   |
| `status`     | `"Aguardando"` \| `"OK"` \| `"AJUDA"`              | Status informado pelo usuário                 |
| `phone`      | `string` \| `null`                                 | Telefone (snapshot)                           |
| `videos`     | `AccidentVideoLink[]`                              | Vídeos enviados por este usuário              |
| `priority`   | `integer` (1–5)                                    | Prioridade de exibição (1 = mais urgente)     |
| `row_color`  | `string`                                           | Cor de destaque para a UI                     |

---

## Códigos de status HTTP

| Código | Significado                                         |
|--------|-----------------------------------------------------|
| `200`  | Sucesso                                             |
| `401`  | Sessão ausente ou expirada                          |

---

## Side effects

Nenhum. Endpoint somente de leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: session_id=<sua_sessao_admin>" \
  http://127.0.0.1:8000/api/admin/accidents/active \
  | python3 -m json.tool
```
