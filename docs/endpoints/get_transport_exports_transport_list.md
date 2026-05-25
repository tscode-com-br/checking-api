# `GET /api/transport/exports/transport-list`

## Visão Geral

Exporta a lista de transporte do dia como arquivo XLSX (Excel). O arquivo contém as solicitações de transporte com os respectivos status de alocação, veículos e informações dos passageiros para a data e sentido de rota selecionados.

| Atributo         | Valor                                                             |
|------------------|-------------------------------------------------------------------|
| **Método**       | `GET`                                                             |
| **Path**         | `/api/transport/exports/transport-list`                           |
| **Autenticação** | Sessão de transporte ativa (cookie `session` com `transport_user_id`) |
| **Content-Type** | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (resposta) |

---

## Autenticação

Requer sessão de transporte válida. Retorna HTTP 401 se não houver sessão ativa.

---

## Parâmetros

### Query Parameters

| Parâmetro      | Tipo     | Obrigatório | Padrão         | Descrição                                               |
|----------------|----------|-------------|----------------|---------------------------------------------------------|
| `service_date` | `date`   | **Sim**     | —              | Data do serviço no formato `YYYY-MM-DD`.                |
| `route_kind`   | `string` | Não         | `home_to_work` | Sentido da rota: `home_to_work` ou `work_to_home`.      |

---

## Resposta

A resposta é um arquivo binário XLSX para download.

**Cabeçalhos da resposta:**

| Cabeçalho              | Valor                                                             |
|------------------------|-------------------------------------------------------------------|
| `Content-Type`         | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `Content-Disposition`  | `attachment; filename="transport-list-2026-05-25-home_to_work.xlsx"` |

O nome do arquivo segue o padrão: `transport-list-{service_date}-{route_kind}.xlsx`.

---

## Códigos de status HTTP

| Código | Significado                               |
|--------|-------------------------------------------|
| `200`  | Arquivo XLSX gerado e retornado com sucesso. |
| `401`  | Sessão de transporte ausente ou inválida. |
| `422`  | Parâmetro `service_date` ausente ou inválido. |

---

## Side effects

Nenhum. Endpoint somente leitura.

---

## Exemplo cURL (ambiente local)

```bash
# Salvar o arquivo XLSX localmente
curl -s -b cookies.txt \
  -o "transport-list.xlsx" \
  "http://127.0.0.1:8000/api/transport/exports/transport-list?service_date=2026-05-25&route_kind=home_to_work"

echo "Arquivo salvo como transport-list.xlsx"
```

Para obter o nome de arquivo original sugerido pelo servidor:

```bash
curl -s -b cookies.txt \
  -D headers.txt \
  -o "transport-list.xlsx" \
  "http://127.0.0.1:8000/api/transport/exports/transport-list?service_date=2026-05-25"

# Verificar o Content-Disposition:
grep -i "content-disposition" headers.txt
```
