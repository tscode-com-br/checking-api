# `POST /api/admin/auth/request-access`

## Visão Geral

Solicita acesso admin para uma chave existente ou nova, enviando todos os dados necessários em uma única chamada. Diferente do endpoint de autoatendimento, este espera `chave`, `nome_completo` e `senha` obrigatoriamente — não há cadastro implícito de usuário. Destinado a formulários mais diretos onde os dados já estão disponíveis.

| Atributo         | Valor                                    |
|------------------|------------------------------------------|
| **Método**       | `POST`                                   |
| **Path**         | `/api/admin/auth/request-access`         |
| **Autenticação** | Nenhuma (endpoint público)               |
| **Content-Type** | `application/json`                       |

---

## Autenticação

Endpoint público.

---

## Parâmetros

### Request Body

```json
{
  "chave": "AB12",
  "nome_completo": "João da Silva",
  "senha": "segredo123"
}
```

| Campo           | Tipo     | Obrigatório | Validação                                                        |
|-----------------|----------|-------------|------------------------------------------------------------------|
| `chave`         | `string` | Sim         | 4 caracteres alfanuméricos (A-Z, 0-9). Convertido para maiúsculas. |
| `nome_completo` | `string` | Sim         | 3–180 caracteres.                                                |
| `senha`         | `string` | Sim         | 3–20 caracteres.                                                 |

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "ok": true,
  "message": "Solicitacao enviada para aprovacao de um administrador."
}
```

---

## Códigos de status HTTP

| Código | Significado                                                                              |
|--------|------------------------------------------------------------------------------------------|
| `200`  | Solicitação criada com sucesso.                                                           |
| `409`  | Chave já pertence a um administrador ativo, ou já existe solicitação pendente para ela.  |
| `422`  | Dados inválidos (campos ausentes ou formato incorreto).                                   |

---

## Side effects

- Cria registro em `admin_access_requests` com a senha hasheada e `requested_profile=1`.
- **Não** cria ou modifica o registro em `users` — apenas registra a solicitação.
- Grava evento em `check_events` com `action="admin_request"`.
- Notifica o painel admin via SSE (`reason="admin"` e `reason="event"`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST http://127.0.0.1:8000/api/admin/auth/request-access \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "nome_completo": "João da Silva", "senha": "segredo123"}'
```
