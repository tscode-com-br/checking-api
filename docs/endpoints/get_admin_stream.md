# `GET /api/admin/stream`

## Visão Geral

Endpoint de Server-Sent Events (SSE) que mantém uma conexão persistente e envia notificações em tempo real ao painel admin. O frontend usa este stream para atualizar a UI sem polling.

| Atributo         | Valor                                  |
|------------------|----------------------------------------|
| **Método**       | `GET`                                  |
| **Path**         | `/api/admin/stream`                    |
| **Autenticação** | Sessão admin (qualquer nível de acesso) |
| **Content-Type** | `text/event-stream`                    |

---

## Autenticação

Requer sessão admin via cookie (`require_admin_stream_session`). Qualquer administrador com sessão válida — escopo limitado ou completo — pode se conectar. Retorna `401` ou redireciona para login se a sessão estiver ausente.

---

## Parâmetros

Nenhum.

---

## Formato dos eventos SSE

O protocolo SSE padrão é usado. Cada mensagem começa com `data:` seguido de JSON serializado, e termina com dois newlines `\n\n`.

### Evento de conexão inicial

Enviado imediatamente ao conectar:

```
data: {"reason": "connected"}

```

### Eventos de atualização de dados

```
data: {"event_id": "a3f5c8d2...", "reason": "register", "emitted_at": "2026-05-25T10:30:00.123456+00:00"}

```

```
data: {"event_id": "b1e2f3a4...", "reason": "accident_closed", "emitted_at": "2026-05-25T10:35:00+00:00", "deleted_accident_id": 42}

```

### Keep-alive

A cada 15 segundos sem evento, um comentário é enviado para manter a conexão:

```
: keep-alive

```

### Campos do payload JSON

| Campo         | Tipo     | Descrição                                                                 |
|---------------|----------|---------------------------------------------------------------------------|
| `event_id`    | `string` | UUID hex único por evento (para deduplicação no frontend).                |
| `reason`      | `string` | Motivo da notificação. Ver tabela de razões abaixo.                       |
| `emitted_at`  | `string` | ISO 8601 UTC do momento de emissão.                                       |
| `*` (variável)| `any`    | Campos de metadados opcionais conforme o `reason` (ex.: `deleted_accident_id`). |

### Valores comuns de `reason`

| Reason               | Quando é emitido                                      |
|----------------------|-------------------------------------------------------|
| `connected`          | Imediatamente ao estabelecer a conexão SSE.           |
| `refresh`            | Atualização genérica de dados.                        |
| `register`           | Cadastro ou atualização de usuário/projeto.           |
| `admin`              | Mudança na lista de administradores.                  |
| `event`              | Novo evento registrado em `check_events`.             |
| `accident_closed`    | Acidente encerrado ou deletado.                       |
| `inactivity_descadastro` | Usuário removido por inatividade.                |

---

## Códigos de status HTTP

| Código | Significado                                                      |
|--------|------------------------------------------------------------------|
| `200`  | Conexão SSE estabelecida (stream aberto).                        |
| `401`  | Sessão ausente ou inválida.                                      |

---

## Cabeçalhos de resposta

| Cabeçalho            | Valor               | Descrição                                                  |
|----------------------|---------------------|------------------------------------------------------------|
| `Content-Type`       | `text/event-stream` | Protocolo SSE.                                             |
| `Cache-Control`      | `no-cache`          | Desabilita cache de proxy.                                 |
| `Connection`         | `keep-alive`        | Mantém a conexão TCP aberta.                               |
| `X-Accel-Buffering`  | `no`                | Desabilita buffering no Nginx (necessário para SSE em produção). |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo de conexão (JavaScript)

```javascript
const evtSource = new EventSource('/api/admin/stream');
evtSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.reason === 'connected') return;
  // atualizar a UI conforme o reason
  console.log('SSE update:', data.reason);
};
```

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -N http://127.0.0.1:8000/api/admin/stream
```
