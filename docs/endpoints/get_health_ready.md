# `GET /api/health/ready`

## Visão Geral

Verifica se a aplicação está pronta para receber tráfego (readiness check). Consulta os componentes críticos — banco de dados, sites estáticos e Transport AI — e retorna HTTP 503 caso qualquer componente crítico esteja com falha. Não inclui o componente `forms_worker` (use `GET /api/health` para inspeção completa).

| Atributo         | Valor                                        |
|------------------|----------------------------------------------|
| **Método**       | `GET`                                        |
| **Path**         | `/api/health/ready`                          |
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

### 200 OK — Aplicação pronta

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
    }
  }
}
```

### 503 Service Unavailable — Aplicação não está pronta

```json
{
  "status": "unready",
  "app": "checking",
  "ready": false,
  "overall_status": "unready",
  "components": {
    "database": {
      "status": "failed",
      "detail": "database unavailable: connection refused"
    },
    "static_sites": {
      "status": "ok",
      "detail": "static sites ready: admin, user, transport"
    },
    "transport_ai_operational_readiness": {
      "status": "disabled",
      "detail": "transport ai disabled"
    },
    "transport_ai_settings_encryption": {
      "status": "disabled",
      "detail": "transport ai disabled"
    }
  }
}
```

### Campos da resposta

| Campo            | Tipo      | Descrição                                                                 |
|------------------|-----------|---------------------------------------------------------------------------|
| `status`         | `string`  | `"ok"` se pronto, `"unready"` se não pronto                              |
| `app`            | `string`  | Nome da aplicação                                                         |
| `ready`          | `boolean` | `true` se todos os componentes críticos estiverem funcionando             |
| `overall_status` | `string`  | `"ok"`, `"degraded"` (algum componente não-crítico degradado) ou `"unready"` |
| `components`     | `object`  | Mapa de componentes e seus respectivos status                            |

### Status possíveis por componente

| Status      | Significado                                                    |
|-------------|----------------------------------------------------------------|
| `"ok"`      | Componente funcionando normalmente                             |
| `"degraded"`| Componente funcional mas com degradação                       |
| `"failed"`  | Componente com falha crítica                                   |
| `"disabled"`| Componente desabilitado por configuração                      |
| `"unknown"` | Status do componente não pôde ser determinado                  |

### Componentes avaliados (excluindo `forms_worker`)

| Componente                         | Crítico | Descrição                                             |
|------------------------------------|---------|-------------------------------------------------------|
| `database`                         | Sim     | Conectividade com o banco de dados (`SELECT 1`)       |
| `static_sites`                     | Sim     | Presença dos diretórios de arquivos estáticos         |
| `transport_ai_operational_readiness` | Sim   | Pré-requisitos operacionais do módulo Transport AI    |
| `transport_ai_settings_encryption` | Sim     | Disponibilidade de chave de criptografia para IA      |

---

## Códigos de status HTTP

| Código | Significado                             |
|--------|-----------------------------------------|
| `200`  | Aplicação pronta para receber tráfego   |
| `503`  | Aplicação não está pronta               |

---

## Side effects

Nenhum. Este endpoint é somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s http://127.0.0.1:8000/api/health/ready
```
