# `GET /api/admin/accidents/local-asset/{path}`

## Visão Geral

Serve arquivos de assets de acidentes armazenados localmente no sistema de arquivos. **Disponível apenas em ambiente de desenvolvimento** (`app_env != "production"`). Em produção, retorna `404` — os assets são servidos diretamente pelo DigitalOcean Spaces via URL pre-assinada.

| Atributo         | Valor                                           |
|------------------|-------------------------------------------------|
| **Método**       | `GET`                                           |
| **Path**         | `/api/admin/accidents/local-asset/{path}`       |
| **Autenticação** | Nenhuma obrigatória (endpoint de desenvolvimento) |

---

## Autenticação

Sem proteção de sessão explícita. Em produção retorna `404` antes de qualquer verificação.

---

## Parâmetros

### Path Parameters

| Parâmetro | Tipo     | Descrição                                                         |
|-----------|----------|-------------------------------------------------------------------|
| `path`    | `string` | Caminho relativo ao diretório local de storage de acidentes. Aceita subdiretórios (path param greedy com `:path`). |

**Exemplo de paths válidos:**

- `accidents/0042/situacao.xlsx`
- `accidents/0042/videos/CD34_video1.mp4`

---

## Resposta

**HTTP 200 — Arquivo encontrado**

Retorna o conteúdo do arquivo com o Content-Type inferido automaticamente pelo FastAPI (`FileResponse`).

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Arquivo servido com sucesso.                                         |
| `404`  | Em produção (armazenamento remoto ativo), arquivo não encontrado, ou path inválido. |

---

## Comportamento por ambiente

| Ambiente      | Comportamento                                              |
|---------------|------------------------------------------------------------|
| Desenvolvimento (`_use_remote() == False`) | Serve o arquivo do diretório local `_local_root()`. |
| Produção (`_use_remote() == True`)         | Retorna `404` imediatamente. Assets são servidos pelo DO Spaces. |

O diretório base é determinado por `object_storage._local_root()`, configurado via variáveis de ambiente ou padrão de desenvolvimento.

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -o situacao.xlsx \
  "http://127.0.0.1:8000/api/admin/accidents/local-asset/accidents/0042/situacao.xlsx"
```
