# `POST /api/web/check/accident/acknowledge`

## Visão Geral

Registra a ciência do usuário autenticado sobre o acidente em curso ("Ciente" no app). Altera o campo `awareness_status` do relatório do usuário de `"waiting"` para `"acknowledged"`. Essa ação é necessária antes de o usuário poder interagir com outras funcionalidades do Modo Acidente.

Se `accident_id` for fornecido, reconhece especificamente aquele acidente (útil quando múltiplos acidentes estão ativos). Caso omitido, usa o comportamento legado: seleciona automaticamente o primeiro acidente ativo que corresponda ao projeto do usuário.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/web/check/accident/acknowledge`          |
| **Autenticação** | Cookie de sessão + chave deve corresponder     |
| **Content-Type** | `application/json`                             |

---

## Autenticação

Requer cookie de sessão `web_user_chave`. O campo `chave` no body deve coincidir com o valor no cookie. Em caso de falha retorna `401`.

---

## Request Body

### Reconhecimento do acidente ativo do projeto (comportamento padrão)

```json
{
  "chave": "AB12"
}
```

### Reconhecimento de um acidente específico

```json
{
  "chave": "AB12",
  "accident_id": 5
}
```

### Campos do request body

| Campo         | Tipo        | Obrigatório | Descrição                                                                                    |
|---------------|-------------|-------------|----------------------------------------------------------------------------------------------|
| `chave`       | string      | Sim         | Chave do usuário (4 caracteres alfanuméricos A-Z 0-9)                                        |
| `accident_id` | int \| null | Não         | ID do acidente a reconhecer. Se omitido, usa o primeiro acidente ativo do projeto do usuário |

---

## Resposta

```json
{
  "ok": true,
  "accident_id": 5
}
```

### Campos da resposta

| Campo         | Tipo | Descrição                                               |
|---------------|------|---------------------------------------------------------|
| `ok`          | bool | Sempre `true` em caso de sucesso                        |
| `accident_id` | int  | ID do acidente que foi reconhecido                      |

---

## Códigos de status HTTP

| Código | Significado                                                      |
|--------|------------------------------------------------------------------|
| `200`  | Ciência registrada com sucesso                                   |
| `401`  | Sessão inválida ou expirada, ou chave não confere                |
| `404`  | `accident_id` informado não corresponde a um acidente ativo      |
| `409`  | Nenhum acidente em curso                                         |
| `422`  | Campos inválidos (chave fora do padrão)                          |

---

## Side effects

- Cria (se inexistente) ou atualiza o registro em `accident_user_reports` com `awareness_status="acknowledged"`.
- Grava evento em `check_events` com `action="accident_ack"`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12"}' \
  "http://127.0.0.1:8000/api/web/check/accident/acknowledge"
```

### Reconhecendo um acidente específico

```bash
curl -s -X POST \
  --cookie "session=<cookie_de_sessao>" \
  -H "Content-Type: application/json" \
  -d '{"chave": "AB12", "accident_id": 5}' \
  "http://127.0.0.1:8000/api/web/check/accident/acknowledge"
```
