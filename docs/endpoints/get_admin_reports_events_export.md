# `GET /api/admin/reports/events/export`

## Visão Geral

Gera e baixa um arquivo XLSX (Excel) com o relatório de eventos de check-in e check-out de um usuário específico. O arquivo contém cabeçalho com nome e chave do usuário, metadados do relatório e uma tabela de eventos. Equivalente à versão JSON de `GET /api/admin/reports/events`, mas em formato planilha para exportação.

| Atributo         | Valor                                                                      |
|------------------|----------------------------------------------------------------------------|
| **Método**       | `GET`                                                                      |
| **Path**         | `/api/admin/reports/events/export`                                         |
| **Autenticação** | Sessão administrativa completa (cookie)                                    |
| **Content-Type** | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (resposta) |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

### Query Parameters

Exatamente um dos parâmetros `chave` ou `nome` deve ser fornecido. Informar os dois simultaneamente resulta em `400`.

| Parâmetro | Tipo     | Obrigatório       | Descrição                                                            |
|-----------|----------|-------------------|----------------------------------------------------------------------|
| `chave`   | `string` | Condicional (`*`) | Chave de 4 caracteres alfanuméricos do usuário (ex.: `AB12`).        |
| `nome`    | `string` | Condicional (`*`) | Nome completo do usuário. Busca por correspondência exata normalizada.|

`(*)` Informe `chave` **ou** `nome`, nunca os dois.

---

## Resposta

**HTTP 200 — Sucesso**

Arquivo XLSX binário para download.

| Header                | Valor                                                                                         |
|-----------------------|-----------------------------------------------------------------------------------------------|
| `Content-Type`        | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`                           |
| `Content-Disposition` | `attachment; filename="relatorio_AB12_20260525_083000.xlsx"` (nome inclui chave e timestamp)  |

**Estrutura da planilha:**

| Linha | Conteúdo                                                                                         |
|-------|--------------------------------------------------------------------------------------------------|
| 1     | Nome completo e chave do usuário (ex.: `João Silva (AB12)`). Célula mesclada em todas as colunas. |
| 2     | Metadados do relatório (período, total de eventos). Célula mesclada.                             |
| 3     | Linha em branco.                                                                                  |
| 4     | Cabeçalhos das colunas.                                                                          |
| 5+    | Uma linha por evento.                                                                             |

**Colunas do relatório (com permissão de ver horário):**

| Coluna        | Descrição                           |
|---------------|-------------------------------------|
| Data          | `DD/MM/YYYY` no fuso do projeto.    |
| Horário       | `HH:MM:SS` no fuso do projeto.      |
| Ação          | `"Check-In"` ou `"Check-Out"`.      |
| Origem        | Rótulo da origem do evento.         |
| Local         | Rótulo do local físico.             |
| Projeto       | Nome do projeto.                    |
| Fuso Horário  | Rótulo do fuso (ex.: `SGT (UTC+8)`). |
| Assiduidade   | `"Normal"` ou `"Retroativo"`.       |

**Colunas sem permissão de ver horário:** as colunas `Horário` são omitidas automaticamente.

---

## Códigos de status HTTP

| Código | Significado                                                                         |
|--------|-------------------------------------------------------------------------------------|
| `200`  | Sucesso. Arquivo XLSX retornado como stream binário.                                |
| `400`  | Ambos `chave` e `nome` foram informados, ou nenhum foi fornecido.                   |
| `401`  | Sessão administrativa ausente ou expirada.                                          |
| `403`  | Usuário autenticado não possui permissão, ou usuário fora do escopo do admin.       |
| `404`  | Nenhum usuário encontrado com a `chave` ou `nome` informados.                       |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
# Exportar relatório por chave
curl -s -b cookies.txt \
  -o relatorio_AB12.xlsx \
  "http://127.0.0.1:8000/api/admin/reports/events/export?chave=AB12"

# Exportar relatório por nome
curl -s -b cookies.txt \
  -o relatorio_joao.xlsx \
  "http://127.0.0.1:8000/api/admin/reports/events/export?nome=Jo%C3%A3o%20Silva"
```
