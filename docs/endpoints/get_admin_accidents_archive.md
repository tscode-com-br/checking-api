# `GET /api/admin/accidents/{accident_id}/archive`

## Visão Geral

Faz o download do arquivo ZIP de archive de um acidente encerrado. O arquivo contém uma planilha XLSX com a tabela de situação e todos os vídeos enviados pelos usuários. Retorna um redirect `307` para uma URL pre-assinada do DigitalOcean Spaces (S3), válida por 5 minutos.

| Atributo         | Valor                                                    |
|------------------|----------------------------------------------------------|
| **Método**       | `GET`                                                    |
| **Path**         | `/api/admin/accidents/{accident_id}/archive`             |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`).

---

## Parâmetros

### Path Parameters

| Parâmetro     | Tipo      | Descrição                 |
|---------------|-----------|---------------------------|
| `accident_id` | `integer` | ID do acidente encerrado. |

---

## Resposta

**HTTP 307 — Redirect para URL pre-assinada**

O servidor redireciona para a URL do objeto no DigitalOcean Spaces, válida por 300 segundos (5 minutos). O arquivo ZIP pode ser baixado diretamente pelo navegador ou por `curl -L`.

---

## Códigos de status HTTP

| Código | Significado                                                             |
|--------|-------------------------------------------------------------------------|
| `307`  | Redirect para a URL pre-assinada do arquivo ZIP.                        |
| `401`  | Sessão ausente ou inválida.                                             |
| `403`  | Sessão com escopo limitado — acesso negado.                             |
| `404`  | Archive não encontrado (ainda em geração ou acidente sem archive).      |

---

## Conteúdo do arquivo ZIP

O arquivo segue a estrutura:

```
ACC-0042/
  situacao.xlsx          # Tabela completa de situação dos usuários
  videos/
    CD34_video1.mp4      # Vídeos agrupados por usuário
    CD34_video2.mp4
    EF56_video1.mp4
```

- A planilha XLSX contém uma linha por usuário reportado, com zona, status, horário e informações de contato.
- Os vídeos são incluídos somente se foram enviados durante o acidente ativo.

---

## Side effects

Nenhum. O redirect é gerado com uma URL temporária — não altera o estado do banco.

---

## Exemplo cURL (ambiente local)

```bash
# -L segue o redirect 307 automaticamente
curl -s -b cookies.txt -L -o acidente_0042.zip \
  http://127.0.0.1:8000/api/admin/accidents/5/archive
```
