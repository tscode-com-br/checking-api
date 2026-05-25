# `GET /api/web/transport/stream`

## Visão Geral

Abre uma conexão SSE (Server-Sent Events) para receber notificações em tempo real sobre mudanças no estado de transporte. O frontend deve assinar este stream e chamar `GET /api/web/transport/state` a cada evento recebido para recarregar o estado atualizado.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/web/transport/stream`                    |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `text/event-stream` (resposta do servidor)     |

---

## Autenticação

Requer cookie de sessão `web_user_chave` definido por login prévio. O valor do cookie deve corresponder ao parâmetro `chave`. Em caso de falha retorna `401` e a conexão não é estabelecida.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo   | Obrigatório | Descrição                                                   |
|-----------|--------|-------------|-------------------------------------------------------------|
| `chave`   | string | Sim         | Chave do usuário (4 caracteres alfanuméricos, ex.: `"AB12"`) |

---

## Resposta

A resposta é um stream contínuo no formato SSE com eventos JSON no campo `data`:

### Evento de conexão estabelecida

Enviado imediatamente após a conexão ser aceita:

```
data: {"reason": "connected"}

```

### Evento de atualização de dados

Enviado quando há alteração no estado de transporte (nova atribuição, confirmação, cancelamento etc.):

```
data: {"reason": "event"}

```

### Keep-alive (heartbeat)

Enviado a cada 15 segundos de inatividade para manter a conexão viva:

```
: keep-alive

```

> **Uso correto:** ao receber qualquer evento com `"reason"` diferente de `"connected"`, o cliente deve chamar `GET /api/web/transport/state` para obter o estado atualizado.

---

## Cabeçalhos da resposta

| Cabeçalho           | Valor             | Descrição                                         |
|---------------------|-------------------|---------------------------------------------------|
| `Content-Type`      | `text/event-stream` | Formato SSE                                     |
| `Cache-Control`     | `no-cache`        | Impede cache do stream                            |
| `Connection`        | `keep-alive`      | Mantém a conexão aberta                           |
| `X-Accel-Buffering` | `no`              | Desativa buffering no Nginx para entrega imediata |

---

## Códigos de status HTTP

| Código | Significado                                       |
|--------|---------------------------------------------------|
| `200`  | Conexão estabelecida, stream iniciado             |
| `401`  | Sessão inválida ou expirada, ou chave não confere |
| `422`  | Parâmetro `chave` inválido                        |

---

## Side effects

Nenhum. Este endpoint é somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<cookie_de_sessao>" \
  -H "Accept: text/event-stream" \
  "http://127.0.0.1:8000/api/web/transport/stream?chave=AB12"
```

Exemplo de saída:

```
data: {"reason": "connected"}

: keep-alive

data: {"reason": "event"}

```
