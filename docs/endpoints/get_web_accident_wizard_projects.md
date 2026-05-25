# `GET /api/web/check/accident/wizard/projects`

## Visão Geral

Lista todos os projetos disponíveis para seleção no wizard de abertura de acidente no Check Web. Retorna id e nome de cada projeto cadastrado no sistema. Usado como primeiro passo do wizard antes de selecionar o local.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `GET`                                          |
| **Path**         | `/api/web/check/accident/wizard/projects`      |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O valor do cookie deve coincidir com o parâmetro `chave`. Em caso de falha retorna `401`.

---

## Parâmetros

### Query Parameters

| Parâmetro | Tipo   | Obrigatório | Descrição                                                    |
|-----------|--------|-------------|--------------------------------------------------------------|
| `chave`   | string | Sim         | Chave do usuário (4 caracteres alfanuméricos, ex.: `"AB12"`) |

---

## Resposta

```json
[
  {
    "id": 1,
    "name": "Projeto Leste"
  },
  {
    "id": 3,
    "name": "Projeto Norte"
  },
  {
    "id": 5,
    "name": "Projeto Sul"
  }
]
```

### Campos de cada item

| Campo  | Tipo   | Descrição                   |
|--------|--------|-----------------------------|
| `id`   | int    | ID do projeto               |
| `name` | string | Nome do projeto             |

---

## Códigos de status HTTP

| Código | Significado                                       |
|--------|---------------------------------------------------|
| `200`  | Lista retornada com sucesso                       |
| `401`  | Sessão inválida ou expirada, ou chave não confere |
| `422`  | Parâmetro `chave` ausente ou inválido             |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/web/check/accident/wizard/projects?chave=AB12"
```
