# `GET /api/admin/reports/events`

## Visão Geral

Retorna o relatório de eventos de check-in e check-out de um usuário específico, identificado por `chave` ou `nome`. A resposta inclui os dados cadastrais da pessoa e a lista de eventos registrados no sistema de sincronização (`UserSyncEvent`), filtrados pelo escopo de projetos do administrador.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `GET`                                   |
| **Path**         | `/api/admin/reports/events`             |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | —                                       |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

### Query Parameters

Exatamente um dos parâmetros `chave` ou `nome` deve ser fornecido. Informar os dois simultaneamente resulta em `400`.

| Parâmetro | Tipo     | Obrigatório         | Descrição                                                         |
|-----------|----------|---------------------|-------------------------------------------------------------------|
| `chave`   | `string` | Condicional (`*`)   | Chave de 4 caracteres alfanuméricos do usuário (ex.: `AB12`). Convertida para maiúsculas internamente. |
| `nome`    | `string` | Condicional (`*`)   | Nome completo ou parcial do usuário. Busca por correspondência exata normalizada. |

`(*)` Informe `chave` **ou** `nome`, nunca os dois.

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "person": {
    "id": 42,
    "rfid": "04AB12CD",
    "nome": "João Silva",
    "chave": "AB12",
    "projeto": "PROJ-A",
    "projetos": ["PROJ-A", "PROJ-B"],
    "timezone_name": "Asia/Singapore",
    "timezone_label": "SGT (UTC+8)"
  },
  "events": [
    {
      "id": 1801,
      "source": "web",
      "source_label": "Aplicativo",
      "action": "checkin",
      "action_label": "Check-In",
      "projeto": "PROJ-A",
      "local": "main",
      "local_label": "Escritório Principal",
      "ontime": true,
      "assiduidade": "Normal",
      "event_time": "2026-05-25T08:30:00Z",
      "event_time_label": "08:30:00",
      "timezone_name": "Asia/Singapore",
      "timezone_label": "SGT (UTC+8)",
      "event_date": "25/05/2026"
    }
  ]
}
```

### Campos de `person` (ReportPersonRow)

| Campo           | Tipo             | Descrição                                            |
|-----------------|------------------|------------------------------------------------------|
| `id`            | `integer`        | ID do usuário na tabela `users`.                     |
| `rfid`          | `string \| null` | Código RFID da tag.                                  |
| `nome`          | `string`         | Nome completo do usuário.                            |
| `chave`         | `string`         | Chave de 4 caracteres.                               |
| `projeto`       | `string`         | Projeto principal ativo.                             |
| `projetos`      | `list[string]`   | Todos os projetos vinculados ao usuário.             |
| `timezone_name` | `string`         | Nome IANA do fuso horário do projeto.                |
| `timezone_label`| `string`         | Rótulo legível do fuso horário.                      |

### Campos de cada item em `events` (ReportEventRow)

| Campo             | Tipo              | Descrição                                                                 |
|-------------------|-------------------|---------------------------------------------------------------------------|
| `id`              | `integer`         | ID do evento na tabela `user_sync_events`.                                |
| `source`          | `string`          | Origem: `web`, `device`, `provider`.                                      |
| `source_label`    | `string`          | Rótulo legível da origem (ex.: `"Aplicativo"`, `"Box ESP32-0001"`, `"Forms"`). |
| `action`          | `"checkin" \| "checkout"` | Ação registrada.                                                |
| `action_label`    | `string`          | Rótulo legível da ação (ex.: `"Check-In"`, `"Check-Out"`).                |
| `projeto`         | `string`          | Projeto ao qual o evento pertence.                                        |
| `local`           | `string \| null`  | Código do local físico.                                                   |
| `local_label`     | `string`          | Rótulo legível do local (ex.: `"Escritório Principal"`).                  |
| `ontime`          | `boolean`         | `true` = evento no horário; `false` = retroativo.                         |
| `assiduidade`     | `"Normal" \| "Retroativo"` | Rótulo de assiduidade derivado de `ontime`.                    |
| `event_time`      | `datetime \| null`| Timestamp UTC. `null` para admins sem permissão de ver horários.          |
| `event_time_label`| `string \| null`  | Horário formatado `HH:MM:SS`. `null` para admins sem permissão.           |
| `timezone_name`   | `string`          | Nome IANA do fuso do projeto.                                             |
| `timezone_label`  | `string`          | Rótulo legível do fuso.                                                   |
| `event_date`      | `string`          | Data formatada `DD/MM/YYYY` no fuso do projeto.                           |

---

## Códigos de status HTTP

| Código | Significado                                                                       |
|--------|-----------------------------------------------------------------------------------|
| `200`  | Sucesso. Relatório retornado.                                                     |
| `400`  | Ambos `chave` e `nome` foram informados, ou nenhum foi fornecido.                 |
| `401`  | Sessão administrativa ausente ou expirada.                                        |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin, ou o usuário consultado está fora do escopo do admin. |
| `404`  | Nenhum usuário encontrado com a `chave` ou `nome` informados.                     |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
# Consultar por chave
curl -s -b cookies.txt "http://127.0.0.1:8000/api/admin/reports/events?chave=AB12"

# Consultar por nome
curl -s -b cookies.txt "http://127.0.0.1:8000/api/admin/reports/events?nome=Jo%C3%A3o%20Silva"
```
