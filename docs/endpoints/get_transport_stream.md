# `GET /api/transport/stream`

## Visão Geral

Abre uma conexão SSE (Server-Sent Events) para receber notificações em tempo real de mudanças nos dados de transporte e do painel admin. A conexão é mantida aberta indefinidamente até ser desconectada pelo cliente ou pelo servidor.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/stream`                                           |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `text/event-stream` (resposta)                                    |

---

## Autenticação

Requer sessão de transporte válida. Se não houver sessão, o servidor retorna HTTP 401 antes de abrir o stream.

---

## Parâmetros

Nenhum parâmetro de query, path ou corpo de requisição.

---

## Resposta

A resposta é um stream SSE com eventos no formato `data: <json>\n\n`. Não há `event:` explícito nos frames; todos os eventos chegam como `data`.

**Evento inicial (conexão estabelecida):**

```
data: {"reason": "connected"}
```

**Keep-alive (enviado a cada 15 segundos sem evento):**

```
: keep-alive
```

**Evento de mudança de dados:**

```
data: {"reason": "event"}
```

ou

```
data: {"reason": "register"}
```

### Valores possíveis do campo `reason`

| Valor        | Descrição                                                    |
|--------------|--------------------------------------------------------------|
| `"connected"` | Confirmação de conexão estabelecida.                        |
| `"event"`    | Ocorreu um evento operacional (ex.: alocação atualizada).    |
| `"register"` | Um cadastro foi alterado (ex.: veículo ou workplace criado). |

---

## Códigos de status HTTP

| Código | Significado                                              |
|--------|----------------------------------------------------------|
| `200`  | Conexão SSE aberta com sucesso.                          |
| `401`  | Sessão de transporte ausente ou inválida.                |

---

## Cabeçalhos da resposta

| Cabeçalho              | Valor              |
|------------------------|--------------------|
| `Content-Type`         | `text/event-stream`|
| `Cache-Control`        | `no-cache`         |
| `Connection`           | `keep-alive`       |
| `X-Accel-Buffering`    | `no`               |

O cabeçalho `X-Accel-Buffering: no` é necessário para desativar o buffer do Nginx e garantir que os eventos sejam entregues imediatamente.

---

## Side effects

Nenhum. Endpoint somente leitura — apenas consome o broker de atualizações internas.

---

## Exemplo cURL (ambiente local)

```bash
curl -N \
  --cookie "session=<valor_do_cookie>" \
  http://127.0.0.1:8000/api/transport/stream
```

A flag `-N` desativa o buffer do cURL para que os eventos apareçam em tempo real.
