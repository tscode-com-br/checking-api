# `POST /api/admin/users`

## Visão Geral

Cria ou atualiza um usuário (upsert). Se um `user_id` ou `rfid` já existente for fornecido, atualiza o registro; caso contrário, cria um novo usuário. Ao criar um novo usuário a partir de um RFID pendente de cadastro, o registro pendente correspondente é removido automaticamente.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/admin/users`                             |
| **Autenticação** | Sessão administrativa com perfil de admin      |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

### Request Body

```json
{
  "user_id": null,
  "rfid": "A1B2C3D4",
  "nome": "João da Silva",
  "chave": "JS01",
  "perfil": 0,
  "projeto": "PROJ-A",
  "projetos": ["PROJ-A", "PROJ-B"],
  "workplace": "Escritório Principal",
  "vehicle_id": null,
  "placa": null,
  "end_rua": "Rua das Flores, 123",
  "zip": "12345678",
  "email": "joao.silva@empresa.com"
}
```

### Campos do body

| Campo        | Tipo             | Obrigatório | Descrição                                                                                               |
|--------------|------------------|-------------|---------------------------------------------------------------------------------------------------------|
| `user_id`    | `integer \| null`| Condicional | ID do usuário para atualização. Obrigatório se `rfid` não for informado.                               |
| `rfid`       | `string \| null` | Condicional | Código RFID (4–64 caracteres). Obrigatório para novos usuários. `user_id` ou `rfid` deve ser fornecido.|
| `nome`       | `string`         | Sim         | Nome completo (3–180 caracteres)                                                                        |
| `chave`      | `string`         | Sim         | Chave de exatamente 4 caracteres alfanuméricos (convertida para maiúsculas)                             |
| `perfil`     | `integer`        | Não         | Código de perfil (0–999, padrão `0`)                                                                   |
| `projeto`    | `string \| null` | Condicional | Projeto ativo do usuário (deve pertencer a `projetos`). Obrigatório se `projetos` não for informado.   |
| `projetos`   | `array[string] \| null` | Condicional | Lista de projetos do usuário. Se omitido, usa `projeto` como único projeto.                  |
| `workplace`  | `string \| null` | Não         | Nome do workplace (deve existir no cadastro)                                                            |
| `vehicle_id` | `integer \| null`| Não         | ID do veículo vinculado                                                                                 |
| `placa`      | `string \| null` | Não         | Placa do veículo (até 15 caracteres, maiúsculas)                                                        |
| `end_rua`    | `string \| null` | Não         | Endereço (até 255 caracteres)                                                                           |
| `zip`        | `string \| null` | Não         | CEP / código postal (até 10 caracteres)                                                                 |
| `email`      | `string \| null` | Não         | E-mail do usuário (até 255 caracteres, armazenado em minúsculas)                                        |

**Regras de validação:**
- `chave` deve ser única — retorna `409` se já pertencer a outro usuário.
- `rfid` deve ser único — retorna `409` se já pertencer a outro usuário.
- Para novos usuários, `rfid` é obrigatório.
- Projetos devem existir no catálogo e estar dentro do escopo do administrador.
- Não é possível remover o perfil de admin do único administrador ativo.

---

## Resposta

```json
{
  "ok": true,
  "rfid": "A1B2C3D4",
  "user_id": 42,
  "linked_existing_user": false
}
```

| Campo                  | Tipo      | Descrição                                                                     |
|------------------------|-----------|-------------------------------------------------------------------------------|
| `ok`                   | `boolean` | `true` em caso de sucesso                                                     |
| `rfid`                 | `string`  | RFID do usuário criado/atualizado                                             |
| `user_id`              | `integer` | ID do usuário criado/atualizado                                               |
| `linked_existing_user` | `boolean` | `true` se um usuário existente sem RFID foi vinculado ao RFID fornecido       |

---

## Códigos de status HTTP

| Código | Significado                                                             |
|--------|-------------------------------------------------------------------------|
| `200`  | Usuário criado ou atualizado com sucesso                                |
| `400`  | RFID ausente para novo usuário                                          |
| `401`  | Sessão administrativa inválida ou expirada                              |
| `403`  | Sem permissão ou tentativa de vincular projetos fora do escopo          |
| `404`  | `user_id`, workplace ou veículo não encontrado                          |
| `409`  | Conflito: `chave` ou `rfid` já pertence a outro usuário; ou tentativa de remover o único administrador |
| `422`  | Erro de validação do payload (campo inválido)                           |

---

## Side effects

- Cria ou atualiza o registro do usuário em `users`.
- Atualiza memberships de projeto em `user_project_memberships`.
- Se o RFID estava em `pending_registrations`, o registro pendente é removido.
- Se a `chave` mudou, atualiza `chave` em `user_sync_events` e `checking_history`.
- Emite notificação SSE para o painel admin (`notify_admin_data_changed`) e grava evento em `check_events`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: admin_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rfid": "A1B2C3D4",
    "nome": "João da Silva",
    "chave": "JS01",
    "perfil": 0,
    "projeto": "PROJ-A"
  }' \
  http://127.0.0.1:8000/api/admin/users
```
