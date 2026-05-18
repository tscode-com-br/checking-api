# `POST /api/admin/accidents/close`

## Visão Geral

Encerra o acidente ativo. Apenas o admin pode fechar o Modo Acidente. Após o encerramento, o sistema gera em background um arquivo ZIP contendo o XLSX da tabela de situação e todos os vídeos enviados.

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `POST`                                              |
| **Path**          | `/api/admin/accidents/close`                        |
| **Autenticação**  | Sessão admin nível completo                         |
| **Content-Type**  | — (sem body)                                        |
| **Formato**       | `application/json`                                  |

---

## Autenticação

Requer sessão admin com nível completo. Sem sessão ou com sessão básica, retorna `401`.

---

## Request Body

Nenhum body necessário.

---

## Resposta (200)

```json
{
  "is_active": false,
  "accident": null,
  "situation_rows": []
}
```

Sempre retorna `is_active=false` após encerramento bem-sucedido.

---

## Códigos de status HTTP

| Código | Significado                                         |
|--------|-----------------------------------------------------|
| `200`  | Acidente encerrado com sucesso                      |
| `401`  | Sessão ausente, expirada ou insuficiente            |
| `409`  | Nenhum acidente em curso (`"Nenhum acidente em curso."`) |

### Exemplo de erro 409

```json
{ "detail": "Nenhum acidente em curso." }
```

---

## Side effects

- `build_and_attach_archive_for_accident(accident_id)` — executa em **background task** após a resposta:
  - Gera XLSX com a tabela de situação de todos os usuários
  - Baixa os vídeos do storage e empacota em ZIP
  - Faz upload do ZIP para DO Spaces
  - Salva `AccidentArchive` no banco
- `notify_admin_data_changed("accident_closed")` — atualiza painel admin via SSE
- `notify_web_check_data_changed("accident_closed")` — notifica Check Web via SSE
- `log_event(action="accident_close", source="admin")` — grava evento na aba "Eventos"

> **Nota:** O arquivo ZIP pode não estar disponível imediatamente após o encerramento. Use `GET /accidents/{id}/archive` para verificar quando `download_ready=true`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: session_id=<sua_sessao_admin>" \
  http://127.0.0.1:8000/api/admin/accidents/close \
  | python3 -m json.tool
```
