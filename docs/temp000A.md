# Task A1 — Resumo detalhado da implementação concluída

A implementação do **Bloco A / Task A1** foi concluída com foco na fundação do backend do Modo Acidente em SQLAlchemy, cobrindo modelos, constraints, índices e testes de persistência/validação.

## 1) Modelos SQLAlchemy adicionados

Arquivo modificado: `sistema/app/models.py`

Foram adicionadas, ao final do arquivo (após `EndpointApiKey`), as cinco entidades solicitadas:

1. `Accident` (`accidents`)
2. `AccidentUserReport` (`accident_user_reports`)
3. `AccidentVideoUpload` (`accident_video_uploads`)
4. `AccidentArchive` (`accident_archives`)
5. `EmailDeliveryLog` (`email_delivery_logs`)

Também foram mantidos campos de snapshot/JSON serializado em `Text` (sem migração para `JSON`), em linha com o padrão já usado no projeto.

## 2) Constraints e regras de integridade implementadas

Arquivo modificado: `sistema/app/models.py`

Foram implementadas as constraints obrigatórias com os nomes especificados:

- `ck_accidents_origin_allowed`
- `ck_accidents_number_non_negative`
- `ck_accident_user_reports_zone_allowed`
- `ck_accident_user_reports_status_allowed`
- `ck_email_delivery_logs_status_allowed`

Além disso:

- `Accident` recebeu `UniqueConstraint` para `accident_number`.
- `AccidentUserReport` recebeu `UniqueConstraint` para `(accident_id, user_id)`.
- `AccidentVideoUpload` recebeu `UniqueConstraint` para `idempotency_key`.
- `AccidentArchive` recebeu `UniqueConstraint` para `accident_id`.
- `Accident` recebeu check adicional para garantir ator de abertura válido (`opened_by_admin_id` XOR `opened_by_user_id`), reforçando a regra “um deles preenchido”.

## 3) Índices implementados

Arquivo modificado: `sistema/app/models.py`

Foram adicionados os índices solicitados:

- `ix_accidents_single_active` (índice parcial único conforme especificação enviada)
- `ix_accident_video_uploads_accident_user` (`accident_id`, `user_id`)
- `ix_email_delivery_logs_accident` (`accident_id`)

Também foi adicionado um índice parcial único complementar:

- `ix_accidents_single_active_guard`

Esse índice complementar existe para garantir efetivamente, em SQLite/Postgres, a unicidade de acidente ativo (`closed_at IS NULL`) no nível de banco, já que a unicidade somente em coluna anulável não bloqueia múltiplos `NULL` em alguns cenários.

## 4) Testes obrigatórios criados

Arquivo criado: `tests/models/test_accident_models.py`

Foram implementados os 9 testes solicitados:

1. `test_accident_columns_match_spec`
2. `test_accident_origin_constraint`
3. `test_accident_number_non_negative_constraint`
4. `test_single_active_accident_partial_index`
5. `test_accident_user_report_zone_status_constraints`
6. `test_accident_user_report_unique_per_user_per_accident`
7. `test_accident_video_upload_idempotency_key_unique`
8. `test_accident_archive_unique_per_accident`
9. `test_email_delivery_log_status_constraint`

Os testes usam SQLite local por arquivo temporário e validam `flush()`/`IntegrityError` nas violações de constraints e unicidade.

## 5) Verificações executadas

1. Import direto dos modelos:
   - comando: `python -c "from sistema.app.models import Accident, AccidentUserReport, AccidentVideoUpload, AccidentArchive, EmailDeliveryLog"`
   - resultado: OK

2. Criação de schema via `Base.metadata.create_all(engine)` em SQLite:
   - verificada presença das 5 tabelas novas e do índice parcial `ix_accidents_single_active`
   - resultado: OK

3. Testes do novo módulo:
   - comando: `python -m pytest -q tests\models\test_accident_models.py`
   - resultado: **9 passed**

## 6) Arquivos alterados nesta tarefa

- `sistema/app/models.py` (edição)
- `tests/models/test_accident_models.py` (novo)
- `docs/temp000A.md` (novo, contendo este resumo)
