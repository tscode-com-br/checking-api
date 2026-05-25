# `GET /api/admin/accidents`

## Visão Geral

Lista todos os acidentes **encerrados** (`closed_at IS NOT NULL`), ordenados pelo número de acidente decrescente (mais recente primeiro). Não retorna acidentes ativos — para o estado ativo, use `GET /api/admin/accidents/active`.

| Atributo         | Valor                                     |
|------------------|-------------------------------------------|
| **Método**       | `GET`                                     |
| **Path**         | `/api/admin/accidents`                    |
| **Autenticação** | Sessão admin com escopo completo (`require_full_admin_session`) |

---

## Autenticação

Requer sessão admin com `access_scope="full"` (`require_full_admin_session`). Administradores com escopo limitado recebem `403`.

---

## Parâmetros

Nenhum. Retorna todos os acidentes encerrados sem paginação (a lista tende a ser pequena em produção).

---

## Resposta

**HTTP 200**

```json
{
  "rows": [
    {
      "id": 5,
      "accident_number_label": "0042",
      "project_name": "P80",
      "author_label": "João da Silva",
      "opened_at": "2026-05-25T08:00:00Z",
      "closed_at": "2026-05-25T09:30:00Z",
      "description": "Colisão na plataforma norte",
      "download_url": "/api/admin/accidents/5/archive",
      "download_ready": true,
      "can_delete": false
    }
  ]
}
```

### Campos de cada item em `rows`

| Campo                  | Tipo       | Descrição                                                                           |
|------------------------|------------|-------------------------------------------------------------------------------------|
| `id`                   | `integer`  | ID interno do acidente.                                                             |
| `accident_number_label`| `string`   | Número sequencial formatado com 4 dígitos (ex.: `"0042"`).                         |
| `project_name`         | `string`   | Snapshot do nome do projeto no momento de abertura.                                 |
| `author_label`         | `string`   | Nome de quem abriu o acidente (admin ou usuário web).                               |
| `opened_at`            | `datetime` | ISO 8601 UTC de abertura.                                                           |
| `closed_at`            | `datetime` | ISO 8601 UTC de encerramento.                                                       |
| `description`          | `string`   | Descrição opcional do acidente.                                                     |
| `download_url`         | `string`   | Path relativo para download do archive: `/api/admin/accidents/{id}/archive`.        |
| `download_ready`       | `boolean`  | `false` enquanto o archive ainda está sendo gerado em background; `true` quando pronto. |
| `can_delete`           | `boolean`  | `true` somente se o admin autenticado tem `perfil=9` (super admin).                 |

---

## Códigos de status HTTP

| Código | Significado                                             |
|--------|---------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ter `rows: []`).      |
| `401`  | Sessão ausente ou inválida.                             |
| `403`  | Sessão com escopo limitado — acesso negado.             |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/accidents
```
