# `GET /api/admin/users`

## Visão Geral

Retorna a lista completa de usuários cadastrados no sistema, filtrada pelo escopo de projetos do administrador autenticado. Inclui dados de identificação, perfil, vínculos de projeto e informações complementares de cada usuário.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/admin/users`                             |
| **Autenticação** | Sessão administrativa com perfil de admin      |

---

## Autenticação

Requer cookie de sessão administrativa válido e que o usuário autenticado possua perfil com acesso de administrador (`require_full_admin_session`). Caso a sessão esteja ausente ou expirada, retorna `401`. Caso o usuário não possua permissão de admin, retorna `403`.

---

## Parâmetros

Este endpoint não possui parâmetros de query, path ou body.

---

## Resposta

Array de objetos `AdminUserListRow`. A lista é filtrada pelo escopo de projetos do administrador — administradores com projetos restritos só veem usuários pertencentes aos seus projetos.

```json
[
  {
    "id": 42,
    "rfid": "A1B2C3D4",
    "nome": "João da Silva",
    "chave": "JS01",
    "perfil": 0,
    "projeto": "PROJ-A",
    "projeto_ativo": "PROJ-A",
    "projetos": ["PROJ-A", "PROJ-B"],
    "vehicle_id": null,
    "workplace": "Escritório Principal",
    "placa": null,
    "end_rua": "Rua das Flores, 123",
    "zip": "12345678",
    "email": "joao.silva@empresa.com"
  }
]
```

### Campos da resposta

| Campo          | Tipo             | Descrição                                                              |
|----------------|------------------|------------------------------------------------------------------------|
| `id`           | `integer`        | ID interno do usuário                                                  |
| `rfid`         | `string \| null` | Código RFID do usuário                                                 |
| `nome`         | `string`         | Nome completo                                                          |
| `chave`        | `string`         | Chave de 4 caracteres alfanuméricos (identificador único)              |
| `perfil`       | `integer`        | Código numérico de perfil (0 = trabalhador, 1 = admin, 9 = superadmin)|
| `projeto`      | `string`         | Nome do projeto legado/principal                                       |
| `projeto_ativo`| `string`         | Projeto ativo calculado (pode diferir de `projeto`)                    |
| `projetos`     | `array[string]`  | Lista de todos os projetos do usuário                                  |
| `vehicle_id`   | `integer \| null`| ID do veículo vinculado (transporte)                                   |
| `workplace`    | `string \| null` | Workplace operacional do usuário                                       |
| `placa`        | `string \| null` | Placa do veículo vinculado                                             |
| `end_rua`      | `string \| null` | Endereço do usuário                                                    |
| `zip`          | `string \| null` | CEP / código postal                                                    |
| `email`        | `string \| null` | E-mail do usuário (armazenado em minúsculas)                           |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia)         |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |

---

## Side effects

Nenhum. Este endpoint é somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  -H "Cookie: admin_session=<token>" \
  http://127.0.0.1:8000/api/admin/users
```
