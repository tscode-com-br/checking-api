# `POST /api/admin/locations/auto-checkout-distances`

## Visão Geral

Salva as distâncias mínimas de check-out automático por projeto. Este endpoint configura, para cada projeto, a distância em metros que o usuário precisa estar da localização cadastrada para que o check-out automático por GPS seja acionado. Substitui os valores anteriores dos projetos informados.

> **Nota:** O path real deste endpoint é `/api/admin/locations/auto-checkout-distances`. Ele gerencia a configuração de distância de checkout por projeto, complementando o campo `minimum_checkout_distance_meters` de `PUT /api/admin/projects/{project_id}`.

| Atributo         | Valor                                                        |
|------------------|--------------------------------------------------------------|
| **Método**       | `POST`                                                       |
| **Path**         | `/api/admin/locations/auto-checkout-distances`               |
| **Autenticação** | Sessão administrativa com perfil de admin                    |
| **Content-Type** | `application/json`                                           |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Request Body

```json
{
  "items": [
    {
      "project_name": "PROJ-A",
      "minimum_checkout_distance_meters": 1500
    },
    {
      "project_name": "PROJ-B",
      "minimum_checkout_distance_meters": 3000
    }
  ]
}
```

### Campos do body

| Campo    | Tipo    | Obrigatório | Descrição                                 |
|----------|---------|-------------|-------------------------------------------|
| `items`  | `array` | Sim         | Lista de configurações por projeto        |

### Campos de cada item em `items`

| Campo                               | Tipo      | Obrigatório | Descrição                                              |
|-------------------------------------|-----------|-------------|--------------------------------------------------------|
| `project_name`                      | `string`  | Sim         | Nome do projeto (2–120 chars, normalizado para uppercase). Deve existir no catálogo. |
| `minimum_checkout_distance_meters`  | `integer` | Sim         | Distância mínima em metros (1–999999)                 |

**Restrições:**
- Não é permitido repetir o mesmo projeto na mesma requisição.
- Os projetos devem estar dentro do escopo do administrador autenticado.
- O administrador deve ter ao menos um projeto vinculado.

---

## Resposta

```json
{
  "ok": true,
  "message": "Distancias minimas para check-out automatico salvas com sucesso.",
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null,
  "items": [
    {
      "project_name": "PROJ-A",
      "minimum_checkout_distance_meters": 1500
    },
    {
      "project_name": "PROJ-B",
      "minimum_checkout_distance_meters": 3000
    }
  ]
}
```

| Campo    | Tipo    | Descrição                                                      |
|----------|---------|----------------------------------------------------------------|
| `ok`     | `boolean` | `true` em caso de sucesso                                    |
| `message`| `string`  | Mensagem de confirmação                                      |
| `items`  | `array`   | Lista atualizada de configurações dentro do escopo do admin  |

---

## Códigos de status HTTP

| Código | Significado                                                        |
|--------|--------------------------------------------------------------------|
| `200`  | Configurações salvas com sucesso                                   |
| `401`  | Sessão administrativa inválida ou expirada                         |
| `403`  | Sem permissão; admin sem projetos vinculados; ou projeto fora do escopo |
| `422`  | Erro de validação do payload (projeto duplicado, valor inválido)   |

---

## Side effects

- Insere ou atualiza registros em `project_location_settings` (tabela de configurações por projeto).
- Emite notificação SSE para o painel admin.
- Grava evento em `check_events` com `action="location_config"`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: admin_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"project_name": "PROJ-A", "minimum_checkout_distance_meters": 1500}
    ]
  }' \
  http://127.0.0.1:8000/api/admin/locations/auto-checkout-distances
```
