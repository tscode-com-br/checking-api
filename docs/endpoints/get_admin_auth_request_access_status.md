# `GET /api/admin/auth/request-access/status`

## Visão Geral

Consulta o status de uma chave antes de enviar uma solicitação de acesso admin. Permite ao frontend decidir qual fluxo apresentar: cadastro novo, solicitação de usuário existente, ou informar que já existe admin/solicitação pendente.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/auth/request-access/status`        |
| **Autenticação** | Nenhuma (endpoint público)                     |

---

## Autenticação

Endpoint público. Não requer sessão ativa.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo     | Obrigatório | Descrição                                                      |
|-----------|----------|-------------|----------------------------------------------------------------|
| `chave`   | `string` | Sim         | Exatamente 4 caracteres alfanuméricos. Insensível a maiúsculas. |

---

## Resposta

**HTTP 200**

```json
{
  "found": true,
  "chave": "AB12",
  "has_password": true,
  "is_admin": false,
  "has_pending_request": false,
  "message": "Chave cadastrada. A solicitacao pode ser enviada."
}
```

| Campo                | Tipo      | Descrição                                                                      |
|----------------------|-----------|--------------------------------------------------------------------------------|
| `found`              | `boolean` | Se a chave corresponde a um usuário já cadastrado.                             |
| `chave`              | `string`  | Chave normalizada (maiúsculas).                                                |
| `has_password`       | `boolean` | Se o usuário existe e já possui senha definida.                                |
| `is_admin`           | `boolean` | Se o usuário já tem perfil de administrador.                                   |
| `has_pending_request`| `boolean` | Se já existe uma solicitação de acesso pendente para esta chave.               |
| `message`            | `string`  | Mensagem descritiva da situação encontrada.                                    |

### Possíveis valores de `message`

| Situação                               | Mensagem                                                       |
|----------------------------------------|----------------------------------------------------------------|
| Solicitação pendente                   | `"Ja existe uma solicitacao pendente para essa chave."`        |
| Já é administrador                     | `"Esta chave ja possui acesso administrativo."`                |
| Chave não cadastrada                   | `"Chave nao cadastrada. Continue para registrar o usuario."`   |
| Cadastrado sem senha                   | `"Esta chave ja existe, mas ainda nao possui senha cadastrada."` |
| Cadastrado com senha, sem acesso admin | `"Chave cadastrada. A solicitacao pode ser enviada."`          |

---

## Códigos de status HTTP

| Código | Significado                                                    |
|--------|----------------------------------------------------------------|
| `200`  | Consulta realizada com sucesso.                                |
| `422`  | Parâmetro `chave` ausente ou fora do formato (< 4 ou > 4 chars). |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s "http://127.0.0.1:8000/api/admin/auth/request-access/status?chave=AB12"
```
