# `GET /api/admin/inactive`

## Visão Geral

Retorna a lista de usuários considerados inativos — aqueles que não realizaram check-in ou check-out por mais dias do que o limiar de inatividade configurado no projeto. A lista é filtrada pelo escopo de projetos do administrador autenticado.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/inactive`                          |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Array de objetos `InactiveUserRow` representando usuários inativos.

```json
[
  {
    "id": 28,
    "rfid": "C3D4E5F6",
    "nome": "Ana Oliveira",
    "chave": "AO04",
    "projeto": "PROJ-A",
    "projetos": ["PROJ-A"],
    "timezone_name": "Asia/Singapore",
    "timezone_label": "SGT (UTC+8)",
    "latest_action": "checkout",
    "latest_time": "2025-03-10T17:30:00+08:00",
    "inactivity_days": 76
  }
]
```

### Campos da resposta

| Campo            | Tipo                        | Descrição                                                           |
|------------------|-----------------------------|---------------------------------------------------------------------|
| `id`             | `integer`                   | ID interno do usuário                                               |
| `rfid`           | `string \| null`            | Código RFID                                                         |
| `nome`           | `string`                    | Nome completo                                                       |
| `chave`          | `string`                    | Chave de 4 caracteres                                               |
| `projeto`        | `string`                    | Projeto ativo                                                       |
| `projetos`       | `array[string]`             | Todos os projetos do usuário                                        |
| `timezone_name`  | `string`                    | Nome do fuso horário do projeto                                     |
| `timezone_label` | `string`                    | Rótulo legível do fuso horário                                      |
| `latest_action`  | `"checkin" \| "checkout"`   | Tipo da última ação registrada                                      |
| `latest_time`    | `datetime`                  | Timestamp da última atividade (UTC)                                 |
| `inactivity_days`| `integer`                   | Número de dias sem atividade desde `latest_time`                    |

**Critério de inatividade:** um usuário é considerado inativo quando `inactivity_days` supera o campo `inactivity_days_threshold` do seu projeto (padrão: 60 dias).

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia)         |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |

---

## Side effects

- Sincroniza o status de inatividade dos usuários antes de retornar (`sync_user_inactivity`).
- Se algum usuário atingir o limiar de descadastro por inatividade (`apply_inactivity_descadastro`), é removido automaticamente e emite notificação SSE para o admin e para o Check Web.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/inactive
```
