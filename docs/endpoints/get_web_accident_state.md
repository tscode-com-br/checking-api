# `GET /api/web/check/accident/state`

## Visão Geral

Retorna o estado atual do Modo Acidente do ponto de vista do usuário autenticado. Indica se há um ou mais acidentes ativos, qual é o status de awareness do usuário (se já reconheceu o acidente), e qual é o relatório de situação já enviado (zona e status de segurança).

O endpoint prioriza acidentes cujo projeto pertença aos projetos cadastrados do usuário. Caso nenhum acidente corresponda ao projeto do usuário, retorna todos os acidentes ativos (comportamento legado de fallback global).

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/web/check/accident/state`                |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O valor do cookie deve coincidir com o parâmetro `chave`. Em caso de falha retorna `401`.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo   | Obrigatório | Descrição                                                    |
|-----------|--------|-------------|--------------------------------------------------------------|
| `chave`   | string | Sim         | Chave do usuário (4 caracteres alfanuméricos, ex.: `"AB12"`) |

---

## Resposta

### Sem acidente ativo

```json
{
  "is_active": false,
  "accident_id": null,
  "accident_number_label": null,
  "project_id": null,
  "project_name": null,
  "location_name": null,
  "description": null,
  "awareness_status": null,
  "current_user_report": null,
  "active_accidents": []
}
```

### Com acidente ativo

```json
{
  "is_active": true,
  "accident_id": 5,
  "accident_number_label": "ACC-0005",
  "project_id": 3,
  "project_name": "Projeto Norte",
  "location_name": "Área de Extração B",
  "description": "Acidente com equipamento pesado na via principal.",
  "awareness_status": "acknowledged",
  "current_user_report": {
    "zone": "safety",
    "status": "ok",
    "reported_at": "2026-05-25T14:32:10+08:00"
  },
  "active_accidents": [
    {
      "accident_id": 5,
      "accident_number_label": "ACC-0005",
      "project_id": 3,
      "project_name": "Projeto Norte",
      "location_name": "Área de Extração B",
      "description": "Acidente com equipamento pesado na via principal.",
      "awareness_status": "acknowledged",
      "current_user_report": {
        "zone": "safety",
        "status": "ok",
        "reported_at": "2026-05-25T14:32:10+08:00"
      }
    }
  ]
}
```

### Campos da resposta

| Campo                  | Tipo                       | Descrição                                                                             |
|------------------------|----------------------------|---------------------------------------------------------------------------------------|
| `is_active`            | bool                       | `true` se há ao menos um acidente ativo relevante para o usuário                     |
| `accident_id`          | int \| null                | ID do primeiro acidente ativo (compatibilidade com clientes legados)                  |
| `accident_number_label`| string \| null             | Número formatado do primeiro acidente (ex.: `"ACC-0005"`)                            |
| `project_id`           | int \| null                | ID do projeto do primeiro acidente                                                    |
| `project_name`         | string \| null             | Nome do projeto                                                                       |
| `location_name`        | string \| null             | Nome do local do acidente                                                             |
| `description`          | string \| null             | Descrição textual do acidente                                                         |
| `awareness_status`     | `"waiting"` \| `"acknowledged"` \| null | Status de awareness do usuário no primeiro acidente                   |
| `current_user_report`  | objeto \| null             | Relatório de situação já enviado pelo usuário (ver abaixo)                            |
| `active_accidents`     | array                      | Lista de todos os acidentes ativos relevantes ao usuário (um objeto por acidente)     |

### Campos de `current_user_report`

| Campo         | Tipo                              | Descrição                                                               |
|---------------|-----------------------------------|-------------------------------------------------------------------------|
| `zone`        | `"safety"` \| `"accident"` \| null | Zona onde o usuário está (`null` se ainda não reportou)                |
| `status`      | `"ok"` \| `"help"` \| null        | Status de segurança do usuário (`null` se ainda não reportou)          |
| `reported_at` | datetime \| null                  | Timestamp do último reporte (ISO 8601)                                 |

### Valores de `awareness_status`

| Valor          | Significado                                                   |
|----------------|---------------------------------------------------------------|
| `"waiting"`    | Usuário ainda não reconheceu o acidente (padrão inicial)      |
| `"acknowledged"` | Usuário já clicou em "Ciente" no app                        |

---

## Códigos de status HTTP

| Código | Significado                                       |
|--------|---------------------------------------------------|
| `200`  | Estado retornado com sucesso                      |
| `401`  | Sessão inválida ou expirada, ou chave não confere |
| `422`  | Parâmetro `chave` inválido                        |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/web/check/accident/state?chave=AB12"
```
