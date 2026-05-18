# `DELETE /api/admin/accidents/{accident_id}`

## Visão Geral

Remove permanentemente um acidente encerrado e todos os seus dados associados (relatórios de usuários, uploads de vídeo, archive). Também remove os arquivos do storage (DO Spaces). Apenas admins com `perfil=9` podem executar esta operação.

| Atributo          | Valor                                               |
|-------------------|-----------------------------------------------------|
| **Método**        | `DELETE`                                            |
| **Path**          | `/api/admin/accidents/{accident_id}`                |
| **Autenticação**  | Sessão admin nível completo + `perfil=9`            |
| **Formato**       | `application/json`                                  |

---

## Autenticação

Requer sessão admin com nível completo **e** `perfil=9` (super-admin). Admins com perfil diferente recebem `403`.

---

## Parâmetros de Path

| Parâmetro     | Tipo      | Descrição                     |
|---------------|-----------|-------------------------------|
| `accident_id` | `integer` | ID interno do acidente        |

---

## Resposta (200)

```json
{
  "ok": true,
  "message": "Acidente removido com sucesso."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                             |
|--------|-----------------------------------------------------------------------------------------|
| `200`  | Acidente removido com sucesso                                                           |
| `401`  | Sessão ausente, expirada ou insuficiente                                                |
| `403`  | Admin não tem `perfil=9` (`"Apenas perfil 9 pode remover acidentes."`)                  |
| `404`  | Acidente não encontrado (`"Acidente nao encontrado."`)                                  |
| `409`  | Acidente ainda está ativo (`"Nao e possivel remover um acidente em curso. Encerre o Modo Acidente primeiro."`) |

### Exemplo de erro 409

```json
{ "detail": "Nao e possivel remover um acidente em curso. Encerre o Modo Acidente primeiro." }
```

---

## Side effects

- **Cascata no banco:** `DELETE` em `accidents` remove via CASCADE `accident_user_reports`, `accident_video_uploads`, `accident_archives` e `email_delivery_logs` (SET NULL).
- **Storage:** Remove o prefixo `accidents/{accident_number_label}/` no DO Spaces (todos os vídeos e ZIP do archive).
- `notify_admin_data_changed("accident_closed")` — atualiza painel admin via SSE
- `notify_web_check_data_changed("accident_closed")` — notifica Check Web via SSE
- `log_event(action="accident_delete", source="admin")` — grava evento na aba "Eventos"

> **Atenção:** Operação irreversível. Todos os vídeos e o archive ZIP são excluídos permanentemente.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X DELETE \
  -H "Cookie: session_id=<sua_sessao_admin_perfil9>" \
  http://127.0.0.1:8000/api/admin/accidents/7 \
  | python3 -m json.tool
```
