# `GET /api/admin/forms`

## Visão Geral

Retorna a lista de registros de formulários enviados por providers externos (ex.: integrações de terceiros via `POST /api/provider/updaterecords`) que ainda estão na fila de processamento ou foram recentemente processados. Cada item representa um evento de check-in ou check-out pendente de sincronização na tabela `user_sync_events` com `source="provider"`.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `GET`                                   |
| **Path**         | `/api/admin/forms`                      |
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

Nenhum. A listagem retorna todos os registros de formulários visíveis ao administrador, ordenados por `id` decrescente (mais recentes primeiro), filtrados pelo escopo de projetos do admin.

---

## Resposta

**HTTP 200 — Sucesso**

Array de objetos `ProviderFormRow`.

```json
[
  {
    "recebimento": "2026-05-25T07:45:00Z",
    "recebimento_date_label": "25/05/2026",
    "recebimento_time_label": "07:45:00",
    "chave": "AB12",
    "nome": "João Silva",
    "projeto": "PROJ-A",
    "timezone_name": "Asia/Singapore",
    "timezone_label": "SGT (UTC+8)",
    "atividade": "check-in",
    "informe": "normal",
    "data": "25/05/2026",
    "hora": "07:30:00"
  }
]
```

| Campo                    | Tipo                          | Descrição                                                                     |
|--------------------------|-------------------------------|-------------------------------------------------------------------------------|
| `recebimento`            | `datetime \| null`            | Timestamp UTC em que o formulário foi recebido pelo sistema. `null` se o admin não tem permissão de ver horários. |
| `recebimento_date_label` | `string`                      | Data de recebimento formatada `DD/MM/YYYY` no fuso do projeto.                |
| `recebimento_time_label` | `string \| null`              | Horário de recebimento `HH:MM:SS`. `null` para admins sem permissão.          |
| `chave`                  | `string`                      | Chave de 4 caracteres do usuário que submeteu o formulário.                   |
| `nome`                   | `string`                      | Nome do usuário (resolvido via `users.nome`, ou vazio se não encontrado).     |
| `projeto`                | `string`                      | Projeto do usuário.                                                           |
| `timezone_name`          | `string`                      | Nome IANA do fuso horário do projeto.                                         |
| `timezone_label`         | `string`                      | Rótulo legível do fuso.                                                       |
| `atividade`              | `"check-in" \| "check-out"`   | Tipo de atividade declarada no formulário.                                    |
| `informe`                | `"normal" \| "retroativo"`    | Indica se o horário é do momento do envio (`normal`) ou retroativo.           |
| `data`                   | `string`                      | Data do evento declarada no formulário, `DD/MM/YYYY`.                         |
| `hora`                   | `string \| null`              | Horário do evento declarado, `HH:MM:SS`. `null` se não disponível.           |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso. Array retornado (pode ser vazio `[]`).                      |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/forms
```
