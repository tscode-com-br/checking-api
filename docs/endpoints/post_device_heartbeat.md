# `POST /api/device/heartbeat`

## Visão Geral

Registra um heartbeat do dispositivo RFID (ESP32-S3), atualizando seu status de `online` e o timestamp da última comunicação. Utilizado pelo firmware para sinalizar que o dispositivo está ativo.

| Atributo         | Valor                        |
|------------------|------------------------------|
| **Método**       | `POST`                       |
| **Path**         | `/api/device/heartbeat`      |
| **Autenticação** | `shared_key` no corpo JSON   |
| **Content-Type** | `application/json`           |
| **Tags**         | `device`                     |

---

## Autenticação

A autenticação é feita via campo `shared_key` no corpo da requisição, comparado com a variável de ambiente `DEVICE_SHARED_KEY`. Em caso de chave inválida, o endpoint retorna HTTP 200 com `{"ok": false}` (não HTTP 401) para evitar que o dispositivo entre em loop de erro, e registra um evento de falha no log.

---

## Parâmetros

### Request Body

```json
{
  "device_id": "esp32-gate-01",
  "shared_key": "minha-chave-secreta"
}
```

| Campo       | Tipo     | Obrigatório | Restrições          | Descrição                                 |
|-------------|----------|-------------|---------------------|-------------------------------------------|
| `device_id` | `string` | Sim         | 2–80 caracteres     | Identificador único do dispositivo RFID   |
| `shared_key`| `string` | Sim         | —                   | Chave compartilhada do dispositivo        |

---

## Resposta

### Sucesso — chave válida

```json
{
  "ok": true,
  "led": "white"
}
```

### Falha — chave inválida

```json
{
  "ok": false,
  "led": "red",
  "message": "invalid shared key"
}
```

| Campo     | Tipo      | Descrição                                                             |
|-----------|-----------|-----------------------------------------------------------------------|
| `ok`      | `boolean` | `true` se o heartbeat foi aceito                                      |
| `led`     | `string`  | Instrução de LED para o dispositivo: `"white"` (ok) ou `"red"` (erro) |
| `message` | `string`  | Presente apenas em caso de erro                                       |

---

## Códigos de status HTTP

| Código | Significado                                                              |
|--------|--------------------------------------------------------------------------|
| `200`  | Sempre retornado — verificar campo `ok` para determinar sucesso ou falha |
| `422`  | Body inválido (campos ausentes ou fora dos limites de tamanho)           |

---

## Side effects

- Grava ou atualiza uma linha na tabela `device_heartbeats` com `device_id`, `is_online=true` e `last_seen_at` com o horário atual (SGT).
- Em caso de chave inválida, grava um evento de falha na tabela `check_events` com `action="heartbeat"`, `status="failed"`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/device/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"device_id": "esp32-gate-01", "shared_key": "minha-chave-secreta"}'
```
