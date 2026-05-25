# `POST /api/scan`

## Visão Geral

Processa uma leitura RFID realizada pelo dispositivo ESP32-S3. Identifica o usuário pelo RFID, aplica a ação de check-in ou checkout, e — conforme a regra de negócio — enfileira ou ignora o envio de uma submissão ao Google Forms. Implementa idempotência via `request_id` para evitar processamento duplicado de retransmissões do firmware.

| Atributo         | Valor                        |
|------------------|------------------------------|
| **Método**       | `POST`                       |
| **Path**         | `/api/scan`                  |
| **Autenticação** | `shared_key` no corpo JSON   |
| **Content-Type** | `application/json`           |
| **Tags**         | `device`                     |

---

## Autenticação

A autenticação é feita via campo `shared_key` no corpo da requisição, comparado com `DEVICE_SHARED_KEY`. Em caso de chave inválida, o endpoint retorna HTTP 200 com `outcome="invalid_key"` e registra o evento de falha no log.

---

## Parâmetros

### Request Body

```json
{
  "rfid": "AABBCCDD",
  "local": "Portaria Principal",
  "action": "checkin",
  "device_id": "esp32-gate-01",
  "request_id": "esp32-gate-01-1716652800-001",
  "shared_key": "minha-chave-secreta"
}
```

| Campo        | Tipo     | Obrigatório | Restrições          | Descrição                                           |
|--------------|----------|-------------|---------------------|-----------------------------------------------------|
| `rfid`       | `string` | Sim         | 4–64 caracteres     | Código RFID lido pelo leitor                        |
| `local`      | `string` | Sim         | 2–40 caracteres     | Local físico onde a leitura ocorreu                 |
| `action`     | `string` | Sim         | `"checkin"` ou `"checkout"` | Ação a registrar                         |
| `device_id`  | `string` | Sim         | 2–80 caracteres     | Identificador do dispositivo RFID                   |
| `request_id` | `string` | Sim         | 8–80 caracteres     | ID único da requisição gerado pelo firmware (chave de idempotência) |
| `shared_key` | `string` | Sim         | —                   | Chave compartilhada do dispositivo                  |

---

## Resposta

```json
{
  "outcome": "submitted",
  "led": "green_1s",
  "message": "Operation accepted and queued for Forms submission"
}
```

| Campo     | Tipo     | Descrição                                                              |
|-----------|----------|------------------------------------------------------------------------|
| `outcome` | `string` | Resultado do processamento (ver tabela abaixo)                         |
| `led`     | `string` | Instrução de LED para o dispositivo (ver tabela abaixo)                |
| `message` | `string` | Descrição legível do resultado                                         |

### Valores de `outcome`

| `outcome`              | Situação                                                                   |
|------------------------|----------------------------------------------------------------------------|
| `"submitted"`          | Ação aceita; submissão ao Forms enfileirada                                |
| `"local_updated"`      | Ação aceita; Forms não enfileirado (ex.: check-in seguido sem checkout)    |
| `"pending_registration"` | RFID não encontrado na base; adicionado à lista de registros pendentes   |
| `"duplicate"`          | `request_id` já processado anteriormente; requisição ignorada             |
| `"invalid_key"`        | `shared_key` inválida                                                      |
| `"failed"`             | Checkout bloqueado — usuário não possui check-in anterior registrado       |

### Valores de `led`

| `led`                  | Comportamento físico                                              |
|------------------------|-------------------------------------------------------------------|
| `"green_1s"`           | Verde sólido por 1 segundo (ação enfileirada no Forms)           |
| `"green_blink_3x_1s"`  | Verde piscando 3x em 1 segundo (ação aceita sem Forms)           |
| `"orange_4s"`          | Laranja por 4 segundos (RFID pendente de registro)               |
| `"white"`              | Branco (requisição duplicada)                                    |
| `"red"`                | Vermelho (chave inválida)                                        |
| `"red_2s"`             | Vermelho por 2 segundos (checkout bloqueado)                     |

---

## Códigos de status HTTP

| Código | Significado                                                              |
|--------|--------------------------------------------------------------------------|
| `200`  | Sempre retornado — verificar campo `outcome` para o resultado da operação |
| `422`  | Body inválido (campos ausentes ou fora dos limites)                      |

---

## Side effects

- Registra eventos na tabela `check_events` (incluindo entradas de idempotência com sufixos `:invalid`, `:duplicate`, `:pending`, `:blocked`, `:local-updated`, `:queued`).
- Cria ou atualiza linha em `pending_registrations` se o RFID não for encontrado.
- Atualiza o estado atual do usuário (`users.checkin`, `users.time`, `users.local`).
- Cria um `UserSyncEvent` registrando a atividade.
- Enfileira uma `FormsSubmission` quando as regras de negócio determinam envio ao Google Forms.
- Chama `notify_admin_data_changed()` via SSE para atualizar o painel admin em tempo real.
- Chama `fire_accident_hook_for_check_event()` para integração com o Modo Acidente (atualiza tabela de situação se houver acidente ativo).

---

## Exemplo cURL (ambiente local)

```bash
# Check-in
curl -s -X POST http://127.0.0.1:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "rfid": "AABBCCDD",
    "local": "Portaria Principal",
    "action": "checkin",
    "device_id": "esp32-gate-01",
    "request_id": "req-20240525-001",
    "shared_key": "minha-chave-secreta"
  }'

# Checkout
curl -s -X POST http://127.0.0.1:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "rfid": "AABBCCDD",
    "local": "Portaria Principal",
    "action": "checkout",
    "device_id": "esp32-gate-01",
    "request_id": "req-20240525-002",
    "shared_key": "minha-chave-secreta"
  }'
```
