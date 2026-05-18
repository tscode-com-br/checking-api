# `GET /api/admin/accidents/{accident_id}/archive`

## Visão Geral

Redireciona para a URL de download do arquivo ZIP do acidente encerrado. O ZIP contém o relatório XLSX de situação de todos os usuários e todos os vídeos enviados durante o acidente.

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `GET`                                               |
| **Path**          | `/api/admin/accidents/{accident_id}/archive`        |
| **Autenticação**  | Sessão admin nível completo                         |
| **Formato**       | Redirecionamento 307 para URL pré-assinada (DO Spaces) |

---

## Autenticação

Requer sessão admin com nível completo. Sem sessão ou com sessão básica, retorna `401`.

---

## Parâmetros de Path

| Parâmetro     | Tipo      | Descrição                     |
|---------------|-----------|-------------------------------|
| `accident_id` | `integer` | ID interno do acidente        |

---

## Resposta

### Arquivo pronto (307 Temporary Redirect)

Redireciona para uma URL pré-assinada do DO Spaces válida por **5 minutos**. O browser ou cliente HTTP deve seguir o redirect automaticamente para fazer o download do ZIP.

```
HTTP/1.1 307 Temporary Redirect
Location: https://seu-bucket.nyc3.digitaloceanspaces.com/accidents/0003/acidente-0003.zip?X-Amz-Signature=...
```

### Conteúdo do ZIP

```
acidente-0003/
  situacao.xlsx          ← tabela completa de situação (zona, status, telefone, chave)
  videos/
    APF1/
      clip_01.webm
    CEL2/
      clip_01.mp4
```

---

## Códigos de status HTTP

| Código | Significado                                                                     |
|--------|---------------------------------------------------------------------------------|
| `307`  | Redirect para URL de download pré-assinada                                      |
| `401`  | Sessão ausente, expirada ou insuficiente                                        |
| `404`  | Archive ainda não gerado ou acidente não encontrado (`"Arquivo do acidente ainda nao esta pronto."`) |

### Exemplo de erro 404

```json
{ "detail": "Arquivo do acidente ainda nao esta pronto." }
```

> O archive é gerado em background após `POST /accidents/close`. Aguarde alguns segundos e consulte `download_ready` via `GET /accidents` antes de tentar o download.

---

## Side effects

Nenhum. Gera uma URL pré-assinada temporária (expiração em 300 segundos).

---

## Exemplo cURL (ambiente local)

```bash
# -L para seguir o redirect automaticamente
curl -s -L \
  -H "Cookie: session_id=<sua_sessao_admin>" \
  -o acidente-0003.zip \
  http://127.0.0.1:8000/api/admin/accidents/7/archive

echo "Download concluído: acidente-0003.zip"
```
