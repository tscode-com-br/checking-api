# `GET /api/web/check/accident/wizard/locations`

## Visão Geral

Lista os locais cadastrados associados a um projeto específico para uso no wizard de abertura de acidente. O frontend usa este endpoint no segundo passo do wizard (após selecionar o projeto) para apresentar os locais disponíveis. Também é possível usar um local personalizado (texto livre) caso o local do acidente não esteja listado.

| Atributo         | Valor                                               |
|------------------|-----------------------------------------------------|
| **Método**       | `GET`                                               |
| **Path**         | `/api/web/check/accident/wizard/locations`          |
| **Autenticação** | Cookie de sessão + chave deve corresponder          |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O valor do cookie deve coincidir com o parâmetro `chave`. Em caso de falha retorna `401`.

---

## Parâmetros

### Query Parameters

| Parâmetro    | Tipo   | Obrigatório | Descrição                                                    |
|--------------|--------|-------------|--------------------------------------------------------------|
| `chave`      | string | Sim         | Chave do usuário (4 caracteres alfanuméricos, ex.: `"AB12"`) |
| `project_id` | int    | Sim         | ID do projeto (obtido no passo anterior do wizard)           |

---

## Resposta

```json
[
  {
    "id": 12,
    "name": "Área de Extração B",
    "registered": true
  },
  {
    "id": 15,
    "name": "Galpão de Equipamentos",
    "registered": true
  },
  {
    "id": 20,
    "name": "Portaria Principal",
    "registered": true
  }
]
```

### Campos de cada item

| Campo        | Tipo   | Descrição                                                                   |
|--------------|--------|-----------------------------------------------------------------------------|
| `id`         | int    | ID do local cadastrado em `managed_locations`                               |
| `name`       | string | Nome do local                                                               |
| `registered` | bool   | Sempre `true` neste endpoint — indica que o local está na base cadastrada   |

> **Quando nenhum local da lista corresponder ao local real do acidente**, o usuário pode usar o campo `custom_location_name` em `POST /api/web/check/accident/open` para informar um nome livre.

---

## Códigos de status HTTP

| Código | Significado                                       |
|--------|---------------------------------------------------|
| `200`  | Lista retornada com sucesso (pode ser vazia `[]`) |
| `401`  | Sessão inválida ou expirada, ou chave não confere |
| `404`  | Projeto não encontrado                            |
| `422`  | Parâmetros ausentes ou inválidos                  |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s \
  --cookie "session=<cookie_de_sessao>" \
  "http://127.0.0.1:8000/api/web/check/accident/wizard/locations?chave=AB12&project_id=3"
```
