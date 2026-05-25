# `POST /api/admin/locations/settings`

## Visão Geral

Atualiza as configurações globais de localização GPS — especificamente o limiar de precisão de sinal GPS aceito pelo sistema. Requisições de check-in/check-out com precisão GPS pior do que o limiar configurado são rejeitadas ou sinalizadas como imprecisas.

| Atributo         | Valor                                          |
|------------------|------------------------------------------------|
| **Método**       | `POST`                                         |
| **Path**         | `/api/admin/locations/settings`                |
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
  "location_accuracy_threshold_meters": 50
}
```

### Campos do body

| Campo                               | Tipo      | Obrigatório | Descrição                                                                    |
|-------------------------------------|-----------|-------------|------------------------------------------------------------------------------|
| `location_accuracy_threshold_meters`| `integer` | Sim         | Limiar máximo de precisão GPS aceito, em metros (1–9999). Valores menores são mais restritivos. |

**Interpretação:** se um dispositivo reporta `accuracy = 80m` e o limiar configurado é `50m`, a requisição será considerada imprecisa. Recomenda-se valores entre 30 e 100 metros para ambientes externos.

---

## Resposta

```json
{
  "ok": true,
  "message": "Configuracoes de localizacao salvas com sucesso.",
  "message_key": null,
  "message_params": {},
  "error_code": null,
  "issues": [],
  "technical_detail": null,
  "location_accuracy_threshold_meters": 50
}
```

| Campo                               | Tipo      | Descrição                                     |
|-------------------------------------|-----------|-----------------------------------------------|
| `ok`                                | `boolean` | `true` em caso de sucesso                     |
| `message`                           | `string`  | Mensagem de confirmação                       |
| `location_accuracy_threshold_meters`| `integer` | Novo valor configurado (confirmação)          |

---

## Códigos de status HTTP

| Código | Significado                                          |
|--------|------------------------------------------------------|
| `200`  | Configuração salva com sucesso                       |
| `401`  | Sessão administrativa inválida ou expirada           |
| `403`  | Usuário não possui permissão de administrador        |
| `422`  | Valor fora do intervalo permitido (1–9999)           |

---

## Side effects

- Atualiza (ou cria) o registro de configuração em `location_settings`.
- Emite notificação SSE para o painel admin.
- Grava evento em `check_events` com `action="location_config"`.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -X POST \
  -H "Cookie: admin_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{"location_accuracy_threshold_meters": 50}' \
  http://127.0.0.1:8000/api/admin/locations/settings
```
