# `GET /api/admin/auth/session`

## Visão Geral

Retorna o estado atual da sessão admin: se o usuário está autenticado e, em caso positivo, os dados de identidade (perfil, abas liberadas, escopo de acesso).

| Atributo         | Valor                           |
|------------------|---------------------------------|
| **Método**       | `GET`                           |
| **Path**         | `/api/admin/auth/session`       |
| **Autenticação** | Cookie de sessão (opcional — retorna `authenticated: false` se ausente) |

---

## Autenticação

Não requer sessão obrigatória. Retorna `authenticated: false` quando o cookie está ausente ou inválido. É o endpoint usado pelo frontend para verificar o estado de login ao carregar a SPA.

---

## Parâmetros

Nenhum.

---

## Resposta

**HTTP 200 — Sem sessão ativa**

```json
{
  "authenticated": false,
  "admin": null
}
```

**HTTP 200 — Com sessão ativa**

```json
{
  "authenticated": true,
  "admin": {
    "id": 7,
    "chave": "AB12",
    "nome_completo": "João da Silva",
    "perfil": 1,
    "can_view_activity_time": true,
    "access_scope": "full",
    "allowed_tabs": ["checkin", "checkout", "forms", "inactive", "cadastro", "relatorios", "eventos", "banco-dados", "acidente"]
  }
}
```

### Campos do objeto `admin`

| Campo                   | Tipo      | Descrição                                                                                     |
|-------------------------|-----------|-----------------------------------------------------------------------------------------------|
| `id`                    | `integer` | ID interno do usuário (`users.id`).                                                           |
| `chave`                 | `string`  | Chave de 4 caracteres do administrador.                                                       |
| `nome_completo`         | `string`  | Nome completo.                                                                                |
| `perfil`                | `integer` | Perfil numérico (ex.: `1` = admin limitado, `9` = super admin).                               |
| `can_view_activity_time`| `boolean` | Se o perfil tem permissão para ver horários de checkin/checkout.                              |
| `access_scope`          | `string`  | `"limited"` ou `"full"` — determina quais seções do painel estão disponíveis.                 |
| `allowed_tabs`          | `array`   | Lista de abas liberadas: `checkin`, `checkout`, `forms`, `inactive`, `cadastro`, `relatorios`, `eventos`, `banco-dados`, `acidente`. |

---

## Códigos de status HTTP

| Código | Significado       |
|--------|-------------------|
| `200`  | Sempre retornado. |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/auth/session
```
