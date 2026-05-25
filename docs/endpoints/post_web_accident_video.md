# `POST /api/web/check/accident/video`

## Visão Geral

Faz upload de um vídeo capturado pelo usuário durante o Modo Acidente. O arquivo é enviado como `multipart/form-data` e armazenado no Digital Ocean Spaces (ou localmente em ambiente de desenvolvimento). O endpoint é idempotente via `idempotency_key`: reenviar o mesmo key não cria duplicata.

| Atributo         | Valor                                              |
|------------------|----------------------------------------------------|
| **Método**       | `POST`                                             |
| **Path**         | `/api/web/check/accident/video`                    |
| **Autenticação** | Cookie de sessão + chave deve corresponder         |
| **Content-Type** | `multipart/form-data`                              |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no formulário deve coincidir com o valor no cookie. Em caso de falha retorna `401`.

---

## Parâmetros do formulário (multipart/form-data)

| Campo             | Tipo           | Obrigatório | Restrições                                       | Descrição                                                                                    |
|-------------------|----------------|-------------|--------------------------------------------------|----------------------------------------------------------------------------------------------|
| `chave`           | string (Form)  | Sim         | 4 caracteres alfanuméricos                       | Chave do usuário                                                                             |
| `idempotency_key` | string (Form)  | Sim         | 8 a 80 caracteres                                | Chave única gerada pelo cliente para evitar uploads duplicados (ex.: UUID ou timestamp+chave) |
| `duration_seconds`| int (Form)     | Não         |                                                  | Duração do vídeo em segundos                                                                 |
| `video`           | file (File)    | Sim         | Tipos aceitos: `video/webm`, `video/mp4`, `video/quicktime`. Tamanho máximo: 50 MB | Arquivo de vídeo gravado |

### Tipos de vídeo aceitos

| MIME type           | Extensão gerada |
|---------------------|-----------------|
| `video/webm`        | `.webm`         |
| `video/mp4`         | `.mp4`          |
| `video/quicktime`   | `.mov`          |

---

## Caminho de armazenamento

O vídeo é salvo com a seguinte estrutura de chave no storage:

```
accidents/{accident_number_label}/{chave}/{idempotency_key_normalizado}.{ext}
```

Exemplo: `accidents/ACC-0005/AB12/uuid-1234-abcd.webm`

---

## Resposta

```json
{
  "video_id": 42,
  "public_url": "https://sgp1.digitaloceanspaces.com/bucket/accidents/ACC-0005/AB12/uuid-1234-abcd.webm",
  "captured_at": "2026-05-25T14:38:55+08:00"
}
```

### Campos da resposta

| Campo        | Tipo     | Descrição                                                  |
|--------------|----------|------------------------------------------------------------|
| `video_id`   | int      | ID do registro criado em `accident_video_uploads`          |
| `public_url` | string   | URL pública do vídeo no storage                            |
| `captured_at`| datetime | Timestamp de quando o upload foi processado (ISO 8601)     |

---

## Códigos de status HTTP

| Código | Significado                                                               |
|--------|---------------------------------------------------------------------------|
| `200`  | Upload concluído com sucesso                                              |
| `401`  | Sessão inválida ou expirada, ou chave não confere                         |
| `409`  | Nenhum acidente em curso                                                  |
| `413`  | Arquivo excede o limite de 50 MB                                          |
| `415`  | Tipo de vídeo não suportado (somente `webm`, `mp4`, `quicktime`)          |

---

## Side effects

- Persiste o arquivo no Digital Ocean Spaces (ou em disco local em desenvolvimento).
- Cria registro em `accident_video_uploads`.
- Grava evento em `check_events` com `action="accident_video"`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  --form "chave=AB12" \
  --form "idempotency_key=550e8400-e29b-41d4-a716-446655440000" \
  --form "duration_seconds=12" \
  --form "video=@/tmp/gravacao.webm;type=video/webm" \
  "http://127.0.0.1:8000/api/web/check/accident/video"
```

> **Nota sobre idempotência:** use um UUID v4 ou combinação `{chave}-{timestamp_ms}` como `idempotency_key`. Em caso de falha de rede e reenvio, o mesmo key garante que o vídeo não seja duplicado na base.
