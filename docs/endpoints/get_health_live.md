# `GET /api/health/live`

## Visão Geral

Verifica se o processo da aplicação está vivo (liveness check). Retorna sempre HTTP 200 enquanto o processo estiver em execução, sem consultar dependências externas como banco de dados. Destinado a probes de liveness em orquestradores de containers (Kubernetes, Docker Swarm, etc.).

| Atributo         | Valor                                        |
|------------------|----------------------------------------------|
| **Método**       | `GET`                                        |
| **Path**         | `/api/health/live`                           |
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

### 200 OK

```json
{
  "status": "ok",
  "app": "checking"
}
```

| Campo  | Tipo     | Descrição                                    |
|--------|----------|----------------------------------------------|
| `status` | `string` | Sempre `"ok"` enquanto o processo estiver ativo |
| `app`    | `string` | Nome da aplicação conforme configurado em `settings.app_name` |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Processo em execução (independente de dependências)  |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s http://127.0.0.1:8000/api/health/live
```
