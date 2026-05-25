# `POST /api/admin/accidents/{accident_id}/emergency-call`

## Visão Geral

Inicia uma chamada de emergência via Twilio Voice para o número de telefone configurado no projeto do acidente. A chamada reproduz uma mensagem de alerta com os dados do acidente e registra o log em `accident_call_logs`.

| Atributo         | Valor                                                   |
|------------------|---------------------------------------------------------|
| **Método**       | `POST`                                                  |
| **Path**         | `/api/admin/accidents/{accident_id}/emergency-call`     |
| **Autenticação** | Sessão admin com identidade completa (`require_admin_identity`) |
| **Content-Type** | Nenhum (sem corpo)                                      |

---

## Autenticação

Requer `require_admin_identity`. Apenas administradores autenticados podem iniciar chamadas de emergência.

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo      | Descrição                                   |
|---------------|-----------|---------------------------------------------|
| `accident_id` | `integer` | ID do acidente para o qual disparar a chamada. |

---

## Resposta

**HTTP 200 — Chamada iniciada**

```json
{
  "call_number": 3,
  "call_number_label": "000003",
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "call_status": "queued",
  "message": "Chamada de emergência #000003 iniciada."
}
```

| Campo              | Tipo           | Descrição                                                    |
|--------------------|----------------|--------------------------------------------------------------|
| `call_number`      | `integer`      | Número sequencial da chamada (vitalício, por acidente).      |
| `call_number_label`| `string`       | Número formatado com 6 dígitos (ex.: `"000003"`).            |
| `call_sid`         | `string\|null` | SID da chamada retornado pelo Twilio.                        |
| `call_status`      | `string`       | Status inicial da chamada (`"queued"`, `"initiated"`, etc.). |
| `message`          | `string`       | Mensagem descritiva da operação.                             |

---

## Códigos de status HTTP

| Código | Significado                                                                                        |
|--------|----------------------------------------------------------------------------------------------------|
| `200`  | Chamada iniciada com sucesso.                                                                      |
| `401`  | Sessão ausente ou inválida.                                                                        |
| `404`  | Acidente não encontrado ou já encerrado; ou projeto não encontrado.                                |
| `422`  | Twilio não está configurado no projeto (credenciais ausentes no `.env` ou nas configurações do projeto). |
| `502`  | Twilio retornou erro ao iniciar a chamada (falha na API externa).                                  |

---

## Pré-requisitos de configuração

Para que as chamadas funcionem, o projeto deve ter configurado:

- `twilio_account_sid`
- `twilio_auth_token`
- `twilio_phone_number` (número de origem)
- `mobile_admin` (número de destino) ou `emergency_phone`
- `emergency_call_message` (texto TTS da mensagem)

Configurações via `.env` global ou diretamente no projeto via `PUT /api/admin/projects/{project_id}`.

---

## Side effects

- Cria registro em `accident_call_logs` com o status inicial da chamada.
- Cria registros em `accident_call_notifications` com mensagens pt-BR do progresso da chamada.
- Grava evento em `check_events` com `action="accident_call"` e `source="admin"`.
- Notifica painel admin via SSE após conclusão (via Twilio callback).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/admin/accidents/5/emergency-call
```
