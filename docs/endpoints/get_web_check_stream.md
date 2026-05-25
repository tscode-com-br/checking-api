# `GET /api/web/check/stream`

## Visão Geral

Abre um stream SSE (Server-Sent Events) que envia notificações em tempo real sempre que há uma mudança no estado do Check Web. O cliente deve manter a conexão aberta e reagir aos eventos recebidos atualizando a interface.

| Atributo         | Valor                                  |
|------------------|----------------------------------------|
| **Método**       | `GET`                                  |
| **Path**         | `/api/web/check/stream`                |
| **Autenticação** | Cookie de sessão obrigatório (chave na sessão deve corresponder ao parâmetro `chave`) |
| **Content-Type** | `text/event-stream` (resposta)         |

---

## Autenticação

Requer sessão ativa via cookie **e** que a chave armazenada na sessão seja idêntica ao parâmetro `chave` informado. Se a autenticação falhar, a conexão é recusada com HTTP 401 antes de iniciar o stream.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo   | Obrigatório | Descrição                                                           |
|-----------|--------|-------------|---------------------------------------------------------------------|
| `chave`   | string | Sim         | Chave do usuário — 4 caracteres alfanuméricos (maiúsculas). Ex.: `AB12` |

---

## Resposta

A resposta usa o protocolo SSE com `Content-Type: text/event-stream`. A conexão permanece aberta indefinidamente até que o cliente se desconecte.

### Headers de resposta

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

> `X-Accel-Buffering: no` desativa o buffer do Nginx, essencial para que os eventos cheguem imediatamente ao cliente.

### Formato dos eventos

Cada evento SSE é enviado como uma linha com o prefixo `data:` seguida de um JSON:

```
data: {"reason": "connected"}

data: {"reason": "event"}

: keep-alive

```

> Linhas iniciadas com `:` são comentários SSE e servem apenas para manter a conexão viva (heartbeat a cada 15 segundos de inatividade). O cliente deve ignorá-las.

### Campos do payload JSON

| Campo    | Tipo   | Valores possíveis | Descrição                                                             |
|----------|--------|-------------------|-----------------------------------------------------------------------|
| `reason` | string | `"connected"`, `"event"`, `"admin"`, `"register"` | Motivo da notificação. O cliente deve usar este campo para decidir quais dados recarregar |

### Comportamento dos eventos

| `reason`     | Quando é enviado                                                              | Ação recomendada no cliente                  |
|--------------|-------------------------------------------------------------------------------|----------------------------------------------|
| `connected`  | Imediatamente após a conexão ser estabelecida                                 | Confirmar conexão; carregar estado inicial   |
| `event`      | Após um novo check-in ou check-out ser registrado                             | Recarregar `GET /api/web/check/state`        |
| `admin`      | Após mudanças de cadastro (usuário, projetos)                                 | Recarregar dados de usuário/projetos         |
| `register`   | Após alteração de projetos do usuário                                         | Recarregar projetos e estado                 |

### Exemplo de sessão SSE

```
data: {"reason": "connected"}

: keep-alive

: keep-alive

data: {"reason": "event"}

data: {"reason": "event"}

```

---

## Códigos de status HTTP

| Código | Significado                                                         |
|--------|---------------------------------------------------------------------|
| `200`  | Stream aberto com sucesso (resposta contínua)                       |
| `401`  | Sessão ausente, inválida, expirada ou chave não corresponde à sessão |
| `422`  | Chave com formato inválido                                          |

---

## Side effects

- O cliente é registrado como assinante no broker interno `web_check_updates_broker`.
- Ao se desconectar, o cliente é removido automaticamente do broker.

---

## Exemplo cURL (ambiente local)

```bash
# Requer cookie de sessão obtido via POST /api/web/auth/login com a mesma chave
curl -s -N "http://127.0.0.1:8000/api/web/check/stream?chave=AB12" \
  -b cookies.txt \
  -H "Accept: text/event-stream"

# A flag -N desativa o buffer do cURL, permitindo ver os eventos em tempo real.
```

### Exemplo com JavaScript (EventSource)

```javascript
const source = new EventSource(
  `/api/web/check/stream?chave=AB12`,
  { withCredentials: true }
);

source.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.reason === 'event') {
    // Recarregar estado do check
    fetchCheckState();
  }
};

source.addEventListener('error', () => {
  // Reconectar após falha (EventSource reconecta automaticamente)
});
```
