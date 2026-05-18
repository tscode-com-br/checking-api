# `POST /api/web/check/accident/video`

## Visão Geral

Faz upload de um clipe de vídeo capturado pelo usuário durante o acidente ativo. O vídeo é enviado em multipart form, armazenado no DO Spaces e vinculado ao acidente e ao usuário. O campo `idempotency_key` garante que envios repetidos do mesmo clipe não criem duplicatas.

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `POST`                                              |
| **Path**          | `/api/web/check/accident/video`                     |
| **Autenticação**  | Sessão web (cookie `web_session_id`) + campo `chave` no form |
| **Content-Type**  | `multipart/form-data`                               |
| **Formato**       | `application/json`                                  |

---

## Autenticação

Requer sessão web válida. O campo `chave` no form deve corresponder ao usuário da sessão ativa.

---

## Request (multipart/form-data)

| Campo             | Tipo               | Obrigatório | Descrição                                                           |
|-------------------|--------------------|-------------|---------------------------------------------------------------------|
| `chave`           | `string` (form)    | ✅           | Código do usuário (4 chars A-Z/0-9)                                 |
| `idempotency_key` | `string` (form)    | ✅           | Chave única do clipe (8–80 chars). Reenvios com mesma chave são ignorados. |
| `video`           | `file` (form)      | ✅           | Arquivo de vídeo. Tipos aceitos: `video/webm`, `video/mp4`, `video/quicktime` |
| `duration_seconds`| `integer` (form)   | —           | Duração em segundos (opcional, informativo)                         |

### Limites

- Tamanho máximo do arquivo: **50 MB** (`MAX_VIDEO_BYTES`)
- Tipos aceitos: `video/webm`, `video/mp4`, `video/quicktime`

### Destino no storage

O arquivo é salvo com a chave:
```
accidents/{accident_number_label}/{chave}/{idempotency_key}.{ext}
```
Exemplo: `accidents/0004/CEL2/clip-01.webm`

---

## Resposta (200)

```json
{
  "video_id": 12,
  "public_url": "https://seu-bucket.nyc3.digitaloceanspaces.com/accidents/0004/CEL2/clip-01.webm",
  "captured_at": "2026-05-18T10:10:00+08:00"
}
```

| Campo          | Tipo               | Descrição                                    |
|----------------|--------------------|----------------------------------------------|
| `video_id`     | `integer`          | ID interno do upload                         |
| `public_url`   | `string`           | URL pública do vídeo no storage              |
| `captured_at`  | `string` (ISO 8601)| Timestamp de criação do upload               |

---

## Códigos de status HTTP

| Código | Significado                                                                        |
|--------|------------------------------------------------------------------------------------|
| `200`  | Vídeo enviado com sucesso                                                          |
| `401`  | Sessão ausente, expirada, ou `chave` não coincide                                  |
| `409`  | Nenhum acidente em curso (`"Nenhum acidente em curso."`)                           |
| `413`  | Arquivo excede o tamanho máximo (50 MB)                                            |
| `415`  | Tipo de vídeo não suportado (`"Tipo de video nao suportado."`)                     |
| `422`  | Campos obrigatórios ausentes ou `idempotency_key` fora do tamanho permitido        |

### Exemplo de erro 415

```json
{ "detail": "Tipo de video nao suportado." }
```

---

## Side effects

- Upload para DO Spaces via `stream_upload_to_storage`
- Registro em `accident_video_uploads` (com `idempotency_key` único — reenvio retorna `200` sem criar duplicata)
- `notify_admin_data_changed("accident_video")` — atualiza painel admin via SSE
- `log_event(action="accident_video", source="web", rfid=chave)` — grava evento na aba "Eventos"

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: web_session_id=<sua_sessao_web>" \
  -F "chave=CEL2" \
  -F "idempotency_key=clip-sessao-abc123" \
  -F "duration_seconds=15" \
  -F "video=@/caminho/para/clip.webm;type=video/webm" \
  http://127.0.0.1:8000/api/web/check/accident/video \
  | python3 -m json.tool
```
