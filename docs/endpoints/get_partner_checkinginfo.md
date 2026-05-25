# `GET /api/partner/checkinginfo`

## Visão Geral

Retorna a situação atual de check-in e checkout de todos os usuários ativos (não inativos). Filtrado para exibir apenas os usuários com atividade recente. Destinado a sistemas parceiros que precisam consultar a presença em tempo real.

| Atributo         | Valor                                      |
|------------------|--------------------------------------------|
| **Método**       | `GET`                                      |
| **Path**         | `/api/partner/checkinginfo`                |
| **Autenticação** | Header `X-API-Key`                         |
| **Tags**         | `partner`                                  |

---

## Autenticação

Requer o header `X-API-Key` com a chave secreta configurada para o endpoint `checkinginfo`. As chaves são gerenciadas via `POST /api/partner/admin/endpoint-keys/{endpoint_name}/rotate` por administradores com `perfil=9`.

```
X-API-Key: a1b2c3d4e5f67890a1b2c3d4e5f67890
```

### Resposta em caso de falha de autenticação

**Endpoint não configurado (chave ainda não foi gerada):**
```json
{
  "detail": "Endpoint nao configurado."
}
```

**Chave inválida:**
```json
{
  "detail": "Chave de acesso invalida."
}
```

---

## Parâmetros

Nenhum parâmetro de query ou path.

---

## Resposta

### 200 OK

```json
{
  "ok": true,
  "total": 2,
  "entries": [
    {
      "nome": "João Silva",
      "chave": "AB12",
      "projeto": "Projeto Alpha",
      "atividade": "check-in",
      "horario": "2024-05-25T08:30:00+08:00",
      "local": "Portaria Principal",
      "assiduidade": "Normal"
    },
    {
      "nome": "Maria Santos",
      "chave": "CD34",
      "projeto": "Projeto Alpha",
      "atividade": "check-out",
      "horario": "2024-05-25T17:05:00+08:00",
      "local": "Portaria Principal",
      "assiduidade": "Normal"
    }
  ]
}
```

| Campo    | Tipo    | Descrição                                         |
|----------|---------|---------------------------------------------------|
| `ok`     | `boolean` | Sempre `true`                                   |
| `total`  | `integer` | Número total de entradas retornadas             |
| `entries`| `array`   | Lista de registros de presença (ver abaixo)     |

### Campos de cada entrada em `entries`

| Campo        | Tipo              | Descrição                                                    |
|--------------|-------------------|--------------------------------------------------------------|
| `nome`       | `string`          | Nome completo do usuário                                     |
| `chave`      | `string`          | Chave de identificação do usuário (4 caracteres)            |
| `projeto`    | `string`          | Projeto ativo do usuário                                     |
| `atividade`  | `string`          | `"check-in"` ou `"check-out"`                               |
| `horario`    | `datetime\|null` | Timestamp da última atividade com timezone do projeto        |
| `local`      | `string\|null`   | Local onde a atividade foi registrada                        |
| `assiduidade`| `string`          | `"Normal"` (on-time) ou `"Retroativo"` (retroativo)         |

> **Ordenação**: entradas são ordenadas por `horario` decrescente (mais recente primeiro). Usuários sem atividade registrada ou com inatividade prolongada são excluídos.

---

## Códigos de status HTTP

| Código | Significado                             |
|--------|-----------------------------------------|
| `200`  | Sucesso                                 |
| `403`  | Endpoint não configurado ou chave inválida |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s http://127.0.0.1:8000/api/partner/checkinginfo \
  -H "X-API-Key: a1b2c3d4e5f67890a1b2c3d4e5f67890"
```
