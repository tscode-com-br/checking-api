# `GET /api/web/check/accident/state`

## Visão Geral

Retorna o estado do Modo Acidente do ponto de vista do usuário autenticado no Check Web. Se há um acidente ativo, inclui o relatório atual do usuário (zona e status informados).

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `GET`                                               |
| **Path**          | `/api/web/check/accident/state`                     |
| **Autenticação**  | Sessão web (cookie `web_session_id`) + parâmetro `chave` |
| **Formato**       | `application/json`                                  |

---

## Autenticação

Requer sessão web válida associada ao `chave` informado. O `chave` deve coincidir com o usuário da sessão ativa.

---

## Parâmetros de Query

| Parâmetro | Tipo     | Obrigatório | Descrição                                    |
|-----------|----------|-------------|----------------------------------------------|
| `chave`   | `string` | ✅           | Código de 4 caracteres alfanuméricos do usuário |

---

## Resposta

### Sem acidente ativo

```json
{
  "is_active": false,
  "accident_number_label": null,
  "project_name": null,
  "location_name": null,
  "current_user_report": null
}
```

### Com acidente ativo, usuário sem relatório

```json
{
  "is_active": true,
  "accident_number_label": "0004",
  "project_name": "PROJETO ALFA",
  "location_name": "Bloco C",
  "current_user_report": null
}
```

### Com acidente ativo, usuário com relatório

```json
{
  "is_active": true,
  "accident_number_label": "0004",
  "project_name": "PROJETO ALFA",
  "location_name": "Bloco C",
  "current_user_report": {
    "zone": "safety",
    "status": "ok",
    "reported_at": "2026-05-18T09:35:00+08:00"
  }
}
```

### Campos da resposta

| Campo                   | Tipo                             | Descrição                                        |
|-------------------------|----------------------------------|--------------------------------------------------|
| `is_active`             | `boolean`                        | Se há acidente em curso                          |
| `accident_number_label` | `string` \| `null`               | Número formatado, ex: `"0004"`                   |
| `project_name`          | `string` \| `null`               | Projeto do acidente                              |
| `location_name`         | `string` \| `null`               | Local do acidente                                |
| `current_user_report`   | `object` \| `null`               | Relatório do usuário para este acidente          |
| └ `zone`                | `"safety"` \| `"accident"` \| `null` | Zona informada pelo usuário                 |
| └ `status`              | `"ok"` \| `"help"` \| `null`    | Status informado pelo usuário                    |
| └ `reported_at`         | `string` (ISO 8601) \| `null`    | Quando o relatório foi enviado                   |

---

## Códigos de status HTTP

| Código | Significado                                         |
|--------|-----------------------------------------------------|
| `200`  | Sucesso                                             |
| `401`  | Sessão ausente, expirada, ou `chave` não coincide   |
| `422`  | `chave` ausente ou fora do formato (≠ 4 chars)      |

---

## Side effects

Nenhum. Endpoint somente de leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: web_session_id=<sua_sessao_web>" \
  "http://127.0.0.1:8000/api/web/check/accident/state?chave=APF1" \
  | python3 -m json.tool
```
