# `POST /api/web/check/location`

## Visão Geral

Recebe as coordenadas GPS do usuário e determina se elas correspondem a algum local cadastrado nos projetos do usuário. Retorna o resultado do matching com detalhes de distância e precisão. Usado pelo frontend antes de realizar o check-in/check-out para identificar automaticamente o local.

| Atributo         | Valor                        |
|------------------|------------------------------|
| **Método**       | `POST`                       |
| **Path**         | `/api/web/check/location`    |
| **Autenticação** | Cookie de sessão obrigatório |
| **Content-Type** | `application/json`           |

---

## Autenticação

Requer sessão ativa via cookie. O servidor identifica o usuário pelo cookie de sessão e usa seus projetos associados para filtrar os locais candidatos ao matching. Se a sessão estiver ausente ou inválida, retorna HTTP 401.

---

## Parâmetros

### Request Body

```json
{
  "latitude": 3.1569,
  "longitude": 101.7123,
  "accuracy_meters": 15.5
}
```

| Campo             | Tipo         | Obrigatório | Descrição                                                                 |
|-------------------|--------------|-------------|---------------------------------------------------------------------------|
| `latitude`        | float        | Sim         | Latitude GPS em graus decimais. Intervalo: -90.0 a 90.0                   |
| `longitude`       | float        | Sim         | Longitude GPS em graus decimais. Intervalo: -180.0 a 180.0                |
| `accuracy_meters` | float\|null  | Não         | Precisão do GPS em metros (`null` ou omitido = precisão desconhecida). Deve ser ≥ 0 |

---

## Resposta

### HTTP 200 — Local identificado (matching bem-sucedido)

```json
{
  "matched": true,
  "resolved_local": "Canteiro de Obras A",
  "label": "Canteiro de Obras A",
  "status": "matched",
  "message": "Localizacao identificada em Canteiro de Obras A.",
  "accuracy_meters": 15.5,
  "accuracy_threshold_meters": 100,
  "minimum_checkout_distance_meters": 500,
  "nearest_workplace_distance_meters": 42.3
}
```

### HTTP 200 — Fora de todos os locais cadastrados

```json
{
  "matched": false,
  "resolved_local": null,
  "label": "Localização não Cadastrada",
  "status": "not_in_known_location",
  "message": "",
  "accuracy_meters": 18.0,
  "accuracy_threshold_meters": 100,
  "minimum_checkout_distance_meters": 500,
  "nearest_workplace_distance_meters": 1250.7
}
```

### HTTP 200 — Fora do local de trabalho mas dentro do raio de checkout

```json
{
  "matched": false,
  "resolved_local": null,
  "label": "300m de Canteiro de Obras A",
  "status": "outside_workplace",
  "message": "",
  "accuracy_meters": 12.0,
  "accuracy_threshold_meters": 100,
  "minimum_checkout_distance_meters": 500,
  "nearest_workplace_distance_meters": 300.0
}
```

### HTTP 200 — Precisão GPS insuficiente

```json
{
  "matched": false,
  "resolved_local": null,
  "label": "Precisao insuficiente",
  "status": "accuracy_too_low",
  "message": "Nao foi possivel confirmar o local porque a precisao da localizacao esta acima do limite permitido.",
  "accuracy_meters": 250.0,
  "accuracy_threshold_meters": 100,
  "minimum_checkout_distance_meters": 500,
  "nearest_workplace_distance_meters": null
}
```

### HTTP 200 — Usuário sem locais cadastrados

```json
{
  "matched": false,
  "resolved_local": null,
  "label": "Sem localização cadastrada",
  "status": "no_known_locations",
  "message": "Nao ha localizacoes conhecidas cadastradas para validar a posicao nos projetos cadastrados do usuario.",
  "accuracy_meters": 10.0,
  "accuracy_threshold_meters": 100,
  "minimum_checkout_distance_meters": 500,
  "nearest_workplace_distance_meters": null
}
```

### Campos da resposta

| Campo                              | Tipo         | Descrição                                                                                          |
|------------------------------------|--------------|-----------------------------------------------------------------------------------------------------|
| `matched`                          | boolean      | `true` se a posição foi identificada dentro de um local cadastrado                                 |
| `resolved_local`                   | string\|null | Nome do local resolvido para uso no check-in/check-out; `null` se não houve matching               |
| `label`                            | string       | Rótulo legível para exibição na interface (pode diferir de `resolved_local`)                       |
| `status`                           | string       | Código do resultado. Valores possíveis abaixo                                                      |
| `message`                          | string       | Mensagem descritiva do resultado (pode ser vazia)                                                  |
| `accuracy_meters`                  | float\|null  | Precisão GPS informada na requisição                                                               |
| `accuracy_threshold_meters`        | integer      | Limite de precisão GPS configurado no sistema (1–9999 metros)                                      |
| `minimum_checkout_distance_meters` | integer      | Distância mínima do local de trabalho para checkout remoto ser aceito                             |
| `nearest_workplace_distance_meters`| float\|null  | Distância em metros até o local cadastrado mais próximo; `null` se não calculado                   |

### Valores possíveis de `status`

| Status                  | Descrição                                                                            |
|-------------------------|--------------------------------------------------------------------------------------|
| `matched`               | Posição identificada dentro de um local cadastrado                                   |
| `accuracy_too_low`      | Precisão GPS superior ao limite configurado (`accuracy_meters > accuracy_threshold`) |
| `not_in_known_location` | Posição não corresponde a nenhum local cadastrado                                    |
| `outside_workplace`     | Fora do local mas dentro do raio de checkout mínimo (checkout remoto possível)      |
| `no_known_locations`    | Nenhum local cadastrado para os projetos do usuário                                  |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Resultado retornado (inclui casos de não-matching)   |
| `401`  | Sessão ausente, inválida ou expirada                 |
| `422`  | Coordenadas fora dos intervalos válidos              |

### Exemplos de erros

```json
// HTTP 401 — sem sessão
{"detail": "Sessao do usuario invalida ou expirada"}

// HTTP 422 — latitude inválida
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "latitude"],
      "msg": "Value error, Latitude must be between -90 and 90"
    }
  ]
}
```

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST "http://127.0.0.1:8000/api/web/check/location" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "latitude": 3.1569,
    "longitude": 101.7123,
    "accuracy_meters": 15.5
  }'
```
