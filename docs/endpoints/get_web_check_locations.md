# `GET /api/web/check/locations`

## Visão Geral

Retorna a lista de locais cadastrados acessíveis ao usuário autenticado, filtrados pelos projetos aos quais ele pertence. Também retorna configurações de precisão GPS e intervalo de zona mista usadas pelo frontend para validar a localização antes do check-in/check-out.

| Atributo         | Valor                        |
|------------------|------------------------------|
| **Método**       | `GET`                        |
| **Path**         | `/api/web/check/locations`   |
| **Autenticação** | Cookie de sessão obrigatório |
| **Content-Type** | N/A                          |

---

## Autenticação

Requer sessão ativa via cookie. O servidor identifica o usuário pelo cookie de sessão (`web_user_chave`) e filtra os locais pelos projetos associados ao usuário em `user_project_memberships`. Se a sessão estiver ausente ou inválida, retorna HTTP 401.

---

## Parâmetros

Nenhum parâmetro é aceito. O usuário é identificado pelo cookie de sessão.

---

## Resposta

### HTTP 200 — Locais retornados com sucesso

```json
{
  "items": [
    "Escritório Principal",
    "Canteiro de Obras A",
    "Refeitório",
    "Portaria"
  ],
  "location_accuracy_threshold_meters": 100,
  "mixed_zone_interval_minutes": 30
}
```

### Campos da resposta

| Campo                              | Tipo         | Descrição                                                                                         |
|------------------------------------|--------------|---------------------------------------------------------------------------------------------------|
| `items`                            | list[string] | Nomes dos locais cadastrados filtrados pelos projetos do usuário, ordenados por nome              |
| `location_accuracy_threshold_meters` | integer    | Precisão GPS máxima aceita em metros para realizar check-in/check-out por localização. Entre 1 e 9999 |
| `mixed_zone_interval_minutes`      | integer      | Intervalo em minutos para zona mista (onde tanto check-in quanto check-out são aceitos). Mínimo 1 |

> **Nota sobre `items`:** A lista pode ser vazia se o usuário não tiver projetos ou se nenhum local estiver cadastrado para seus projetos.

---

## Códigos de status HTTP

| Código | Significado                                              |
|--------|----------------------------------------------------------|
| `200`  | Locais retornados com sucesso                            |
| `401`  | Sessão ausente, inválida ou expirada                     |

### Exemplo de erro

```json
// HTTP 401 — sem sessão ativa
{"detail": "Sessao do usuario invalida ou expirada"}
```

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
# Requer cookie de sessão obtido via POST /api/web/auth/login
curl -s "http://127.0.0.1:8000/api/web/check/locations" \
  -b cookies.txt
```
