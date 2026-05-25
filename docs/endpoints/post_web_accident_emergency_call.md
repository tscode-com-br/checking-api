# `POST /api/web/check/accident/emergency-call`

## Visão Geral

Dispara uma chamada telefônica de emergência via Twilio para o número de emergência do projeto associado ao acidente ativo. Apenas um usuário pode iniciar a chamada por acidente — chamadas duplicadas são bloqueadas. O endpoint verifica se há acidente ativo no projeto do usuário antes de acionar o serviço externo.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/check/accident/emergency-call`       |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no body deve coincidir com o valor no cookie. Em caso de falha retorna `401`.

---

## Request Body

```json
{
  "chave": "AB12"
}
```

### Campos do request body

| Campo         | Tipo        | Obrigatório | Descrição                                                                                        |
|---------------|-------------|-------------|--------------------------------------------------------------------------------------------------|
| `chave`       | string      | Sim         | Chave do usuário (4 caracteres alfanuméricos A-Z 0-9)                                            |
| `accident_id` | int \| null | Não         | ID do acidente alvo. Se omitido, usa o primeiro acidente ativo do projeto do usuário (legado)    |

---

## Resposta

```json
{
  "call_number": 3,
  "call_number_label": "000003",
  "call_sid": "CA1234567890abcdef1234567890abcdef",
  "call_status": "queued",
  "message": "Chamada de emergência #000003 iniciada."
}
```

### Campos da resposta

| Campo               | Tipo           | Descrição                                                                        |
|---------------------|----------------|----------------------------------------------------------------------------------|
| `call_number`       | int            | Número sequencial vitalício da chamada (contador global do sistema)              |
| `call_number_label` | string         | Número formatado com zero à esquerda (6 dígitos, ex.: `"000003"`)               |
| `call_sid`          | string \| null | SID da chamada no Twilio. `null` se a chamada ainda não foi confirmada pelo Twilio |
| `call_status`       | string         | Status inicial retornado pelo Twilio: `"queued"`, `"initiated"`, `"ringing"`, `"in-progress"`, `"completed"`, `"failed"`, `"busy"`, `"no-answer"`, `"canceled"` |
| `message`           | string         | Mensagem de confirmação para exibir ao usuário                                   |

---

## Códigos de status HTTP

| Código | Significado                                                                                   |
|--------|-----------------------------------------------------------------------------------------------|
| `200`  | Chamada iniciada com sucesso                                                                  |
| `401`  | Sessão inválida ou expirada, ou chave não confere                                             |
| `404`  | Nenhum acidente em curso para o projeto do usuário, ou projeto não encontrado                |
| `409`  | Uma chamada de emergência já foi realizada por outro usuário neste acidente                  |
| `422`  | Twilio não está configurado no ambiente (variáveis de ambiente ausentes)                     |
| `502`  | Falha ao contatar o Twilio — erro retornado pela API externa                                 |

---

## Pré-requisitos no ambiente

Para que a chamada seja realizada, as seguintes variáveis de ambiente devem estar configuradas no servidor:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_PHONE` — número Twilio de origem
- O projeto deve ter `emergency_phone` cadastrado

---

## Side effects

- Cria registro em `accident_call_logs` com `call_number` sequencial.
- Registra notificações persistentes em `accident_call_notifications` para o feed do admin.
- Grava evento em `check_events` com `action="accident_call"`.
- Emite notificação SSE admin via `notify_admin_data_changed`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12"}' \
  "http://127.0.0.1:8000/api/web/check/accident/emergency-call"
```
