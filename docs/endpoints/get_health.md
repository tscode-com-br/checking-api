# `GET /api/health`

## Visão Geral

Inspeção completa de saúde da aplicação, incluindo o componente `forms_worker`. Idêntico ao `GET /api/health/ready`, mas adiciona o status do worker de envio de formulários (Google Forms). Retorna HTTP 503 caso qualquer componente crítico esteja com falha. Degradação no `forms_worker` não impede a resposta `ready: true`, mas eleva o `overall_status` para `"degraded"`.

| Atributo         | Valor                                        |
|------------------|----------------------------------------------|
| **Método**       | `GET`                                        |
| **Path**         | `/api/health`                                |
| **Autenticação** | Nenhuma                                      |
| **Tags**         | `health`                                     |

---

## Autenticação

Endpoint público. Nenhuma autenticação é necessária.

---

## Parâmetros

Nenhum parâmetro.

---

## Resposta

### 200 OK — Aplicação pronta e saudável

```json
{
  "status": "ok",
  "app": "checking",
  "ready": true,
  "overall_status": "ok",
  "components": {
    "database": {
      "status": "ok",
      "detail": "database reachable"
    },
    "static_sites": {
      "status": "ok",
      "detail": "static sites ready: admin, user, transport"
    },
    "transport_ai_operational_readiness": {
      "status": "ok",
      "detail": "transport ai operational readiness approved"
    },
    "transport_ai_settings_encryption": {
      "status": "ok",
      "detail": "transport ai settings encryption ready"
    },
    "forms_worker": {
      "status": "ok",
      "detail": "forms worker healthy"
    }
  }
}
```

### 200 OK — Pronta mas degradada (forms_worker com problema)

```json
{
  "status": "ok",
  "app": "checking",
  "ready": true,
  "overall_status": "degraded",
  "components": {
    "database": { "status": "ok", "detail": "database reachable" },
    "static_sites": { "status": "ok", "detail": "static sites ready: admin, user, transport" },
    "transport_ai_operational_readiness": { "status": "disabled", "detail": "transport ai disabled" },
    "transport_ai_settings_encryption": { "status": "disabled", "detail": "transport ai disabled" },
    "forms_worker": {
      "status": "degraded",
      "detail": "forms worker stale: last heartbeat 420s ago"
    }
  }
}
```

### 503 Service Unavailable — Aplicação não pronta

Retornado quando `database`, `static_sites`, `transport_ai_operational_readiness` ou `transport_ai_settings_encryption` estiverem com status `"failed"`.

### Campos da resposta

| Campo            | Tipo      | Descrição                                                                 |
|------------------|-----------|---------------------------------------------------------------------------|
| `status`         | `string`  | `"ok"` se pronto, `"unready"` se não pronto                              |
| `app`            | `string`  | Nome da aplicação                                                         |
| `ready`          | `boolean` | `true` se todos os componentes críticos estiverem funcionando             |
| `overall_status` | `string`  | `"ok"`, `"degraded"` ou `"unready"`                                      |
| `components`     | `object`  | Mapa de componentes e seus respectivos status                            |

### Componentes avaliados (incluindo `forms_worker`)

| Componente                         | Crítico | Descrição                                                       |
|------------------------------------|---------|------------------------------------------------------------------|
| `database`                         | Sim     | Conectividade com o banco de dados                              |
| `static_sites`                     | Sim     | Presença dos diretórios de arquivos estáticos habilitados       |
| `transport_ai_operational_readiness` | Sim   | Pré-requisitos operacionais do módulo Transport AI              |
| `transport_ai_settings_encryption` | Sim     | Disponibilidade de chave de criptografia para IA                |
| `forms_worker`                     | Não     | Thread worker de envio de formulários Google Forms              |

> **Nota**: `forms_worker` com status `"degraded"` ou `"unknown"` mantém `ready: true`, mas eleva `overall_status` para `"degraded"`. `forms_worker` com status `"disabled"` não afeta o `overall_status`.

---

## Códigos de status HTTP

| Código | Significado                                              |
|--------|----------------------------------------------------------|
| `200`  | Aplicação pronta (pode estar `"degraded"` no forms_worker) |
| `503`  | Componente crítico com falha — aplicação não pronta      |

---

## Side effects

Nenhum. Este endpoint é somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s http://127.0.0.1:8000/api/health
```
