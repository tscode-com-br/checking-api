# Migration M3 — Runbook: Aplicação em Produção

## Pré-requisitos

| Item | Detalhe |
|------|---------|
| Arquivo SQL | `sistema/scripts/migrate_accidents_v1.sql` |
| Tabelas pré-existentes | `projects`, `users`, `admin_users` |
| Permissão no DB | `CONNECT` + `CREATE TABLE` no schema público |
| Ferramenta | `psql` ≥ 13 ou equivalente |
| Variável de ambiente | `DATABASE_URL` configurada no servidor |

---

## Passo 1 — Backup completo

Execute **antes** de qualquer alteração no banco:

```bash
# Via pg_dump (recomendado)
pg_dump "$DATABASE_URL" \
    --format=custom \
    --file="backup_pre_m3_$(date +%Y%m%d_%H%M%S).dump"

# Verificar que o dump não está vazio
pg_restore --list backup_pre_m3_*.dump | head -20

# Confirmar tamanho razoável (ajustar conforme o banco de produção)
ls -lh backup_pre_m3_*.dump
```

> **Checkpoint:** O backup deve existir e ter tamanho > 0 antes de continuar.

---

## Passo 2 — Aplicar a migration

```bash
# Via psql diretamente
psql "$DATABASE_URL" \
    -v ON_ERROR_STOP=1 \
    -f sistema/scripts/migrate_accidents_v1.sql

# Saída esperada:
#   CREATE TABLE
#   CREATE UNIQUE INDEX
#   CREATE UNIQUE INDEX
#   CREATE TABLE
#   CREATE TABLE
#   CREATE INDEX
#   CREATE TABLE
#   CREATE TABLE
#   CREATE INDEX
```

Flag `-v ON_ERROR_STOP=1` garante que o psql interrompe ao primeiro erro (importante: o script usa `IF NOT EXISTS`, então é idempotente — pode ser re-executado com segurança se houver falha parcial).

---

## Passo 3 — Verificação de schema

### 3.1 — Listar as 5 novas tabelas

```sql
\dt accidents
\dt accident_user_reports
\dt accident_video_uploads
\dt accident_archives
\dt email_delivery_logs
```

Resultado esperado (uma linha por tabela, tipo `table`, schema `public`):

```
 Schema |          Name          | Type  |  Owner
--------+------------------------+-------+----------
 public | accidents              | table | postgres
 public | accident_user_reports  | table | postgres
 public | accident_video_uploads | table | postgres
 public | accident_archives      | table | postgres
 public | email_delivery_logs    | table | postgres
```

### 3.2 — Verificar constraints e índice parcial de `accidents`

```sql
\d accidents
```

Resultado esperado (colunas relevantes):

```
                     Table "public.accidents"
          Column          |            Type             | Nullable
--------------------------+-----------------------------+----------
 id                       | integer                     | not null
 accident_number          | integer                     | not null
 project_id               | integer                     | not null
 project_name_snapshot    | character varying(120)      | not null
 location_name_snapshot   | character varying(120)      | not null
 location_is_registered   | boolean                     | not null
 origin                   | character varying(16)       | not null
 opened_by_admin_id       | integer                     |
 opened_by_user_id        | integer                     |
 opened_at                | timestamp with time zone    | not null
 closed_by_admin_id       | integer                     |
 closed_at                | timestamp with time zone    |
 archive_object_key       | character varying(512)      |
 created_at               | timestamp with time zone    | not null
 updated_at               | timestamp with time zone    | not null

Indexes:
    "accidents_pkey" PRIMARY KEY, btree (id)
    "uq_accidents_accident_number" UNIQUE CONSTRAINT, btree (accident_number)
    "ix_accidents_single_active" UNIQUE, btree (closed_at) WHERE closed_at IS NULL
    "ix_accidents_single_active_guard" UNIQUE, btree ((1)) WHERE closed_at IS NULL

Check constraints:
    "ck_accidents_number_non_negative" CHECK (accident_number >= 0)
    "ck_accidents_opened_by_actor_required" CHECK (...)
    "ck_accidents_origin_allowed" CHECK (origin IN ('admin'::text, 'web'::text))
```

### 3.3 — Verificar constraints de `accident_user_reports`

```sql
\d accident_user_reports
```

Verificar presença de:
- `uq_accident_user_reports_accident_id_user_id` (UNIQUE)
- `ck_accident_user_reports_zone_allowed` (CHECK zone IN ...)
- `ck_accident_user_reports_status_allowed` (CHECK status IN ...)

### 3.4 — Verificar índice de `accident_video_uploads`

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'accident_video_uploads';
```

Deve conter `ix_accident_video_uploads_accident_user` (btree em `(accident_id, user_id)`).

### 3.5 — Verificar índice de `email_delivery_logs`

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'email_delivery_logs';
```

Deve conter `ix_email_delivery_logs_accident` (btree em `(accident_id)`).

### 3.6 — Verificação funcional rápida

```sql
-- Deve falhar com ck_accidents_origin_allowed
INSERT INTO accidents (accident_number, project_id, project_name_snapshot,
    location_name_snapshot, location_is_registered, origin, opened_by_admin_id,
    opened_at, created_at, updated_at)
VALUES (0, 1, 'Proj', 'Loc', true, 'invalid', 1,
    NOW(), NOW(), NOW());
-- Esperado: ERROR: new row for relation "accidents" violates check constraint "ck_accidents_origin_allowed"

-- Deve falhar com ck_accidents_number_non_negative
INSERT INTO accidents (accident_number, project_id, project_name_snapshot,
    location_name_snapshot, location_is_registered, origin, opened_by_admin_id,
    opened_at, created_at, updated_at)
VALUES (-1, 1, 'Proj', 'Loc', true, 'admin', 1,
        NOW(), NOW(), NOW());
-- Esperado: ERROR: ... violates check constraint "ck_accidents_number_non_negative"
```

---

## Passo 4 — Verificação de rowcount (pós-migration)

As 5 novas tabelas devem estar **vazias** imediatamente após a migration:

```sql
SELECT 'accidents'              AS tbl, COUNT(*) FROM accidents
UNION ALL
SELECT 'accident_user_reports'  AS tbl, COUNT(*) FROM accident_user_reports
UNION ALL
SELECT 'accident_video_uploads' AS tbl, COUNT(*) FROM accident_video_uploads
UNION ALL
SELECT 'accident_archives'      AS tbl, COUNT(*) FROM accident_archives
UNION ALL
SELECT 'email_delivery_logs'    AS tbl, COUNT(*) FROM email_delivery_logs;
```

Resultado esperado: 0 em todas as linhas (estado limpo antes do primeiro acidente).

---

## Passo 5 — Rollback (se necessário)

> ⚠️ **Executar o rollback apenas se a migration falhou E o backup foi confirmado no Passo 1.**

```sql
-- Ordem: tabelas filhas antes das tabelas pai (respeitar FKs)
DROP TABLE IF EXISTS accident_archives      CASCADE;
DROP TABLE IF EXISTS accident_video_uploads CASCADE;
DROP TABLE IF EXISTS accident_user_reports  CASCADE;
DROP TABLE IF EXISTS email_delivery_logs    CASCADE;
DROP TABLE IF EXISTS accidents              CASCADE;
```

Ou via script de rollback incluído ao final do arquivo SQL de migration:

```bash
psql "$DATABASE_URL" -c "
DROP TABLE IF EXISTS accident_archives, accident_video_uploads,
    accident_user_reports, email_delivery_logs, accidents CASCADE;
"
```

Após o rollback, restaurar o backup (somente se houve corrupção de dados):

```bash
pg_restore \
    --dbname="$DATABASE_URL" \
    --clean \
    --if-exists \
    backup_pre_m3_*.dump
```

---

## Checklist de Go/No-Go

| # | Item | OK? |
|---|------|-----|
| 1 | Backup confirmado (arquivo dump existe, tamanho > 0) | `[ ]` |
| 2 | Migration aplicada sem erros no psql | `[ ]` |
| 3 | `\dt` mostra as 5 tabelas | `[ ]` |
| 4 | `\d accidents` mostra constraints + índices parciais | `[ ]` |
| 5 | Rowcount = 0 em todas as 5 tabelas | `[ ]` |
| 6 | Smoke test M2 passou (`18/18 checks`) | `[ ]` |
| 7 | Logs do servidor sem erros 500 nas primeiras 5 min | `[ ]` |

Todos os itens `[x]` = **aprovado para continuar o deploy**.
Qualquer item `[ ]` = **executar Passo 5 (rollback)** e acionar a equipe.

---

## Referências

- Script SQL: `sistema/scripts/migrate_accidents_v1.sql`
- Smoke test: `scripts/smoke_test_accident_mode.py`
- Checklist E2E: `docs/descritivos/e2e_modo_acidente_checklist.md`
- Critérios de aceitação: `docs/descritivos/aceitacao_modo_acidente.md`
