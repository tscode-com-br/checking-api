# `GET /api/admin/diagnostics/database`

## Visão Geral

Retorna diagnósticos detalhados da conexão e desempenho do banco de dados, incluindo métricas do pool de conexões SQLAlchemy, latência de queries, conexões ativas no servidor PostgreSQL (ou SQLite em desenvolvimento) e limiares recomendados para alertas operacionais.

| Atributo         | Valor                                   |
|------------------|-----------------------------------------|
| **Método**       | `GET`                                   |
| **Path**         | `/api/admin/diagnostics/database`       |
| **Autenticação** | Sessão administrativa completa (cookie) |
| **Content-Type** | —                                       |

---

## Autenticação

Requer sessão administrativa válida obtida via `POST /api/admin/auth/login`. A sessão é transmitida por cookie HTTP assinado. O usuário deve ter perfil com acesso ao painel admin (`perfil` com dígito `1` ou `9`).

Falhas de autenticação retornam:
- `401` — sessão ausente ou expirada.
- `403` — sessão válida, mas o usuário não tem permissão de acesso ao admin.

---

## Parâmetros

Nenhum.

---

## Resposta

**HTTP 200 — Sucesso**

```json
{
  "generated_at": "2026-05-25T08:30:00Z",
  "pool": {
    "dialect": "postgresql",
    "driver": "psycopg2",
    "pool_class": "QueuePool",
    "status": "ok",
    "configured_pool_size": 5,
    "configured_max_overflow": 10,
    "configured_pool_timeout_seconds": 30,
    "configured_pool_recycle_seconds": 1800,
    "pool_pre_ping": true,
    "checked_in": 4,
    "checked_out": 1,
    "current_overflow": 0,
    "total_capacity": 15,
    "usage_ratio": 0.067,
    "saturation": "low",
    "checked_out_high_watermark": 3,
    "current_open_connections": 5,
    "open_connections_high_watermark": 7,
    "total_connect_events": 42,
    "total_close_events": 37,
    "total_checkout_events": 12840,
    "total_checkin_events": 12839
  },
  "latency": {
    "query_count_total": 12840,
    "query_error_count_total": 2,
    "slow_query_count_total": 5,
    "query_time_ms_total": 89400,
    "recent_query_sample_size": 100,
    "recent_average_query_ms": 7,
    "recent_p95_query_ms": 22,
    "hot_paths": [
      {
        "path": "GET /api/admin/users",
        "recent_query_count": 48,
        "recent_average_query_ms": 15,
        "recent_p95_query_ms": 38,
        "total_query_count": 2310
      }
    ]
  },
  "server_connections": {
    "source": "pg_stat_activity",
    "database_connections_total": 8,
    "active_database_connections": 2,
    "waiting_database_connections": 0,
    "idle_in_transaction_connections": 0,
    "error": null
  },
  "recommended_alert_thresholds": {
    "pool_usage_warning_ratio": 0.7,
    "pool_usage_critical_ratio": 0.9,
    "recent_query_p95_warning_ms": 100,
    "recent_query_p95_critical_ms": 500,
    "slow_query_log_threshold_ms": 200,
    "postgres_active_connections_warning": 20,
    "postgres_active_connections_critical": 40,
    "postgres_waiting_connections_warning": 3,
    "postgres_waiting_connections_critical": 10,
    "postgres_idle_in_transaction_warning": 2
  }
}
```

### Campos de `pool` (DatabasePoolDiagnosticsResponse)

| Campo                             | Tipo              | Descrição                                                                      |
|-----------------------------------|-------------------|--------------------------------------------------------------------------------|
| `dialect`                         | `string`          | Dialeto SQL (ex.: `"postgresql"`, `"sqlite"`).                                 |
| `driver`                          | `string`          | Driver Python utilizado (ex.: `"psycopg2"`).                                   |
| `pool_class`                      | `string`          | Classe do pool SQLAlchemy (ex.: `"QueuePool"`, `"StaticPool"`).                |
| `status`                          | `string \| null`  | Status geral do pool.                                                          |
| `configured_pool_size`            | `integer \| null` | Tamanho configurado do pool (`pool_size`).                                     |
| `configured_max_overflow`         | `integer \| null` | Overflow máximo configurado.                                                   |
| `configured_pool_timeout_seconds` | `integer \| null` | Timeout de checkout de conexão em segundos.                                    |
| `configured_pool_recycle_seconds` | `integer \| null` | Intervalo de reciclagem de conexões em segundos.                               |
| `pool_pre_ping`                   | `boolean`         | Se `pre_ping` está habilitado (verifica conexão antes de reusar).              |
| `checked_in`                      | `integer \| null` | Conexões disponíveis no pool no momento.                                       |
| `checked_out`                     | `integer \| null` | Conexões em uso no momento.                                                    |
| `current_overflow`                | `integer \| null` | Conexões de overflow abertas no momento.                                       |
| `total_capacity`                  | `integer \| null` | Capacidade total do pool (`pool_size` + `max_overflow`).                       |
| `usage_ratio`                     | `float \| null`   | Razão de uso atual do pool (0.0–1.0).                                          |
| `saturation`                      | `string`          | Nível de saturação: `"low"`, `"medium"`, `"high"`, `"critical"`.               |
| `checked_out_high_watermark`      | `integer`         | Máximo histórico de conexões em uso simultâneas.                               |
| `current_open_connections`        | `integer`         | Total de conexões abertas no momento.                                          |
| `open_connections_high_watermark` | `integer`         | Máximo histórico de conexões abertas simultâneas.                              |
| `total_connect_events`            | `integer`         | Total de conexões abertas desde o início do processo.                          |
| `total_close_events`              | `integer`         | Total de conexões fechadas desde o início do processo.                         |
| `total_checkout_events`           | `integer`         | Total de checkouts de conexão do pool.                                         |
| `total_checkin_events`            | `integer`         | Total de checkins de conexão de volta ao pool.                                 |

### Campos de `latency` (DatabaseLatencyDiagnosticsResponse)

| Campo                      | Tipo                              | Descrição                                                              |
|----------------------------|-----------------------------------|------------------------------------------------------------------------|
| `query_count_total`        | `integer`                         | Total de queries executadas desde o início do processo.                |
| `query_error_count_total`  | `integer`                         | Total de queries que resultaram em erro.                               |
| `slow_query_count_total`   | `integer`                         | Total de queries consideradas lentas (acima do limiar configurado).    |
| `query_time_ms_total`      | `integer`                         | Tempo acumulado total de queries em millisegundos.                     |
| `recent_query_sample_size` | `integer`                         | Tamanho da janela de amostra recente.                                  |
| `recent_average_query_ms`  | `integer \| null`                 | Média de tempo de query (ms) na amostra recente.                       |
| `recent_p95_query_ms`      | `integer \| null`                 | Percentil 95 de tempo de query (ms) na amostra recente.                |
| `hot_paths`                | `list[DatabaseHotPathTelemetry]`  | Caminhos HTTP com mais queries na amostra recente.                     |

#### Campos de cada item em `hot_paths`

| Campo                    | Tipo              | Descrição                                               |
|--------------------------|-------------------|---------------------------------------------------------|
| `path`                   | `string`          | Caminho HTTP associado às queries.                      |
| `recent_query_count`     | `integer`         | Quantidade de queries deste caminho na amostra recente. |
| `recent_average_query_ms`| `integer \| null` | Média de tempo (ms) para este caminho.                  |
| `recent_p95_query_ms`    | `integer \| null` | Percentil 95 (ms) para este caminho.                    |
| `total_query_count`      | `integer`         | Total histórico de queries deste caminho.               |

### Campos de `server_connections` (DatabaseServerConnectionDiagnosticsResponse)

| Campo                            | Tipo              | Descrição                                                               |
|----------------------------------|-------------------|-------------------------------------------------------------------------|
| `source`                         | `string`          | Fonte dos dados (ex.: `"pg_stat_activity"`, `"unavailable"`).           |
| `database_connections_total`     | `integer \| null` | Total de conexões com o banco de dados (PostgreSQL).                    |
| `active_database_connections`    | `integer \| null` | Conexões ativas executando queries.                                     |
| `waiting_database_connections`   | `integer \| null` | Conexões aguardando lock ou recurso.                                    |
| `idle_in_transaction_connections`| `integer \| null` | Conexões idle em transação aberta (sinal de alerta).                    |
| `error`                          | `string \| null`  | Mensagem de erro ao coletar dados do servidor, se houver.               |

### Campos de `recommended_alert_thresholds`

| Campo                                   | Tipo    | Descrição                                                            |
|-----------------------------------------|---------|----------------------------------------------------------------------|
| `pool_usage_warning_ratio`              | `float` | Razão de uso do pool que deve disparar alerta de aviso.              |
| `pool_usage_critical_ratio`             | `float` | Razão de uso do pool que deve disparar alerta crítico.               |
| `recent_query_p95_warning_ms`           | `int`   | P95 de latência (ms) que deve disparar alerta de aviso.              |
| `recent_query_p95_critical_ms`          | `int`   | P95 de latência (ms) que deve disparar alerta crítico.               |
| `slow_query_log_threshold_ms`           | `int`   | Limiar (ms) acima do qual uma query é registrada como lenta.         |
| `postgres_active_connections_warning`   | `int`   | Número de conexões ativas que dispara alerta de aviso.               |
| `postgres_active_connections_critical`  | `int`   | Número de conexões ativas que dispara alerta crítico.                |
| `postgres_waiting_connections_warning`  | `int`   | Número de conexões em espera que dispara alerta de aviso.            |
| `postgres_waiting_connections_critical` | `int`   | Número de conexões em espera que dispara alerta crítico.             |
| `postgres_idle_in_transaction_warning`  | `int`   | Número de conexões idle-in-transaction que dispara alerta de aviso.  |

---

## Códigos de status HTTP

| Código | Significado                                                          |
|--------|----------------------------------------------------------------------|
| `200`  | Sucesso.                                                             |
| `401`  | Sessão administrativa ausente ou expirada.                           |
| `403`  | Usuário autenticado não possui permissão de acesso ao painel admin.  |

---

## Side effects

Nenhum. Endpoint somente-leitura que coleta métricas do pool SQLAlchemy e, quando disponível, consulta `pg_stat_activity` no PostgreSQL (em dev/SQLite, `server_connections.source` será `"unavailable"`).

---

## Exemplo cURL (ambiente local)

```bash
curl -s -b cookies.txt http://127.0.0.1:8000/api/admin/diagnostics/database
```
