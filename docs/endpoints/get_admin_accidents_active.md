# `GET /api/admin/accidents/active`

## Visão Geral

Retorna o estado atual do Modo Acidente: se há acidente ativo, e em caso positivo, os dados do acidente e a tabela de situação com todos os usuários reportados.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/accidents/active`                  |
| **Autenticação** | Sessão admin (qualquer nível de acesso)        |

---

## Autenticação

Requer sessão admin via cookie (`require_admin_session`). Qualquer administrador com sessão válida pode consultar o estado ativo, independente do escopo.

---

## Parâmetros

Nenhum.

---

## Resposta

**HTTP 200 — Sem acidente ativo**

```json
{
  "is_active": false,
  "active_accidents": [],
  "accident": null,
  "situation_rows": []
}
```

**HTTP 200 — Com acidente ativo**

```json
{
  "is_active": true,
  "active_accidents": [
    {
      "accident": {
        "id": 5,
        "accident_number": 42,
        "accident_number_label": "0042",
        "project_id": 3,
        "project_name": "P80",
        "location_name": "Plataforma Norte",
        "location_is_registered": true,
        "origin": "admin",
        "opened_by_label": "João da Silva",
        "opened_at": "2026-05-25T08:00:00Z",
        "closed_at": null,
        "description": "Colisão na plataforma"
      },
      "situation_rows": [
        {
          "user_id": 12,
          "event_time": "2026-05-25T08:05:00Z",
          "name": "Maria Souza",
          "chave": "CD34",
          "projects": ["P80"],
          "local": "Plataforma Norte",
          "activity_local": null,
          "zone": "Acidente",
          "status": "AJUDA",
          "phone": "+551199999999",
          "videos": [],
          "priority": 1,
          "section": 1,
          "awareness_status": "waiting",
          "row_color": "blinking-red"
        }
      ]
    }
  ],
  "accident": { "...": "mesmo objeto acima" },
  "situation_rows": [ "...mesmas linhas acima..." ]
}
```

### Campos de `accident`

| Campo                  | Tipo              | Descrição                                             |
|------------------------|-------------------|-------------------------------------------------------|
| `id`                   | `integer`         | ID do acidente.                                       |
| `accident_number`      | `integer`         | Número sequencial vitalício.                          |
| `accident_number_label`| `string`          | Número formatado com 4 dígitos (ex.: `"0042"`).       |
| `project_id`           | `integer`         | ID do projeto associado.                              |
| `project_name`         | `string`          | Snapshot do nome do projeto no momento de abertura.   |
| `location_name`        | `string`          | Nome do local (snapshot ou personalizado).            |
| `location_is_registered` | `boolean`       | Se o local é cadastrado no sistema.                   |
| `origin`               | `"admin"\|"web"`  | Quem abriu: painel admin ou Check Web.                |
| `opened_by_label`      | `string`          | Nome de quem abriu (admin ou usuário web).            |
| `opened_at`            | `datetime`        | ISO 8601 UTC de abertura.                             |
| `closed_at`            | `datetime\|null`  | Sempre `null` para acidentes ativos.                  |
| `description`          | `string`          | Descrição opcional do acidente.                       |

### Campos de `situation_rows`

| Campo              | Tipo                                          | Descrição                                                    |
|--------------------|-----------------------------------------------|--------------------------------------------------------------|
| `user_id`          | `integer`                                     | ID do usuário.                                               |
| `event_time`       | `datetime`                                    | Momento do último reporte.                                   |
| `name`             | `string`                                      | Nome do usuário.                                             |
| `chave`            | `string`                                      | Chave do usuário.                                            |
| `projects`         | `string[]`                                    | Projetos do usuário.                                         |
| `local`            | `string\|null`                                | Local atual do usuário (do check-in mais recente).           |
| `zone`             | `"Aguardando"\|"Segurança"\|"Acidente"`       | Zona reportada.                                              |
| `status`           | `"Aguardando"\|"OK"\|"AJUDA"`                 | Status de segurança.                                         |
| `phone`            | `string\|null`                                | Telefone para contato.                                       |
| `videos`           | `object[]`                                    | Vídeos enviados pelo usuário durante o acidente.             |
| `priority`         | `integer`                                     | Prioridade de exibição (1=mais urgente, 5=menos urgente).    |
| `section`          | `integer`                                     | Seção na tabela: 1=Emergência, 2=Local do Acidente, 3=Não Reportados, 4=Demais. |
| `awareness_status` | `string`                                      | Status de awareness do usuário.                              |
| `row_color`        | `string`                                      | Cor de fundo da linha na tabela de situação.                 |

---

## Códigos de status HTTP

| Código | Significado                              |
|--------|------------------------------------------|
| `200`  | Estado retornado com sucesso.            |
| `401`  | Sessão ausente ou inválida.              |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/accidents/active
```
