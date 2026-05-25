# `GET /api/admin/reports/events/export-all`

## Visão Geral

Gera e baixa um arquivo XLSX (Excel) com os eventos de check-in e check-out de **todos os usuários** visíveis ao administrador autenticado, em uma única planilha consolidada. O relatório respeita o escopo de projetos do administrador e ordena os dados por nome do usuário, depois por data do evento (mais recente primeiro).

| Atributo         | Valor                                                                      |
|------------------|----------------------------------------------------------------------------|
| **Método**       | `GET`                                                                      |
| **Path**         | `/api/admin/reports/events/export-all`                                     |
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

Nenhum. O escopo de usuários é determinado automaticamente pelos projetos monitorados pelo administrador autenticado.

---

## Resposta

**HTTP 200 — Sucesso**

Arquivo XLSX binário para download.

| Header                | Valor                                                                                       |
|-----------------------|---------------------------------------------------------------------------------------------|
| `Content-Type`        | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`                         |
| `Content-Disposition` | `attachment; filename="relatorio_todos_20260525_083000.xlsx"` (nome inclui timestamp)        |

**Estrutura da planilha:**

| Linha | Conteúdo                        |
|-------|---------------------------------|
| 1     | Cabeçalhos das colunas.         |
| 2+    | Uma linha por evento de usuário.|

**Colunas do relatório (com permissão de ver horário):**

| Coluna        | Descrição                                              |
|---------------|--------------------------------------------------------|
| Nome          | Nome completo do usuário (presente apenas neste export). |
| Data          | `DD/MM/YYYY` no fuso do projeto.                       |
| Horário       | `HH:MM:SS` no fuso do projeto.                         |
| Ação          | `"Check-In"` ou `"Check-Out"`.                         |
| Origem        | Rótulo da origem do evento.                            |
| Local         | Rótulo do local físico.                                |
| Projeto       | Nome do projeto.                                       |
| Fuso Horário  | Rótulo do fuso (ex.: `SGT (UTC+8)`).                   |
| Assiduidade   | `"Normal"` ou `"Retroativo"`.                          |

**Colunas sem permissão de ver horário:** a coluna `Horário` é omitida automaticamente.

Os dados são ordenados por nome de usuário (A–Z) e, dentro de cada usuário, por data do evento (mais recente primeiro).

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso. Arquivo XLSX retornado (pode ter apenas cabeçalho se não houver eventos). |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

Nenhum.

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt \
  -o relatorio_todos.xlsx \
  http://127.0.0.1:8000/api/admin/reports/events/export-all
```
