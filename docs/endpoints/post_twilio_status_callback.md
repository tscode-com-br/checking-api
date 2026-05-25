# `POST /api/twilio/status-callback`

## Visão Geral

Webhook chamado automaticamente pelo Twilio quando o status de uma chamada de voz de emergência muda. Atualiza o `AccidentCallLog` correspondente com o novo status e duração, persiste uma notificação formatada em português na tabela `accident_call_notifications`, e dispara um evento SSE para o painel admin atualizar a barra de notificações de chamadas em tempo real.

Este endpoint **não é chamado diretamente pelo cliente** — é invocado pelo servidor Twilio via HTTP POST com dados em formato `application/x-www-form-urlencoded`.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/twilio/status-callback`                  |
| **Autenticação** | Nenhuma (chamado pelo servidor Twilio)         |
| **Content-Type** | `application/x-www-form-urlencoded`            |
| **Tags**         | `twilio`                                       |

---

## Autenticação

Nenhuma autenticação de chave é implementada neste endpoint. A segurança se baseia na URL secreta configurada no painel Twilio como `statusCallback`. Recomenda-se restringir por IP (faixas de IP do Twilio) na camada de infraestrutura em produção.

Se o `CallSid` não for reconhecido na base, o endpoint retorna HTTP 200 e registra um warning no log do servidor, sem processar.

---

## Parâmetros

### Request Body (form-urlencoded)

Enviado pelo Twilio automaticamente. Os campos relevantes consumidos pelo endpoint:

| Campo          | Tipo     | Descrição                                                                           |
|----------------|----------|-------------------------------------------------------------------------------------|
| `CallSid`      | `string` | Identificador único da chamada no Twilio                                           |
| `CallStatus`   | `string` | Status atual da chamada (ver tabela abaixo)                                        |
| `CallDuration` | `string` | Duração em segundos (presente apenas no status `completed`)                        |
| `Duration`     | `string` | Alternativa a `CallDuration` (ambos são tentados)                                  |

### Valores de `CallStatus` enviados pelo Twilio

| Status Twilio  | Mapeamento interno (`status_event`) | Descrição                              |
|----------------|--------------------------------------|----------------------------------------|
| `initiated`    | `"initiated"`                        | Chamada iniciada                       |
| `ringing`      | `"initiated"`                        | Telefone do destinatário tocando       |
| `in-progress`  | `"answered"`                         | Chamada atendida                       |
| `completed`    | `"completed"`                        | Chamada encerrada normalmente          |
| `failed`       | `"failed"`                           | Falha técnica na chamada               |
| `busy`         | `"busy"`                             | Número ocupado                         |
| `no-answer`    | `"no_answer"`                        | Não atendida (timeout)                 |
| `canceled`     | `"canceled"`                         | Chamada cancelada antes de ser atendida |

---

## Resposta

O endpoint sempre retorna HTTP 200 com body vazio. O Twilio ignora o conteúdo da resposta.

```
HTTP/1.1 200 OK
```

---

## Códigos de status HTTP

| Código | Significado                                                    |
|--------|----------------------------------------------------------------|
| `200`  | Sempre retornado, inclusive em casos de erro de parsing       |

> O endpoint captura exceções de parsing e retorna HTTP 200 de qualquer forma para evitar que o Twilio reenvie o callback indefinidamente.

---

## Side effects

- Atualiza `AccidentCallLog.call_status` e `AccidentCallLog.duration_seconds` (se disponível).
- Define `AccidentCallLog.ended_by = "system"` quando `call_status == "completed"` e `ended_by` ainda não foi definido.
- Atualiza `AccidentCallLog.updated_at` com o horário atual (SGT).
- Persiste uma linha em `accident_call_notifications` com metadados formatados em português (apenas se o acidente e projeto ainda existirem).
- Chama `notify_admin_data_changed("emergency_call_status_update", metadata=...)` via SSE, disparando atualização em tempo real na barra de notificações do painel admin (seção 3 do painel).

### Metadados SSE propagados

O payload do evento SSE inclui:

| Campo                | Descrição                                                    |
|----------------------|--------------------------------------------------------------|
| `call_number`        | Número sequencial vitalício da chamada                       |
| `call_number_label`  | Número formatado com zero-padding (ex.: `"000042"`)         |
| `accident_id`        | ID do acidente relacionado                                   |
| `call_status`        | Status bruto do Twilio                                       |
| `status_event`       | Status mapeado para o frontend                               |
| `occurred_at`        | Timestamp do evento                                          |
| `duration_seconds`   | Duração da chamada (apenas em `completed`)                   |
| `ended_by`           | Quem encerrou: `"system"` (padrão) ou outro valor se definido |

---

## Exemplo de payload enviado pelo Twilio

```
POST /api/twilio/status-callback HTTP/1.1
Content-Type: application/x-www-form-urlencoded

CallSid=CA1234567890abcdef1234567890abcdef&CallStatus=completed&CallDuration=45&...
```

> **Nota**: este endpoint não deve ser chamado manualmente em produção. Em desenvolvimento, é possível simular um callback com cURL para testes.

## Exemplo cURL de simulação (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/twilio/status-callback \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "CallSid=CA1234567890abcdef1234567890abcdef" \
  --data-urlencode "CallStatus=completed" \
  --data-urlencode "CallDuration=45"
```
