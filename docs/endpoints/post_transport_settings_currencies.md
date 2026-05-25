# `POST /api/transport/settings/currencies`

## Visão Geral

Cria uma nova opção de moeda disponível para uso nas configurações de precificação de transporte. Após a criação, a moeda fica disponível para seleção no campo `price_currency_code` do `PUT /api/transport/settings`.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/settings/currencies`                              |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json`                                                |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Request Body

```json
{
  "code": "BRL",
  "display_label": "Real Brasileiro"
}
```

| Campo           | Tipo           | Obrigatório | Restrições               | Descrição                                                  |
|-----------------|----------------|-------------|--------------------------|-------------------------------------------------------------|
| `code`          | `string`       | Sim         | 2–12 chars, normalizado para maiúsculas | Código único da moeda (ex.: `"USD"`, `"BRL"`, `"SGD"`). |
| `display_label` | `string\|null` | Não         | Máx. 80 caracteres       | Rótulo legível da moeda para exibição no frontend.          |

---

## Resposta

```json
{
  "code": "BRL",
  "display_label": "Real Brasileiro"
}
```

| Campo           | Tipo           | Descrição                              |
|-----------------|----------------|----------------------------------------|
| `code`          | `string`       | Código da moeda criada.                |
| `display_label` | `string\|null` | Rótulo da moeda.                       |

---

## Erros estruturados

Quando o código já existe:

```json
{
  "detail": {
    "message": "Currency code already exists.",
    "message_key": "warnings.currencyAlreadyExists",
    "message_params": {},
    "error_code": "transport_currency_code_duplicate",
    "issues": [{"code": "transport_currency_code_duplicate"}]
  }
}
```

---

## Códigos de status HTTP

| Código | Significado                                   |
|--------|-----------------------------------------------|
| `200`  | Moeda criada com sucesso.                     |
| `401`  | Sessão de transporte ausente ou inválida.     |
| `409`  | Código de moeda duplicado.                    |
| `422`  | Corpo da requisição inválido.                 |

---

## Side effects

- Persiste a nova opção de moeda no banco de dados.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"code": "BRL", "display_label": "Real Brasileiro"}' \
  http://127.0.0.1:8000/api/transport/settings/currencies | python -m json.tool
```
