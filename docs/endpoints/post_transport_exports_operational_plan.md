# `POST /api/transport/exports/operational-plan`

## Visão Geral

Exporta o plano operacional de transporte como arquivo XLSX (Excel), com base em uma proposta operacional. O arquivo inclui as decisões de alocação da proposta (veículos, passageiros, horários de embarque) organizadas para uso operacional em campo.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `POST`                                                            |
| **Path**         | `/api/transport/exports/operational-plan`                         |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/json` (requisição) / `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (resposta) |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Request Body

O corpo é um objeto `TransportOperationalProposal` completo (qualquer status: `draft`, `approved` ou `applied`):

```json
{
  "proposal_key": "proposal:home_to_work:2026-05-25:manual:20260525T073000",
  "proposal_status": "approved",
  "origin": "manual",
  "created_at": "2026-05-25T07:30:00+08:00",
  "snapshot": {
    "service_date": "2026-05-25",
    "route_kind": "home_to_work",
    "...": "campos completos do snapshot"
  },
  "decisions": [
    {
      "request_id": 10,
      "request_kind": "regular",
      "service_date": "2026-05-25",
      "route_kind": "home_to_work",
      "suggested_status": "confirmed",
      "vehicle_id": 5,
      "boarding_time": "07:30",
      "response_message": null,
      "rationale": null
    }
  ],
  "summary": { "...": "summary" },
  "validation_issues": [],
  "audit_trail": []
}
```

A data e o sentido de rota para o export são extraídos de `proposal.snapshot.service_date` e `proposal.snapshot.route_kind`.

---

## Resposta

A resposta é um arquivo binário XLSX para download.

**Cabeçalhos da resposta:**

| Cabeçalho              | Valor                                                                      |
|------------------------|----------------------------------------------------------------------------|
| `Content-Type`         | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`        |
| `Content-Disposition`  | `attachment; filename="operational-plan-2026-05-25-home_to_work.xlsx"`     |

O nome do arquivo segue o padrão: `operational-plan-{service_date}-{route_kind}.xlsx`.

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Arquivo XLSX gerado e retornado com sucesso. |
| `401`  | Sessão de transporte ausente ou inválida. |
| `422`  | Corpo da requisição inválido ou incompleto. |

---

## Side effects

Nenhum. Endpoint somente leitura em relação ao banco de dados.

---

## Exemplo cURL (ambiente local)

```bash
# Salvar o plano operacional como XLSX
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d @proposta.json \
  -o "plano-operacional.xlsx" \
  http://127.0.0.1:8000/api/transport/exports/operational-plan

echo "Arquivo salvo como plano-operacional.xlsx"
```

Para obter o nome sugerido pelo servidor:

```bash
curl -s -b cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d @proposta.json \
  -D headers.txt \
  -o "plano-operacional.xlsx" \
  http://127.0.0.1:8000/api/transport/exports/operational-plan

grep -i "content-disposition" headers.txt
```
