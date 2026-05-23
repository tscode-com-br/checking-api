# Plano de implementação — Melhorias do Checking

Status do documento: aprovado para implementação após revisão.
Datas: 2026-05-22 (Parte I) · 2026-05-23 (Parte II + Parte III + consolidação)
Autor: Tamer + Claude (planejamento conjunto)

Este documento agrupa três frentes de trabalho, com dependências fracas entre si (ver §A.3):

| Parte | Frente | Status | Próximo passo |
|---|---|---|---|
| **I** | Otimização do envio do Microsoft Forms (pausas + concorrência) | Não iniciado | Commit A — redução de pausas (§3) |
| **II** | Correção do piscar do Admin2 (animação + diff render) | Não iniciado | Commit C — fim do piscar (§13) |
| **III** | Colunas Forms / Transporte / Emergência na tabela de Projetos | Não iniciado | Commit E — backend + endpoints (§22) |

## Sumário

**Apêndice — convenções transversais (ler primeiro)**
- [A.1 Pre-flight checks comuns](#a1-pre-flight-checks-comuns)
- [A.2 Convenções de PR e commit](#a2-convenções-de-pr-e-commit)
- [A.3 Ordem global recomendada entre as três Partes](#a3-ordem-global-recomendada-entre-as-três-partes)
- [A.4 Janelas de deploy sugeridas](#a4-janelas-de-deploy-sugeridas)
- [A.5 Definição de Pronto (DoD) por commit](#a5-definição-de-pronto-dod-por-commit)
- [A.6 Glossário](#a6-glossário)
- [A.7 Plano de comunicação ao usuário final](#a7-plano-de-comunicação-ao-usuário-final)

**Parte I — Forms (§0–§9):** Commits A (pausas) + B (concorrência)
**Parte II — Admin2 piscar (§10–§19):** Commits C (núcleo) + D (mitigações)
**Parte III — Projetos com toggles (§20–§28):** Commits E (backend) + F (gates) + G (admin2 UI) + H (Check Web)

---

# Apêndice — Convenções transversais

Esta seção concentra o que vale para os três módulos do plano. Ler antes de começar qualquer Parte.

## A.1 Pre-flight checks comuns

Antes de qualquer commit que faça parte deste plano, rodar localmente:

```bash
# Testes — escopo do commit (ajustar path conforme Parte)
pytest tests/ -x -q

# Testes — somente arquivos tocados pelo commit (mais rápido para iteração)
pytest tests/services/test_forms_submit_resilience.py tests/test_forms_worker_resilience.py -x -q  # Parte I (Commit A)
pytest tests/services/test_forms_worker_concurrency.py tests/test_api_flow.py -x -q              # Parte I (Commit B)
pytest tests/check_admin_*.test.js -x -q                                                          # Parte II (se houver runner JS)
pytest tests/routers/test_admin_projects.py tests/services/test_project_catalog.py -x -q          # Parte III (E)

# Migration check (Parte III, Commit E)
python -m alembic upgrade head        # aplica até a 0066
python -m alembic downgrade -1        # valida rollback
python -m alembic upgrade head        # reaplica

# Build do worker container (Parte I, Commit B — após mudança no docker-compose)
docker compose build forms-worker

# Smoke local do app (Parte II + III, antes de mergear frontend)
python -m uvicorn sistema.app.main:app --reload
# Em outro shell, abrir http://localhost:8000/admin2 e /check
```

> **Não mergear** se algum pre-flight falhar. Se não conseguir rodar localmente, espelhar no CI antes do merge.

## A.2 Convenções de PR e commit

**Título do PR:** `[Parte X — Commit Y] descrição curta`
Exemplos:
- `[Parte I — Commit A] Reduz pausas do worker do Forms para até 1s`
- `[Parte II — Commit C] Remove animação stagger e implementa diff render no Admin2`
- `[Parte III — Commit E] Adiciona colunas forms_enabled/transport_enabled/emergency_phone em projects`

**Corpo do PR (template mínimo):**

```markdown
## Contexto
Refere-se à §X.Y do `docs/temp001.md`.

## Mudanças
- ...

## Validação
- [x] Pre-flight checks (§A.1)
- [x] Checklist de pronto para mergear do commit (ver respectiva seção)
- [x] Smoke manual: ...

## Risco / rollback
Ver §X (Riscos) e §X (Rollback) na respectiva Parte.
```

**Commits dentro do PR:** mensagens em português, voz ativa, formato `<area>(<escopo>): <verbo no infinitivo> <objeto>`. Ex.: `forms(worker): reduzir POST_SUBMIT_SETTLE para 1s`.

**Labels sugeridas:**
- `area:forms-worker`, `area:admin2`, `area:check-web`, `area:db-migration`
- `risk:low` / `risk:medium` / `risk:high`

## A.3 Ordem global recomendada entre as três Partes

As Partes são tecnicamente independentes (cada uma compila e roda sozinha). Mas há **sinergias** que recomendam a seguinte ordem:

1. **Parte III antes da Parte I.** O gate `forms_enabled` (Commit F) reduz o volume de submissões na fila quando algum projeto está com Forms desativado. Isso facilita o teste de carga da concorrência (Commit B) com baseline conhecido — você sabe exatamente quantos projetos contribuem para o backlog.

2. **Parte II independente das outras.** Pode ir em qualquer ordem; mexe só em frontend admin2 (`app.js` / `styles.css`). Faz sentido começar por ela se a equipe quiser entregar valor visual rápido.

3. **Parte I depois (Commit A primeiro, B depois).** Pausas reduzidas (A) é entrega isolada de baixíssimo risco. Concorrência (B) merece ir só após A estar estável em produção — assim, se algo regredir, fica claro qual mudança causou.

**Ordem sugerida combinada:**

```
II.C → II.D → III.E → III.F → III.G → III.H → I.A → I.B
```

Não é obrigatório seguir essa ordem — apenas é a que minimiza interferência cruzada e maximiza isolamento de variáveis em incidentes.

## A.4 Janelas de deploy sugeridas

| Commit | Janela recomendada | Razão |
|---|---|---|
| I.A (pausas) | Qualquer horário, fora de pico | Mudança apenas no `forms-worker`; reinício do container em ~5s; impacto se algo regredir é "Forms enfileira mas demora", não perda de dado. |
| I.B (concorrência) | **Madrugada / fim de semana** | Reinício do worker durante carga real expõe race conditions. Janela calma + observação ativa. |
| II.C / II.D (admin2) | Qualquer horário | Frontend estático; admins reabrem aba para pegar versão nova. Sem impacto para usuários do Check Web. |
| III.E (migration + endpoints) | **Janela de manutenção curta (~5 min)** | Migration Alembic em produção; defaults seguros, mas tradição de janela. |
| III.F (gates) | Após III.E estabilizar | Comportamento default (`True`) não muda nada; mas o código entra em paths críticos (`submit_forms_event`, `WebCheckHistoryResponse`). |
| III.G (admin2 UI) | Qualquer horário | Frontend estático. |
| III.H (Check Web) | Qualquer horário, com aviso prévio | Label muda de "Em Teste" para "Transporte" — usuários podem estranhar sem aviso. Ver §A.7 abaixo (comunicação). |

## A.5 Definição de Pronto (DoD) por commit

Um commit só é considerado "Pronto" quando, cumulativamente:

1. ✅ Todos os itens do **Checklist** específico do commit estão marcados.
2. ✅ **Pre-flight checks** (§A.1) passaram localmente E no CI.
3. ✅ **Smoke manual** do commit (descrito na seção "Validação manual" da Parte) foi executado.
4. ✅ Documentação relevante atualizada (`CLAUDE.md`, `docs/forms_routine.md`, etc.) se a mudança afeta convenções.
5. ✅ **Code review** por pelo menos 1 outra pessoa, OU justificativa explícita no PR de por que vai sem review (ex: hotfix).
6. ✅ **Rollback documentado** está testado (não basta estar escrito).
7. ✅ Se a mudança altera comportamento perceptível para o usuário final: **comunicação enviada** (§A.7).

## A.6 Glossário

| Termo | Definição |
|---|---|
| **Claim atômico** | Pattern `UPDATE...WHERE status='pending'` + checagem de `rowcount==1` que garante exclusividade de reserva entre threads/processos. Em [forms_queue.py:529-538](../sistema/app/services/forms_queue.py#L529-L538). |
| **Diff render** | Estratégia de re-renderização que reaproveita nós DOM existentes quando o conteúdo é idêntico, em vez de destruir + recriar tudo. Elimina o piscar do Admin2. |
| **Forms worker** | Processo separado (container `forms-worker`) que consome a fila `forms_submissions` e preenche o Microsoft Forms via Playwright. |
| **Gate (forms_enabled / transport_enabled)** | Verificação que decide se uma feature deve executar para um projeto específico. Lê coluna `bool` na tabela `projects`. |
| **Self-watchdog** | Padrão onde uma thread captura todas as exceções internamente e nunca sai voluntariamente, garantindo que só morra com o processo. |
| **Skip path** | Caminho no `submit_forms_event` onde a atividade é aceita sem enfileirar novo envio ao Forms. Já existia para "mesma ação no mesmo dia"; estendemos para "Forms desligado por projeto". |
| **SSE (Server-Sent Events)** | Stream HTTP unidirecional servidor→cliente. Usado em `/api/admin/stream`, `/api/web/check/stream` para refresh em tempo real. |
| **Stagger animation** | Animação que aplica delay incremental por linha (e.g., 14ms × índice). Estética em primeiro load, problemática em re-renders frequentes. |
| **State (Check Web)** | Payload retornado por `/api/web/check/state` que descreve o estado atual do usuário e (pós-Parte III) o `transport_enabled` do projeto ativo. |

## A.7 Plano de comunicação ao usuário final

Mudanças visíveis exigem aviso prévio para evitar reclamação:

| Mudança | Quem precisa saber | Canal sugerido | Texto base |
|---|---|---|---|
| Label do botão "Em Teste" → "Transporte" (Commit H) | Usuários do Check Web | Comunicado interno + nota no topo do Check Web por 1 semana | "O botão 'Em Teste' agora se chama 'Transporte'. Sem mudança de comportamento — apenas o nome." |
| Toggle de Forms / Transporte (Commit G) | Administradores | Treinamento interno ou changelog | "Cada projeto agora tem controles Forms/Transporte. Use com cuidado: desligar Forms para um projeto interrompe o envio para o Microsoft Forms até religar." |
| Concorrência do Forms worker (Commit B) | Time técnico | Changelog técnico | "O worker do Forms agora processa até 3 submissões em paralelo. Diagnóstico em `/api/admin/forms/queue/diagnostics` expõe `concurrency` e `consumer_threads_alive`." |
| Demais commits | Apenas changelog técnico | — | — |

---

# Parte I — Otimização do envio do Microsoft Forms

## 0. Contexto e objetivos

O envio para o Microsoft Forms hoje é o gargalo percebido pelo usuário do Checking. Duas causas concretas no código:

1. **Pausas longas dentro de cada submissão** ([sistema/app/services/forms_worker.py:18-24](../sistema/app/services/forms_worker.py#L18-L24)): somam ~17,5 s só de `_pause(...)` por submissão.
2. **Worker single-thread**: o consumo da fila é estritamente sequencial ([forms_queue.py:744-783](../sistema/app/services/forms_queue.py#L744-L783)) — quando 3 ou 4 usuários acionam atividades em rajada, a fila drena uma por vez.

### Objetivos mensuráveis

- Reduzir o tempo de uma submissão em ~7 s (de ~17,5 s só em pausas para ~10,5 s).
- Permitir até 3 submissões em paralelo, configurável via `FORMS_WORKER_CONCURRENCY` (default `3`).
- Manter compatibilidade com:
  - Todos os testes em `tests/test_api_flow.py` que chamam `process_forms_submission_queue_once(...)` direto (~10 testes).
  - O teste `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` ([test_api_flow.py:5776](../tests/test_api_flow.py#L5776)).
  - Os testes de health/warning em `tests/services/test_forms_queue_worker_down_warning.py`.
  - O endpoint `GET /api/admin/forms/queue/diagnostics` (mesmos campos do snapshot, mais campos novos opcionais).

### Premissas

- Worker continua rodando em container próprio (`forms-worker` do docker-compose).
- Postgres em produção; SQLite em dev. O claim atômico funciona em ambos.
- O Playwright sync API suporta uso multi-thread quando cada thread instancia seu próprio `sync_playwright()` — é exatamente como está em [forms_worker.py:253](../sistema/app/services/forms_worker.py#L253) (`with sync_playwright() as p:` dentro de `_submit_once`).

### Sinergia com a Parte III

Se a Parte III já estiver em produção (Commits E + F), a validação da concorrência (Commit B) fica mais limpa: você pode **desligar `forms_enabled`** para projetos não-críticos antes do teste de carga, garantindo que o backlog medido vem só dos projetos sob teste. Ver §A.3 para a ordem global recomendada.

### Decisões arquiteturais já tomadas

- **Concorrência via thread pool dentro do worker** (não `docker-compose --scale`, não pool de processos). Justificativa:
  - O claim atômico (`UPDATE...WHERE status='pending'` + checagem de `rowcount` em [forms_queue.py:529-538](../sistema/app/services/forms_queue.py#L529-L538)) já é thread-safe.
  - Cada thread abre seu próprio Chromium subprocess via Playwright → isolamento real de navegador no nível do kernel.
  - Health snapshot único (`forms_worker_health.json`) — escalar containers exigiria redesenhar todo o sistema de health/diagnóstico.
  - Single supervisor → reinício é trivial via Docker.
- **Pausas cap absoluto em 1 s** — reduzir só as 3 que excedem 1 s, expostas como `settings` configuráveis via env. Pausas ≤ 1 s ficam intocadas (já validadas em produção). Default conservador, permite ajuste sem deploy se algo regredir.

---

## 1. Fase 1 — Redução de pausas

### 1.1 Alvos

Em [sistema/app/services/forms_worker.py:18-24](../sistema/app/services/forms_worker.py#L18-L24):

| Constante | Valor atual | Novo default | Justificativa técnica |
|---|---|---|---|
| `URL_LOAD_SETTLE_SECONDS` | 3.0 | **1.0** | `page.goto(...)` em [forms_worker.py:257](../sistema/app/services/forms_worker.py#L257) já aguarda navegação. O settle é paranoia para repintura inicial; 1 s cobre. |
| `AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS` | 2.0 | **1.0** | Após `_locate_step(...)` o DOM já está pronto. A descoberta seguinte tem retry interno (`FIELD_SEARCH_TIMEOUT_SECONDS=60`). |
| `POST_SUBMIT_SETTLE_SECONDS` | 5.0 | **1.0** | O `_wait_for_step(sucesso, ..., SUCCESS_SEARCH_TIMEOUT_SECONDS=60)` já faz polling. O settle só evita falso-positivo no early-check; 1 s é suficiente. |

**Pausas que permanecem (≤ 1 s, já validadas):**
- `STEP_DISCOVERY_SETTLE_SECONDS = 0.5`
- `AFTER_FILL_SETTLE_SECONDS = 1.0`
- `AFTER_SELECTION_SETTLE_SECONDS = 1.0`
- `PRE_SUBMIT_SETTLE_SECONDS = 1.0`

**Constantes de timeout que NÃO são pausas (não tocar):**
- `FIELD_SEARCH_TIMEOUT_SECONDS = 60` (retry deadline)
- `SUCCESS_SEARCH_TIMEOUT_SECONDS = 60` (retry deadline)
- `STEP_CONFIRM_TIMEOUT_SECONDS = 10` (validação de input)
- `FIELD_SEARCH_RETRY_INTERVAL_SECONDS = 1.0` (intervalo entre retries dentro do timeout)
- `FIELD_SEARCH_CANDIDATE_TIMEOUT_MS = 250` (per-selector wait)

### 1.2 Economia estimada

Tempo gasto só em `_pause(...)` por submissão:

| Caminho | Antes | Depois |
|---|---|---|
| checkin | 3 + 5×0.5 + 2 + 2×1 + 1 + 1 + 1 + 5 = **17.5 s** | 1 + 5×0.5 + 1 + 2×1 + 1 + 1 + 1 + 1 = **10.5 s** |
| checkout | 3 + 5×0.5 + 2 + 2×1 + 1 + 1 + 5 = **16.5 s** | 1 + 5×0.5 + 1 + 2×1 + 1 + 1 + 1 = **9.5 s** |

**Ganho: 7 s/submissão.**

### 1.3 Configuração

Adicionar em [sistema/app/core/config.py](../sistema/app/core/config.py) (após `forms_worker_unhealthy_consecutive_errors` em torno da linha 51):

```python
forms_settle_url_load_seconds: float = 1.0
forms_settle_after_checkout_discovery_seconds: float = 1.0
forms_settle_post_submit_seconds: float = 1.0
```

**Em [forms_worker.py](../sistema/app/services/forms_worker.py)**: em vez de constantes module-level, ler `settings.*` inline dentro de `_submit_once`. Isso preserva configurabilidade em testes (`monkeypatch.setattr(settings, "forms_settle_url_load_seconds", 0.0)`) sem precisar reimportar módulo.

Trocar:

```python
URL_LOAD_SETTLE_SECONDS = 3.0
...
self._pause(page, URL_LOAD_SETTLE_SECONDS)
```

Por:

```python
# (remover a constante)
...
self._pause(page, settings.forms_settle_url_load_seconds)
```

Mesma transformação para `AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS` e `POST_SUBMIT_SETTLE_SECONDS`.

> **Importante:** adicionar `from ..core.config import settings` se ainda não estiver importado (já está em [forms_worker.py:9](../sistema/app/services/forms_worker.py#L9)).

### 1.4 Exposição no docker-compose e env

[docker-compose.yml](../docker-compose.yml), seção `forms-worker.environment`:

```yaml
FORMS_SETTLE_URL_LOAD_SECONDS: ${FORMS_SETTLE_URL_LOAD_SECONDS:-1.0}
FORMS_SETTLE_AFTER_CHECKOUT_DISCOVERY_SECONDS: ${FORMS_SETTLE_AFTER_CHECKOUT_DISCOVERY_SECONDS:-1.0}
FORMS_SETTLE_POST_SUBMIT_SECONDS: ${FORMS_SETTLE_POST_SUBMIT_SECONDS:-1.0}
```

Também em [.env.example](../.env.example) e [deploy/.env.production.example](../deploy/.env.production.example) com os mesmos defaults.

### 1.5 Testes da Fase 1

**Arquivo:** `tests/services/test_forms_submit_resilience.py` (já existe).

Adicionar:

```python
def test_settle_defaults_are_capped_at_one_second():
    # garante o contrato com o usuário
    assert settings.forms_settle_url_load_seconds <= 1.0
    assert settings.forms_settle_after_checkout_discovery_seconds <= 1.0
    assert settings.forms_settle_post_submit_seconds <= 1.0
```

**Arquivo:** `tests/test_forms_worker_resilience.py` (já existe).

Adicionar teste que mockeia `page.wait_for_timeout` e captura os valores chamados, validando que correspondem aos settings (e não aos valores hardcoded antigos):

```python
def test_settle_values_come_from_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "forms_settle_url_load_seconds", 0.5)
    monkeypatch.setattr(settings, "forms_settle_after_checkout_discovery_seconds", 0.5)
    monkeypatch.setattr(settings, "forms_settle_post_submit_seconds", 0.5)
    # ... usar FakePage do teste existente, capturar wait_for_timeout calls
    # assert 500 in waits (em vez de 3000, 2000, 5000)
```

**Verificação prévia:** grep por `wait_for_timeout(3000)`, `wait_for_timeout(2000)`, `wait_for_timeout(5000)` nos testes — não devem existir asserts com esses valores.

### 1.6 Validação manual da Fase 1

Antes de mergear:

1. Subir worker localmente (`python -m sistema.app.forms_worker_main`).
2. Enfileirar 1 submissão checkin e 1 checkout via fixture/script.
3. Cronometrar via logs `forms_queue_processed` (campo `turnaround_ms`).
4. Esperado: turnaround ~7 s menor que baseline atual.

---

## 2. Fase 2 — Concorrência

### 2.1 Configuração

Em [sistema/app/core/config.py](../sistema/app/core/config.py):

```python
forms_worker_concurrency: int = 3
forms_worker_idle_poll_seconds: float = 0.25  # ex-FORMS_QUEUE_POLL_SECONDS, promovido a setting
```

Em [docker-compose.yml](../docker-compose.yml) `forms-worker.environment`:

```yaml
FORMS_WORKER_CONCURRENCY: ${FORMS_WORKER_CONCURRENCY:-3}
FORMS_WORKER_IDLE_POLL_SECONDS: ${FORMS_WORKER_IDLE_POLL_SECONDS:-0.25}
```

**Crítico — subir o pool de DB do worker:**

```yaml
FORMS_WORKER_DATABASE_POOL_SIZE: ${FORMS_WORKER_DATABASE_POOL_SIZE:-5}    # antes 2
FORMS_WORKER_DATABASE_MAX_OVERFLOW: ${FORMS_WORKER_DATABASE_MAX_OVERFLOW:-2}  # antes 1
```

Razão: 3 threads consumidoras + 1 supervisora escrevendo heartbeat = ≥ 4 conexões simultâneas. Folga de 1 evita bloqueio no claim atômico se houver retry. Postgres em produção está em `max_connections=40` ([docker-compose.yml:16](../docker-compose.yml#L16)) — folga abundante.

### 2.2 Refatoração de `FormsSubmissionWorker`

**Arquivo:** [sistema/app/services/forms_queue.py:664-783](../sistema/app/services/forms_queue.py#L664-L783).

**Novo modelo:**

```python
class FormsSubmissionWorker:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._consumer_threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        # estado agregado (mantém compatibilidade com snapshot existente)
        self._status = "stopped"
        self._started_at: datetime | None = None
        self._start_count = 0
        # estado per-thread (chave = thread.ident)
        self._per_thread: dict[int, dict] = {}
        # snapshot agregado lazy
        self._supervisor_backoff_seconds = 0.0

    def start(self) -> None:
        """Idempotente. Spawna threads consumidoras faltantes até atingir concurrency."""
        with self._lock:
            self._stop_event = threading.Event() if self._stop_event.is_set() else self._stop_event
            target_count = max(int(settings.forms_worker_concurrency), 1)
            alive = [t for t in self._consumer_threads if t.is_alive()]
            self._consumer_threads = alive
            if len(alive) >= target_count:
                return  # já tem o suficiente
            if not alive:
                # primeiro start: zera state
                self._started_at = now_sgt()
                self._per_thread = {}
                self._start_count += 1
                self._status = "starting"
            for i in range(target_count - len(alive)):
                thread_index = len(self._consumer_threads)
                t = threading.Thread(
                    target=self._run_consumer,
                    name=f"forms-submission-worker-{thread_index}",
                    daemon=True,
                )
                self._consumer_threads.append(t)
                t.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            threads = list(self._consumer_threads)
        for t in threads:
            t.join(timeout=2)
        with self._lock:
            self._consumer_threads = []
            self._status = "stopped"

    def stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def has_alive_consumers(self) -> bool:
        """API pública usada pelo supervisor (substitui leitura direta de _thread)."""
        with self._lock:
            return any(t.is_alive() for t in self._consumer_threads)

    def consumer_threads_alive_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._consumer_threads if t.is_alive())

    def mark_supervisor_restart_wait(self, *, backoff_seconds: float) -> None:
        with self._lock:
            self._status = "restarting"
            self._supervisor_backoff_seconds = backoff_seconds

    def snapshot(self) -> dict[str, object]:
        """Agrega estado per-thread em um snapshot único — preserva campos existentes."""
        with self._lock:
            alive_count = sum(1 for t in self._consumer_threads if t.is_alive())
            states = list(self._per_thread.values())
            running = alive_count > 0
            # status agregado: prioridade restarting > degraded > running > idle > stopped
            if self._status == "restarting":
                aggregated_status = "restarting"
            elif any(s.get("status") == "degraded" for s in states):
                aggregated_status = "degraded"
            elif alive_count == 0:
                aggregated_status = "stopped"
            elif any(s.get("status") == "running" for s in states):
                aggregated_status = "running"
            else:
                aggregated_status = "idle"
            # campos agregados
            last_loop_started_at = max(
                (s.get("last_loop_started_at") for s in states if s.get("last_loop_started_at")),
                default=None,
            )
            last_loop_completed_at = max(
                (s.get("last_loop_completed_at") for s in states if s.get("last_loop_completed_at")),
                default=None,
            )
            processed_total = sum(int(s.get("processed_total") or 0) for s in states)
            max_consecutive_errors = max((int(s.get("consecutive_errors") or 0) for s in states), default=0)
            max_backoff = max((float(s.get("current_backoff_seconds") or 0) for s in states), default=0.0)
            last_error = next(
                (s.get("last_error") for s in states if s.get("last_error")),
                None,
            )
            primary_thread_name = (
                self._consumer_threads[0].name
                if self._consumer_threads and self._consumer_threads[0].is_alive()
                else None
            )
            return {
                "running": running,
                "status": aggregated_status,
                "thread_name": primary_thread_name,  # mantido para retrocompat
                "started_at": self._started_at,
                "last_loop_started_at": last_loop_started_at,
                "last_loop_completed_at": last_loop_completed_at,
                "last_loop_processed_count": processed_total,  # semântica: total processado desde start
                "consecutive_error_count": max_consecutive_errors,
                "current_backoff_seconds": max(max_backoff, self._supervisor_backoff_seconds),
                "restart_count": max(self._start_count - 1, 0),
                "last_error": last_error,
                # campos NOVOS (compatíveis — testes existentes ignoram):
                "concurrency": int(settings.forms_worker_concurrency),
                "consumer_threads_alive": alive_count,
            }

    def _run_consumer(self) -> None:
        """Loop por thread consumidora — self-watchdog, nunca sai voluntariamente."""
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        with self._lock:
            self._per_thread[thread_id] = {
                "thread_name": thread_name,
                "status": "running",
                "last_loop_started_at": None,
                "last_loop_completed_at": None,
                "processed_total": 0,
                "consecutive_errors": 0,
                "current_backoff_seconds": 0.0,
                "last_error": None,
            }

        while not self._stop_event.is_set():
            with self._lock:
                state = self._per_thread[thread_id]
                state["status"] = "running"
                state["last_loop_started_at"] = now_sgt()

            try:
                # claim atômico + processamento de UM item
                submission_id = _reserve_next_submission_id()
                if submission_id is None:
                    processed = 0
                else:
                    _process_submission(submission_id)
                    processed = 1
            except Exception as exc:
                backoff_seconds = _compute_exponential_backoff_seconds(
                    base_seconds=FORMS_WORKER_ERROR_BACKOFF_BASE_SECONDS,
                    max_seconds=FORMS_WORKER_ERROR_BACKOFF_MAX_SECONDS,
                    attempt=state["consecutive_errors"] + 1,
                )
                with self._lock:
                    state["status"] = "degraded"
                    state["last_loop_completed_at"] = now_sgt()
                    state["consecutive_errors"] += 1
                    state["current_backoff_seconds"] = backoff_seconds
                    state["last_error"] = str(exc)[:1000]
                _log_forms_queue_event(
                    "forms_queue_consumer_error",
                    backoff_seconds=backoff_seconds,
                    consecutive_error_count=state["consecutive_errors"],
                    error=str(exc)[:1000],
                    thread_name=thread_name,
                )
                self._stop_event.wait(backoff_seconds)
                continue

            with self._lock:
                state["status"] = "idle" if processed == 0 else "running"
                state["last_loop_completed_at"] = now_sgt()
                state["processed_total"] += processed
                state["consecutive_errors"] = 0
                state["current_backoff_seconds"] = 0.0
                state["last_error"] = None
            if processed == 0:
                self._stop_event.wait(settings.forms_worker_idle_poll_seconds)
            # if processed > 0: continua imediatamente
```

**Pontos críticos do desenho:**

- **Self-watchdog**: cada `_run_consumer` envolve o trabalho em try/except. Threads nunca saem por exceção — só pelo `_stop_event`. Robustez máxima.
- **Backoff per-thread**: uma thread em backoff por erro **não bloqueia** as outras. Isso é o ganho principal sobre o desenho atual.
- **Claim atômico por item, não por lote**: o `_run` atual chama `process_forms_submission_queue_once(max_items=10)`. O novo desenho processa **1 item por vez por thread**, em loop. Cada item passa pelo claim → menor latência de pickup, melhor distribuição entre threads.
- **`start()` idempotente**: pode ser chamado várias vezes; só spawna threads faltantes. Crítico para o caso de uma thread morrer por algum motivo extremo (OOM no Chromium, etc.) e o supervisor reiniciar.

### 2.3 Supervisor

Em [forms_queue.py:789-862](../sistema/app/services/forms_queue.py#L789-L862), trocar:

```python
thread = forms_submission_worker._thread
if thread is not None and thread.is_alive():
```

por:

```python
if forms_submission_worker.has_alive_consumers():
```

O resto da lógica do supervisor (heartbeat, backoff exponencial em restart, escrita do health snapshot) permanece igual. A semântica fica:

- Enquanto **ao menos 1** consumer thread estiver viva → considera o worker "rodando", não dispara restart.
- Se **todas** as threads morrerem → dispara restart com backoff exponencial.
- O `start()` interno é idempotente e ressuscitará threads faltantes na próxima iteração.

### 2.4 Health snapshot e diagnóstico

Em [forms_queue.py:205-245](../sistema/app/services/forms_queue.py#L205-L245), `_build_observed_worker_snapshot`:

- Adicionar `concurrency` e `consumer_threads_alive` ao dict retornado, lendo do `raw_snapshot`:

```python
"concurrency": int(raw_snapshot.get("concurrency") or settings.forms_worker_concurrency),
"consumer_threads_alive": int(raw_snapshot.get("consumer_threads_alive") or 0),
```

Em [forms_queue.py:265-275](../sistema/app/services/forms_queue.py#L265-L275), `get_forms_worker_health_failure_reason`:

- **Não** acrescentar nova razão de unhealthy baseada em `consumer_threads_alive`. Justificativa: o `running` agregado já reflete "tem ao menos 1 consumer viva". Se quisermos sinalizar "rodando degradado" (ex: 1 viva de 3), isso vai no admin como info — mas não vira "worker down" para o usuário, porque a fila ainda drena.
- Resultado: testes em `test_forms_queue_worker_down_warning.py` continuam passando sem alteração.

### 2.5 Compatibilidade com `process_forms_submission_queue_once`

**Não tocar** em [forms_queue.py:509-517](../sistema/app/services/forms_queue.py#L509-L517). Função permanece serial. Os ~10 testes que a chamam direto seguem passando.

O novo `_run_consumer` **não chama** essa função — chama `_reserve_next_submission_id()` + `_process_submission()` direto.

### 2.6 Compatibilidade com `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit`

Esse teste em [test_api_flow.py:5776-5840](../tests/test_api_flow.py#L5776) tem uma `FakeWorker` que define `_thread = DeadThread()`. O supervisor antes lia `forms_submission_worker._thread.is_alive()`; agora vai chamar `has_alive_consumers()`.

**Atualização necessária no teste:**

```python
class FakeWorker:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread = None  # mantido por retrocompat de outros leitores
        self._consumer_threads = []  # NOVO
        self.start_calls = 0
        ...

    def start(self) -> None:
        self.start_calls += 1
        self._thread = DeadThread()
        self._consumer_threads = [DeadThread()]  # NOVO
        if self.start_calls >= 2:
            self._stop_event.set()

    def has_alive_consumers(self) -> bool:  # NOVO
        return False  # simula thread morta para gatilhar restart
    ...
```

**Verificar antes da implementação:** procurar outros pontos no código que leiam `forms_submission_worker._thread` direto. Grep prévio mostrou apenas o supervisor em `forms_queue.py:811`, mas vale uma segunda passada.

### 2.7 Testes novos da Fase 2

**Arquivo novo:** `tests/services/test_forms_worker_concurrency.py`.

Casos:

1. **`test_three_pending_items_processed_concurrently`**
   - Enfileirar 3 submissões com mock de `_process_submission` que dorme 2 s cada.
   - Setar `settings.forms_worker_concurrency=3`.
   - Disparar `forms_submission_worker.start()`, medir wall time.
   - Esperado: ≤ 3.5 s (3 em paralelo, não 6 s sequencial).
   - Limpar com `stop()`.

2. **`test_atomic_claim_under_thread_pressure`**
   - Enfileirar 10 submissões `pending`.
   - Disparar 5 threads chamando `_reserve_next_submission_id()` em loop.
   - Validar que cada submission é reservada por exatamente 1 thread (nenhuma dupla reserva, nenhuma perdida).
   - **Importante:** rodar tanto em SQLite (WAL mode) quanto via fixture Postgres se disponível.

3. **`test_one_consumer_error_does_not_block_others`**
   - 2 threads consumidoras.
   - Mockar `_process_submission` para a thread A levantar exceção uma vez, depois OK.
   - Enfileirar 5 submissões.
   - Esperado: thread A entra em backoff, thread B continua processando; todas as 5 são processadas; nenhuma fica presa em `processing`.

4. **`test_snapshot_aggregates_concurrency_info`**
   - Start com `concurrency=3`.
   - Aguardar threads ativarem.
   - Snapshot deve conter `concurrency=3` e `consumer_threads_alive=3`.
   - Stop. Snapshot deve mostrar `running=False`, `consumer_threads_alive=0`.

5. **`test_start_is_idempotent_and_respawns_missing_threads`**
   - Start com `concurrency=3`.
   - Matar manualmente uma thread (via `_stop_event` localizado ou raise).
   - Chamar `start()` de novo.
   - Validar que 3 threads voltam a estar vivas.

**Importante para os testes:** mockar `_process_submission` (não chamar Playwright real). Os testes devem ser rápidos (< 5 s no total) e isolados.

### 2.8 Validação manual da Fase 2

1. **Smoke com `concurrency=1`**: comportamento idêntico ao atual, sem regressão.
2. **Smoke com `concurrency=3`**: enfileirar 10 submissões fake (script de inje­ção `scripts/load/phase10_forms_backlog.example.json` já existe).
   - Medir `oldest_backlog_age_seconds` via `GET /api/admin/forms/queue/diagnostics`.
   - Esperado: drena em ~33% do tempo vs `concurrency=1`.
3. **Memória**: `docker stats forms-worker` durante a injeção. Anotar pico.
4. **Resiliência**: forçar erro em uma submissão (ex: chave inválida que dispara `FormsStepTimeoutError`). Validar via logs que só aquela thread aplicou backoff, as outras seguiram drenando.
5. **Health**: matar o worker container (`docker kill forms-worker`). Diagnóstico do admin deve mostrar `worker.running=false` e o aviso `forms_warn` deve disparar na próxima enqueue.

---

## 3. Sequência de implementação

| Passo | O quê | Onde | Risco |
|---|---|---|---|
| 1 | Settings novos (3 pausas + concurrency + idle_poll) | `core/config.py` | baixo |
| 2 | Substituir constantes por leitura inline de `settings` | `services/forms_worker.py` | baixo |
| 3 | Testes da Fase 1 | `tests/services/test_forms_submit_resilience.py`, `tests/test_forms_worker_resilience.py` | baixo |
| **— Commit A — pausas — pode ir para produção isolado —** | | | |
| 4 | Refatorar `FormsSubmissionWorker` para multi-thread | `services/forms_queue.py` | médio |
| 5 | Substituir `forms_submission_worker._thread` por `has_alive_consumers()` no supervisor | `services/forms_queue.py` | médio |
| 6 | Atualizar `_build_observed_worker_snapshot` com campos novos | `services/forms_queue.py` | baixo |
| 7 | Atualizar `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` | `tests/test_api_flow.py` | baixo |
| 8 | Adicionar testes de concorrência | `tests/services/test_forms_worker_concurrency.py` (novo) | médio |
| 9 | docker-compose: env novos + subir pool DB | `docker-compose.yml`, `.env.example`, `deploy/.env.production.example` | baixo |
| 10 | Atualizar `docs/forms_routine.md` §9.3 (lotes) e §13 (multi-thread) | `docs/forms_routine.md` | nenhum |
| **— Commit B — concorrência — depende do Commit A —** | | | |

**Estratégia de PRs:** 2 commits no mesmo PR ou 2 PRs separados. Recomendo 2 PRs para permitir:
- Ir para produção só o Commit A primeiro → medir impacto real das pausas isoladamente.
- Mergear Commit B depois, com baseline pós-A.

---

## 4. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| `POST_SUBMIT_SETTLE_SECONDS` 5→1 curto demais → Forms ainda processando quando `_wait_for_step(sucesso)` começa | Baixa | Falsos `forms_step_timeout` | `SUCCESS_SEARCH_TIMEOUT_SECONDS=60` cobre. Se regredir, env override `FORMS_SETTLE_POST_SUBMIT_SECONDS=3.0` sem deploy. |
| Pico de memória do worker container com 3 Chromiums | Média | Container reinicia (OOM), fila atrasa | Subir `concurrency` gradualmente em produção via env: `1 → 2 → 3`. Monitorar `docker stats`. |
| Playwright sync instável em multi-thread em alguma combinação Chrome/driver | Baixa | Crashes intermitentes em threads | Cada thread em `sync_playwright()` isolado é padrão suportado. Fallback: `FORMS_WORKER_CONCURRENCY=1` via env, sem precisar redeploy. |
| Dupla reserva do mesmo item entre threads | Muito baixa | Item processado 2x → dois CheckEvents de sucesso para mesma `request_id` | Claim atômico já tem checagem de `rowcount`. `UniqueConstraint` em `forms_submissions.request_id` impediria duplicação na fila desde o enqueue. Teste `test_atomic_claim_under_thread_pressure` blinda. |
| Snapshot agregado perde fidelidade — admin não enxerga qual thread está com erro | Baixa | Diagnóstico menos rico | Adicionar logs estruturados `forms_queue_consumer_error` com `thread_name`. Em incidente, basta filtrar log. |
| Teste `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` quebra ao trocar `_thread` por `has_alive_consumers` | Alta (se esquecermos) | CI quebra | Atualizar `FakeWorker` no Passo 7. Mitigado por estar explícito na sequência. |
| `process_forms_submission_queue_once` quebra por mudança colateral | Baixa | ~10 testes em CI quebram | Função explicitamente fora do escopo de mudança. Não tocar. |
| Memória do pool DB do worker insuficiente | Média | Threads bloqueiam em `db.acquire()` | Pool subido de 2+1 para 5+2 no Passo 9. Postgres `max_connections=40` tem folga. |
| Heartbeat do supervisor compete com threads pelo pool DB | Baixa | Heartbeat atrasa, status fica `stale` | Heartbeat não usa SessionLocal — escreve em arquivo. Sem competição. |

---

## 5. Observabilidade pós-deploy

Endpoint `GET /api/admin/forms/queue/diagnostics`:

| Campo | O que monitorar | Esperado pós-deploy |
|---|---|---|
| `recent_average_processing_ms` | tempo médio por submissão | cair ~40% (de ~25 s para ~15 s) |
| `oldest_backlog_age_seconds` | idade do item mais antigo na fila | cair rapidamente em rajadas (3 em paralelo) |
| `worker.concurrency` | concorrência configurada | `3` |
| `worker.consumer_threads_alive` | threads vivas | `3` em operação normal |
| `worker.status` | estado agregado | `running` ou `idle` |
| `worker.consecutive_error_count` | maior contador de erros entre threads | `0` se saudável |

Logs estruturados:

- `forms_queue_consumer_error` (novo) — erro per-thread com `thread_name`.
- `forms_queue_processed` (existente) — agora chega entrelaçado de threads diferentes; usar `thread_name` no campo se quiser segregar por thread em análise.

`CheckEvents` com `source="forms"`:
- Taxa de eventos sobe até 3× durante rajadas.
- Sem novos `actions` introduzidos — mantém `checkin`/`checkout` apenas.

---

## 6. O que **não** está no escopo

- Não tocar em `should_enqueue_forms_for_action` (regra de negócio sobre quando enfileirar).
- Não mudar `forms_max_retries` (continua `3`).
- Não mudar timeouts internos do Playwright (`FIELD_SEARCH_TIMEOUT_SECONDS`, `SUCCESS_SEARCH_TIMEOUT_SECONDS`, `STEP_CONFIRM_TIMEOUT_SECONDS`) — são proteções, não pausas.
- Não introduzir prioridade na fila — continua FIFO por `id`.
- Não mudar o endpoint `/api/admin/forms/queue/diagnostics` (só adiciona campos novos opcionais).
- Não tocar no frontend admin (admin2-web) — os campos novos no diagnostics ficam disponíveis caso queira-se mostrar depois, mas não é exigência desta entrega.

---

## 7. Checklist de pronto para mergear

### Commit A (pausas)
- [ ] Settings adicionados em `core/config.py`
- [ ] Constantes substituídas por `settings.*` inline em `forms_worker.py`
- [ ] Testes da Fase 1 passando (`pytest tests/services/test_forms_submit_resilience.py tests/test_forms_worker_resilience.py`)
- [ ] Todos os testes existentes passando
- [ ] docker-compose / .env.* atualizados
- [ ] Smoke manual: 1 submissão checkin + 1 checkout funcionam, ~7 s mais rápidas

### Commit B (concorrência)
- [ ] `FormsSubmissionWorker` refatorada com pool de threads
- [ ] Supervisor usa `has_alive_consumers()`
- [ ] Snapshot inclui `concurrency` e `consumer_threads_alive`
- [ ] `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` atualizado
- [ ] 5 testes novos em `test_forms_worker_concurrency.py` passando
- [ ] Pool DB do worker subido para 5+2 no docker-compose
- [ ] Todos os testes existentes passando
- [ ] Smoke manual: 10 submissões na fila drenam em ~33% do tempo
- [ ] `docker stats forms-worker` monitorado durante teste — pico abaixo do limite do droplet
- [ ] `docs/forms_routine.md` atualizado nas seções afetadas

---

## 8. Rollback

### Rollback do Commit A (pausas)

Sem deploy, via env:

```bash
FORMS_SETTLE_URL_LOAD_SECONDS=3.0
FORMS_SETTLE_AFTER_CHECKOUT_DISCOVERY_SECONDS=2.0
FORMS_SETTLE_POST_SUBMIT_SECONDS=5.0
```

Restart do container `forms-worker`. Recupera comportamento exatamente como antes.

### Rollback do Commit B (concorrência)

Opção 1 — sem deploy:

```bash
FORMS_WORKER_CONCURRENCY=1
```

Restart do container. Recupera comportamento single-thread, mantém todas as mudanças de código (que continuam corretas com `concurrency=1`).

Opção 2 — revert do commit. Mais drástico, só se o código novo causar instabilidade que `concurrency=1` não resolve.

---

## 9. Memória — Parte I

> Convenções globais em [§A](#apêndice--convenções-transversais). Esta seção é só o que é exclusivo da Parte I.

- **Código alvo:** `forms_worker.py` (pausas), `forms_queue.py` (concorrência), `core/config.py` (settings), `docker-compose.yml` (env + pool DB).
- **Testes que não podem quebrar:**
  - `tests/test_api_flow.py::test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` ([linha 5776](../tests/test_api_flow.py#L5776)) — requer atualizar `FakeWorker` com `has_alive_consumers`. **Esquecer este passo é a falha mais provável.**
  - `tests/services/test_forms_queue_worker_down_warning.py` — mocka snapshot inteiro; passa sem alteração se preservarmos `enabled`/`running`/`stale`/`consecutive_error_count`.
  - Todos os ~10 testes que chamam `process_forms_submission_queue_once(...)` — função intocada por design.
- **Decisões consolidadas (não revisitar sem motivo):**
  - Thread pool dentro do worker (não scale, não process pool).
  - Cap 1 s nas pausas; configurável via env.
  - `process_forms_submission_queue_once` permanece serial.
  - Self-watchdog por thread.
- **Próximo passo:** Commit A (passos 1-3 da sequência §3).

---

# Parte II — Correção do piscar do Admin2

## 10. Contexto e objetivos

O painel admin v2 ([sistema/app/static/admin2](../sistema/app/static/admin2)) tem as tabelas "Usuários em Check-in" e "Usuários em Check-Out" piscando continuamente em momentos de pico, mesmo quando os dados não mudam. O painel admin v1 ([sistema/app/static/admin](../sistema/app/static/admin)) tem exatamente o mesmo backend, o mesmo SSE, o mesmo `body.innerHTML = ""` + appendChild, e **não pisca**.

A diferença está numa camada de animação adicionada apenas no v2, que reanima toda linha em cada re-render. Como o re-render é frequente em pico (SSE + debounce 250 ms), os ciclos de animação se sobrepõem e produzem o piscar contínuo percebido pelo usuário.

### Objetivos mensuráveis

- Eliminar o piscar visual nas tabelas de check-in/check-out em pico.
- Reduzir o número de re-renders desnecessários (mesmo conteúdo → mesmo DOM, sem reanimar).
- Reduzir a pressão de fetches sobre o backend em pico (mitiga 504s ocasionais).
- **Não** quebrar a animação inicial das linhas no primeiro carregamento de cada aba (a animação `v2-row-enter` é estética e fica em outros contextos).

### Premissas

- Backend e SSE permanecem inalterados. Mudanças estritamente no frontend `admin2/app.js` e `admin2/styles.css`.
- O admin v1 segue como fallback intacto.
- Os endpoints `/api/admin/checkin` e `/api/admin/checkout` retornam JSON estável (a chave `id` ou `chave` por usuário é confiável como identificador de linha).

## 11. Diagnóstico — por que o v2 pisca

### 11.1 Causa raiz (confirmada por leitura de código)

Em [admin2/app.js:88-101](../sistema/app/static/admin2/app.js#L88-L101):

```js
function staggerRows(tbody) {
  const rows = Array.from(tbody.children);
  rows.forEach((row, i) => {
    row.classList.remove("v2-row-enter");
    row.style.setProperty("--row-i", String(Math.min(i, 30)));
  });
  requestAnimationFrame(() => rows.forEach((row) => row.classList.add("v2-row-enter")));
}
document.querySelectorAll("tbody").forEach((tbody) => {
  new MutationObserver((muts) => {
    if (muts.some((m) => m.addedNodes.length > 0)) staggerRows(tbody);
  }).observe(tbody, { childList: true });
});
```

Um `MutationObserver` global é registrado em **todos os `<tbody>`** da página. Sempre que linhas são adicionadas (o que acontece em todo `body.innerHTML = ""` + `appendChild`), `staggerRows` reaplica a classe `v2-row-enter` em todas as linhas.

A classe dispara a animação CSS definida em [admin2/styles.css:102-109](../sistema/app/static/admin2/styles.css#L102-L109):

```css
.v2-row-enter {
  animation: v2RowEnter 0.22s ease both;
  animation-delay: calc(var(--row-i, 0) * 14ms);
}
@keyframes v2RowEnter {
  from { opacity: 0; transform: translateY(-5px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

Cada linha entra com `opacity 0 → 1` e `translateY(-5px) → 0` em 0,22 s, com delay escalonado de 14 ms por linha (cap 30 linhas = 420 ms). **Duração total: até ~640 ms de fade-in por re-render.**

O ciclo se repete a cada SSE event (debounce 250 ms < 640 ms da animação), então em pico vários ciclos se sobrepõem → piscar contínuo.

### 11.2 Por que o admin v1 não pisca

O admin v1 ([sistema/app/static/admin/app.js](../sistema/app/static/admin/app.js)) faz exatamente o mesmo `body.innerHTML = ""` + `appendChild` em `renderPresenceTable` ([admin/app.js:3539-3550](../sistema/app/static/admin/app.js#L3539-L3550)), **mas não tem o `MutationObserver` nem a classe `v2-row-enter`**. Re-renders são instantâneos e visualmente imperceptíveis.

### 11.3 Fontes secundárias de ruído visual no v2

**Barra de progresso superior** em [admin2/app.js:8-43](../sistema/app/static/admin2/app.js#L8-L43): toda chamada a `/api/*` dispara uma barra animada (0% → 30% → 70% → 88% → 100%) no topo da página. Em pico, `refreshAutomaticTables` dispara 2-4 fetches em paralelo a cada SSE event → a barra fica sempre piscando.

**Refresh continua mesmo com aba escondida** em [admin2/app.js:5734-5747](../sistema/app/static/admin2/app.js#L5734-L5747): o handler `eventStream.onmessage` chama `requestRefreshAllTables()` independentemente de `document.hidden`. O `startAutoRefresh` ([admin2/app.js:5700-5708](../sistema/app/static/admin2/app.js#L5700-L5708)) checa `document.hidden`, mas o SSE não.

**Debounce 250 ms é curto demais para pico** em [admin2/app.js:197-198](../sistema/app/static/admin2/app.js#L197-L198): com SSE emitindo 4+ eventos/s em rajada, só agrupa o que chega em < 250 ms. A janela humana de percepção de "tempo real" é ~1 s — há folga para subir o debounce sem prejudicar a UX.

### 11.4 HTTP 504 (sintoma separado)

O 504 ocasional visto na barra de notificações é independente do piscar. Sob carga de pico, alguma das chamadas (`/api/admin/checkin`, `/api/admin/checkout` ou `/api/admin/stream`) estoura o timeout do proxy reverso. A mitigação de debounce maior (§12.4) ajuda indiretamente reduzindo a pressão no backend, mas a investigação de fundo dos endpoints fica fora do escopo desta seção.

## 12. Estratégia — três mudanças principais + três mitigações secundárias

### 12.1 Remover a animação stagger nas tabelas de presença (PRINCIPAL)

**Alvo:** o `MutationObserver` global em [admin2/app.js:97-101](../sistema/app/static/admin2/app.js#L97-L101) e a aplicação automática de `v2-row-enter` via `staggerRows`.

**Decisão:** remover completamente o observer global e o `staggerRows`. A classe `v2-row-enter` no CSS pode permanecer — fica apenas como utilitária, aplicável manualmente em pontos específicos se quisermos animação em modal de cadastro etc. Mas **nenhum reanimar automático** nas tabelas.

**Impacto colateral aceitável:** o primeiro carregamento das tabelas (após login) também não terá mais a animação stagger. Trade-off explícito: estética inicial sutil vs. piscar contínuo em produção. Vale.

### 12.2 Render por diff nas tabelas de check-in/check-out (PRINCIPAL)

**Alvo:** [admin2/app.js:3729-3740](../sistema/app/static/admin2/app.js#L3729-L3740) (`renderPresenceTable`).

**Estratégia:** introduzir um helper `renderRowsByDiff(bodyId, rows, buildRowFn, keyOfRow)` que:

1. Lê o cache de linhas atualmente no DOM (`Map<key, HTMLTableRowElement>`).
2. Para cada linha em `rows`:
   - Se a chave já existe no DOM **e** o HTML que ela renderiza é idêntico ao atual → reaproveita o `<tr>` existente, sem tocar.
   - Se a chave existe **mas** o HTML mudou → faz `tr.innerHTML = newHtml` (substitui só conteúdo, não cria nó novo).
   - Se a chave **não** existe → cria nó novo e insere na posição correta.
3. Linhas que não estão em `rows` mas estão no DOM são removidas.
4. Ordem do DOM é alinhada à ordem de `rows` movendo nós existentes (sem destruí-los) com `insertBefore`.

**Chave de identidade:** `row.chave` (4 caracteres alfanuméricos, único por usuário) é a chave natural. Adicionar `tr.dataset.rowKey = row.chave` no momento de criação.

**Comparação de HTML:** armazenar a serialização **completa** do `<tr>` (incluindo `class`, `dataset`, atributos) em um `WeakMap<HTMLTableRowElement, string>` externo, comparando contra o `tr.outerHTML` corrente antes de re-renderizar.

> **Por que `outerHTML` e não `innerHTML`:** as tabelas de presença aplicam classes condicionais no `<tr>` (ex.: status visual de check-in atrasado, destaque por ação recente). `innerHTML` ignoraria mudança de classe no próprio `<tr>` e deixaria a UI dessincronizada do estado real. `outerHTML` captura tudo.
>
> **Por que `WeakMap` e não `dataset.lastHtml`:** evita poluir o DOM com strings grandes (cada `<tr>` pode ter ~1-2 KB de HTML). `WeakMap` permite GC automático quando o nó sai do DOM. Custo: ~O(N) por refresh, irrelevante para N ≤ 200 linhas típicas.

**Por que isso elimina o piscar mesmo sem remover a animação:** se o `<tr>` não é recriado, o `MutationObserver` não dispara `addedNodes` para ele → `v2-row-enter` não é reaplicada. Mesmo que a animação fique no CSS, ela não é triggada em refreshes sem mudança real. Mas combinado com §12.1, é cinto-e-suspensórios — robustez máxima.

**Aplicar onde:** apenas em `renderPresenceTable` (checkin, checkout). As outras tabelas (`renderInactiveTable`, `renderMissingCheckoutTable`, `renderUsersTable`, etc.) podem manter o `innerHTML = ""` se quisermos minimizar escopo. **Sugestão:** começar pelas duas tabelas afetadas e estender para as outras só se reportarem piscar similar.

### 12.3 Remover o `MutationObserver` global em tbody (PRINCIPAL)

**Alvo:** [admin2/app.js:97-101](../sistema/app/static/admin2/app.js#L97-L101).

Já contemplado em §12.1, mas vale reforçar: o observer global em `document.querySelectorAll("tbody")` é problemático mesmo independentemente da animação. Ele:

- Roda em **todos** os tbodies, não só nos de check-in/check-out.
- Re-cria callbacks de animação a cada child append, mesmo em tabelas como "Eventos" (`databaseEventsBody`) que crescem com listagens grandes.
- Causa custo de mutation tracking permanente no DOM mesmo quando a animação não é o foco.

**Decisão:** remover o observer global. Se quisermos animação inicial em alguma tabela específica, aplicamos `v2-row-enter` explicitamente no momento do primeiro `appendChild` daquela tabela (controlado por uma flag `firstLoad`).

### 12.4 [SECUNDÁRIO] Pular re-render via SSE quando aba/janela escondida

**Alvo:** [admin2/app.js:5734-5747](../sistema/app/static/admin2/app.js#L5734-L5747) (`eventStream.onmessage`).

Adicionar guarda `if (document.hidden) return;` antes de `requestRefreshAllTables()`. Mantém o status `realtimeConnected = true` para o chrome (para a UI mostrar a conexão como ativa), mas não dispara fetches inúteis.

Ao voltar de `document.hidden = false`, o `startAutoRefresh` já cobre o catch-up (intervalo de 5 s pega o próximo refresh). Sem perda funcional.

### 12.5 [SECUNDÁRIO] Subir `REALTIME_DEBOUNCE_MS` de 250 → 600

**Alvo:** [admin2/app.js:198](../sistema/app/static/admin2/app.js#L198).

Subir para 600 ms agrupa mais eventos SSE consecutivos em pico, reduzindo o número de refreshes pela metade ou mais. A latência percebida de "tempo real" continua imperceptível (humanos só notam latência > ~1 s em UI passiva).

Trade-off mínimo. Mitiga adicionalmente a pressão sobre os endpoints `/api/admin/checkin` e `/api/admin/checkout`, o que reduz a chance dos 504s ocasionais.

### 12.6 [SECUNDÁRIO] Ignorar barra de progresso para fetches automáticos do SSE

**Alvo:** [admin2/app.js:8-43](../sistema/app/static/admin2/app.js#L8-L43) (interceptador global de `window.fetch`).

**Estratégia:** o `refreshAutomaticTables` chamado pelo handler SSE marca seus fetches com um header custom (ex: `X-Realtime-Refresh: 1`) ou com um símbolo no `init` (ex: `{ realtimeRefresh: true }`). O interceptor de progresso pula essas chamadas.

Implementação: criar um wrapper `fetchSilent(url, options)` que chama `fetch` com uma flag no objeto `options`. O interceptor checa essa flag antes de incrementar `_pending`.

Resultado: a barra de progresso só aparece em ações do usuário (clique em botão, salvar, etc.), não em refreshes automáticos. Drasticamente menos "ruído visual" em pico.

**Impacto colateral:** se um refresh automático demorar, o usuário não vê a barra — mas esse caso é raro e o status fica visível em `setStatus` se der erro. Trade-off aceitável.

## 13. Sequência de implementação

| Passo | O quê | Onde | Risco |
|---|---|---|---|
| 1 | Remover `MutationObserver` global em tbody (§12.1 + §12.3) | `admin2/app.js:88-101` | baixo |
| 2 | Remover função `staggerRows` (sem chamadas restantes) | `admin2/app.js:88-96` | nenhum |
| 3 | Render por diff em `renderPresenceTable` (§12.2) | `admin2/app.js:3729-3740` | médio |
| 4 | Testes manuais: smoke nas tabelas checkin/checkout em pico | navegador | — |
| **— Commit C — fim do piscar — pode ir para produção isolado —** | | | |
| 5 | Guarda `document.hidden` no SSE onmessage (§12.4) | `admin2/app.js:5734-5747` | baixo |
| 6 | Subir `REALTIME_DEBOUNCE_MS` para 600 (§12.5) | `admin2/app.js:198` | baixo |
| 7 | Wrapper `fetchSilent` para refreshes automáticos (§12.6) | `admin2/app.js:8-43` + uso em `refreshAutomaticTables` | médio |
| 8 | Testes manuais: verificar barra de progresso só dispara em ações do usuário | navegador | — |
| **— Commit D — mitigações secundárias — depende do Commit C —** | | | |

**Estratégia de PRs:** 2 PRs. Commit C resolve o problema reportado pelo usuário; Commit D é refinamento. Permite mergear C e medir antes de aplicar D.

## 14. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Diff render quebra ordenação ao trocar `sortKey`/`sortDirection` | Média | Linhas em ordem errada após reorder | Diff também reorganiza a posição dos nós existentes (`insertBefore` na posição correta de `rows`). Teste manual: clicar em coluna para inverter ordem e validar. |
| Chave `row.chave` colidir entre tabelas | Muito baixa | Linha "errada" reaproveitada | A chave é única por usuário (4-char alfanumérico). Caches são por tabela (`bodyId`), não globais. Sem colisão possível. |
| Cache de `outerHTML` no `WeakMap` ficar dessincronizado de mutações externas (clique em "Remover", etc.) | Baixa | Linha não atualiza após ação do usuário | Ações do usuário disparam refresh completo de qualquer modo. Mesmo se o cache ficar stale, o próximo refresh corrige. |
| Mobile detection (`isMobileAdminViewport`) muda layout em resize → linha precisa ser reconstruída | Baixa | Diff não detecta mudança de variante mobile | Anexar `tr.dataset.responsiveVariant` no momento da renderização. Como `outerHTML` inclui `dataset`, mudança de variante invalida o cache automaticamente. |
| Remover animação stagger quebra teste UI em `tests/check_admin_presence_forms_layout.test.js` | Baixa | CI quebra | Verificar antes via grep se o teste depende de `v2-row-enter`. Se sim, atualizar. |
| `document.hidden` ser pessimista (browser falsamente reportar `hidden` em alguns casos) | Muito baixa | Refresh perdido em background | Catch-up via `startAutoRefresh` (5 s) cobre. |
| Subir debounce para 600 ms percebido como "lento" pelo usuário | Baixa | Reclamação subjetiva | Ajustável via constante. Se chiar, voltar para 400 ou 500. |
| Wrapper `fetchSilent` esquecer de marcar algum fetch automático → barra ainda pisca | Média | Mitigação parcial | Auditar lista de fetches em `refreshAutomaticTables` e suas dependências. Testar com aba aberta em modo idle. |

## 15. Validação pós-deploy

### 15.1 Smoke manual

1. Abrir admin2 logado com perfil 9 em modo desktop.
2. Em ambiente com tráfego (ou simulando via curl para `/api/admin/checkin` repetidamente disparar SSE), observar tabela "Usuários em Check-in" por 60 s.
3. **Esperado:** nenhum piscar visível. Linhas estáticas. Quando alguém faz check-in real, só a linha nova aparece (sem reanimar as outras).
4. Repetir com tabela "Usuários em Check-Out".
5. Clicar em coluna para reordenar — linhas devem reordenar visualmente, sem piscar.
6. Filtrar via input de filtro — linhas que saem do filtro somem, as que entram aparecem; nenhuma reanimação das que permaneceram visíveis.

### 15.2 Pós-Commit D

7. Minimizar a janela do navegador por 2 minutos com SSE ativo. Voltar. Validar via DevTools Network que nenhum fetch a `/api/admin/checkin` ou `/api/admin/checkout` ocorreu durante o tempo escondido.
8. Disparar ação do usuário (ex: salvar projeto). Barra de progresso aparece. Sem ação, barra fica invisível mesmo com SSE ativo.

### 15.3 Métricas de backend (opcional)

- Logs do nginx/proxy: contar requests a `/api/admin/checkin` e `/api/admin/checkout` por minuto antes e depois do Commit D. Esperado: queda de ~60% sob mesma carga.
- Se houver 504s antes, esperar redução significativa após Commit D.

## 16. O que **não** está no escopo

- Não tocar no admin v1 ([sistema/app/static/admin](../sistema/app/static/admin)). Continua intacto como fallback.
- Não tocar no backend (`/api/admin/checkin`, `/api/admin/checkout`, `/api/admin/stream`).
- Não investigar causa raiz dos 504s no backend. Apenas mitigar pressão. Investigação separada se persistir.
- Não tocar em outras animações do v2 (`v2-tab-enter`, `v2-modal-enter`, `accidentPulse`). Foco exclusivo no piscar das tabelas de presença.
- Não estender o render por diff para outras tabelas além de checkin/checkout (a menos que reportem piscar).

## 17. Checklist de pronto para mergear

### Commit C (núcleo da correção)
- [ ] `MutationObserver` global em tbody removido
- [ ] Função `staggerRows` removida (sem chamadas restantes — confirmado via grep)
- [ ] `renderPresenceTable` usa diff por chave; `outerHTML` cacheado em `WeakMap<HTMLTableRowElement, string>`
- [ ] `responsiveVariant` incluída na chave de invalidação (ou no `outerHTML` capturado)
- [ ] Smoke manual em desktop e mobile com tráfego simulado
- [ ] Reordenação por coluna funciona sem piscar
- [ ] Filtros funcionam sem piscar
- [ ] Adição de linha nova continua visível (pode ou não animar — escolha consciente)
- [ ] Testes existentes em `tests/check_admin_presence_forms_layout.test.js` passando
- [ ] Admin v1 intacto (smoke rápido)

### Commit D (mitigações secundárias)
- [ ] Guarda `document.hidden` no handler SSE
- [ ] `REALTIME_DEBOUNCE_MS` em 600
- [ ] `fetchSilent` (ou equivalente) implementado e aplicado em `refreshAutomaticTables`
- [ ] Barra de progresso só dispara em ações explícitas do usuário
- [ ] Smoke manual: aba escondida não dispara fetches
- [ ] Sem regressão no Commit C

## 18. Rollback

### Rollback do Commit C

Sem deploy fácil (frontend é estático): reverter o commit no git e redeploy. Não há env var para desligar diff render — é mudança de código.

**Mitigação:** o admin v1 continua disponível em [sistema/app/static/admin](../sistema/app/static/admin). Se admin v2 quebrar, os administradores podem usar v1 enquanto o rollback é deployado.

### Rollback do Commit D

Idem — reverter no git. As 3 mitigações são pequenas e isoladas; podem ser revertidas individualmente se uma específica causar problema.

## 19. Memória — Parte II

> Convenções globais em [§A](#apêndice--convenções-transversais). Esta seção é só o que é exclusivo da Parte II.

- **Código alvo:** [admin2/app.js](../sistema/app/static/admin2/app.js), [admin2/styles.css](../sistema/app/static/admin2/styles.css).
- **Pontos exatos do piscar:**
  - [admin2/app.js:88-101](../sistema/app/static/admin2/app.js#L88-L101) — `MutationObserver` global + `staggerRows` (REMOVER).
  - [admin2/styles.css:102-109](../sistema/app/static/admin2/styles.css#L102-L109) — animação `v2RowEnter` (manter no CSS, mas sem auto-aplicação).
  - [admin2/app.js:3729-3740](../sistema/app/static/admin2/app.js#L3729-L3740) — `renderPresenceTable` (REESCREVER com diff).
- **Por que admin v1 não pisca:** comparar com [admin/app.js:3539-3550](../sistema/app/static/admin/app.js#L3539-L3550) — backend e SSE idênticos, mas v1 não tem observer nem animação.
- **Decisões consolidadas:**
  - Remover totalmente observer + `staggerRows` (não "preservar só no primeiro load").
  - Diff só em checkin/checkout; outras tabelas seguem como estão.
  - Chave de identidade: `row.chave`.
  - Cache: `WeakMap<HTMLTableRowElement, string>` com `outerHTML` (não `dataset.lastHtml`, não `innerHTML`).
- **Próximo passo:** Commit C (passos 1-3 da sequência §13).

---

# Parte III — Colunas Forms, Transporte e Emergência na tabela de Projetos

## 20. Contexto e objetivos

A tabela "Projetos" na aba "Cadastro" do admin2 ([sistema/app/static/admin2](../sistema/app/static/admin2)) permite criar, editar e remover projetos. Hoje cada projeto tem só dados de localização (nome, país, endereço, ZIP, fuso). Precisamos enriquecer com três controles operacionais por projeto:

- **Forms** (toggle on/off por projeto): quando OFF, o sistema **não enfileira** preenchimento do Microsoft Forms para atividades desse projeto. Quando ON (default), comportamento atual permanece. Outros projetos com ON seguem normais.
- **Transporte** (toggle on/off por projeto): quando ON, o Check Web ([sistema/app/static/check](../sistema/app/static/check)) mostra o botão de transporte na tela principal. Quando OFF, o botão some e Check-In/Check-Out ocupam a largura completa do grid. **Adicionalmente:** renomear o label do botão de "Em Teste" para "Transporte" em todos os idiomas.
- **Emergência** (telefone, string): número de telefone fornecido pela contratada para chamadas de atendimento a acidentes. **Detalhamento de uso fica para o futuro.** Por enquanto, apenas o cadastro do campo (DB + UI).

### Objetivos mensuráveis

- Toggle Forms desligado num projeto faz com que zero `FormsSubmission` seja criada para atividades desse projeto, sem afetar os demais.
- Toggle Transporte desligado num projeto faz o botão sumir do Check Web e o grid colapsar de 3 → 2 colunas.
- Label do botão exibe "Transporte" (PT) / "Transport" (EN) / etc. em todas as situações, independente do toggle (a label do botão é estática; o que muda é a visibilidade).
- Campo de emergência aceita, persiste e expõe um telefone arbitrário no painel admin. Sem uso funcional ainda.

### Premissas

- Defaults dos toggles novos = `True` (ligado) para preservar comportamento atual em produção. Todos os projetos existentes continuam preenchendo Forms e mostrando botão de Transporte após a migration.
- Telefone padrão = `""` (vazio). Não há validação rígida de formato agora — virá quando a feature de chamada de emergência for desenhada.
- Mudanças nos endpoints `/api/admin/projects` (GET/POST/PUT) são aditivas (campos novos opcionais nos requests).
- O Check Web já recarrega o `state` ([/api/web/check/state](../sistema/app/routers/web_check.py#L737)) ao trocar projeto ativo via membership selector — então o `transport_enabled` precisa entrar no payload desse state.

## 21. Levantamento técnico — pontos de mudança

### 21.1 Model e migration

**Arquivo:** [sistema/app/models.py:10-20](../sistema/app/models.py#L10-L20) (`class Project`).

Adicionar:

```python
forms_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa.true())
transport_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa.true())
emergency_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
```

**Migration nova:** `alembic/versions/0066_add_project_forms_transport_emergency_columns.py`.

`upgrade()`:
- `op.add_column("projects", sa.Column("forms_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))`
- `op.add_column("projects", sa.Column("transport_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))`
- `op.add_column("projects", sa.Column("emergency_phone", sa.String(32), nullable=False, server_default=""))`

`downgrade()`:
- `op.drop_column("projects", "emergency_phone")`
- `op.drop_column("projects", "transport_enabled")`
- `op.drop_column("projects", "forms_enabled")`

**Importante:** o `server_default` garante que rows existentes em produção (Postgres) ganhem os defaults sem erro de NOT NULL. SQLite em dev também respeita o default.

### 21.2 Schemas Pydantic

**Arquivo:** [sistema/app/schemas.py:1083-1180](../sistema/app/schemas.py#L1083) (`ProjectRow`, `ProjectCreate`, `ProjectUpdate`).

Adicionar em `ProjectRow`:

```python
forms_enabled: bool
transport_enabled: bool
emergency_phone: str
```

Adicionar em `ProjectCreate` e `ProjectUpdate`:

```python
forms_enabled: bool = True
transport_enabled: bool = True
emergency_phone: str = Field(default="", max_length=32)

@field_validator("emergency_phone", mode="before")
@classmethod
def validate_emergency_phone(cls, value: object) -> str:
    # normalizar: aceita string vazia, strip whitespace, mantém formato livre por ora
    if value is None:
        return ""
    return str(value).strip()[:32]
```

### 21.3 Endpoints admin

**Arquivo:** [sistema/app/routers/admin.py](../sistema/app/routers/admin.py) (procurar handlers de `/api/admin/projects`).

- `GET /api/admin/projects` → response inclui `forms_enabled`, `transport_enabled`, `emergency_phone`.
- `POST /api/admin/projects` → aceita os 3 novos campos no request body (com defaults se omitidos).
- `PUT /api/admin/projects/{project_id}` → aceita atualização parcial dos 3 campos.
- `DELETE /api/admin/projects/{project_id}` → sem mudança (cascata permanece).

**Atenção:** ao mudar o request schema do POST/PUT, manter os campos novos como **opcionais com default** no Pydantic — clientes legados que não enviam continuam funcionando.

**Comportamento do PUT (merge, não substituição):**

O `ProjectUpdate` schema deve aceitar campos individualmente opcionais (`Optional[bool] = None`) e o handler deve aplicar **apenas os campos presentes no payload** sobre o registro existente. Isso suporta tanto o uso atual (modal "Editar" envia o objeto inteiro) quanto o PATCH-like dos toggles (`{ "forms_enabled": false }`).

```python
# em ProjectUpdate (mudança incremental: campos viram Optional)
forms_enabled: bool | None = None
transport_enabled: bool | None = None
emergency_phone: str | None = Field(default=None, max_length=32)

# no handler do PUT (pseudocode)
update_data = payload.model_dump(exclude_unset=True)
for key, value in update_data.items():
    setattr(project, key, value)
```

`exclude_unset=True` garante que campos omitidos não viram `None` no banco.

**Notificação SSE ao alterar `transport_enabled`:**

Quando o PUT muda `transport_enabled`, o handler deve chamar `notify_web_check_data_changed("project_transport_flag")` para que o Check Web atualize em tempo real. Sem isso, usuários conectados continuariam vendo o botão antigo até relogar.

```python
# após commit do update
if "transport_enabled" in update_data:
    notify_web_check_data_changed("project_transport_flag")
```

**Log de auditoria ao desligar Forms/Transporte:**

Quando o PUT desliga (transição `True → False`) algum dos flags, gravar `CheckEvent` de auditoria:

```python
# carregar valor anterior antes do update; depois comparar
if previous_forms_enabled and not project.forms_enabled:
    log_event(
        db,
        source="admin",
        action="proj_forms_off",      # ≤ 16 chars conforme convenção CheckEvent.action
        status="warning",
        message=f"Forms desativado para projeto {project.name}",
        project=project.name,
        details=f"actor_admin_user_id={identity.admin_user.id}",
    )

if previous_transport_enabled and not project.transport_enabled:
    log_event(
        db,
        source="admin",
        action="proj_trans_off",
        status="warning",
        message=f"Transporte desativado para projeto {project.name}",
        project=project.name,
        details=f"actor_admin_user_id={identity.admin_user.id}",
    )
```

> **Endpoint requer `require_admin_identity`** (não apenas `require_full_admin_session`) para ter o `AdminActorIdentity` disponível para a FK de auditoria. Conferir convenção em [CLAUDE.md §Identidade de admin](../CLAUDE.md).

### 21.4 Gate no Forms — onde checar `forms_enabled`

**Arquivo:** [sistema/app/services/forms_submit.py:44](../sistema/app/services/forms_submit.py#L44) (`submit_forms_event`).

**Decisão de design:** checar `forms_enabled` **antes** do `should_enqueue_forms_for_action(...)`. Se o projeto está desligado, segue o caminho de "skip" (`record_forms_submission_skip(...)`) com `skip_reason="forms_disabled_for_project"`. Resultado:
- Nenhuma `FormsSubmission(status="pending")` é criada.
- `UserSyncEvent` ainda é gravado (histórico interno preservado).
- `CheckEvent` é gravado com status `updated` e `forms_skipped=true`, `reason=forms_disabled_for_project`.
- API responde 200 normal ao cliente. Trans­parente.

**Por que aqui e não no worker:** o worker já estaria com o Chromium aberto. Bloquear no enqueue economiza recurso e simplifica o log de auditoria. A pergunta "Forms está habilitado para este projeto?" pertence à camada de regra de negócio, não à execução do Playwright.

**Implementação proposta:**

```python
# em services/forms_submit.py, dentro de submit_forms_event(...), antes do bloco que
# calcula latest_activity e should_queue_forms:

from .project_catalog import is_forms_enabled_for_project  # nova função

if not is_forms_enabled_for_project(db, projeto=projeto):
    skip_reason = "forms_disabled_for_project"
    # segue caminho de skip existente — apenas troca o reason
    ...
```

**Novo helper em [sistema/app/services/project_catalog.py](../sistema/app/services/project_catalog.py):**

```python
def is_forms_enabled_for_project(db: Session, *, projeto: str) -> bool:
    normalized = (projeto or "").strip().upper()
    if not normalized:
        return True  # sem projeto → comportamento padrão (não bloqueia)
    row = db.execute(
        select(Project.forms_enabled).where(Project.name == normalized)
    ).scalar_one_or_none()
    return bool(row) if row is not None else True  # projeto desconhecido → não bloqueia
```

**Edge case — `project_candidates`:** o `enqueue_forms_submission(...)` recebe `project_candidates` (lista de fallback para resolver XPath no worker). A decisão `forms_enabled` é sobre o `projeto` ativo informado, **não** sobre os candidates. Outros projetos do usuário não influenciam o gate.

### 21.5 Gate no Check Web — onde expor `transport_enabled`

**Arquivo:** [sistema/app/routers/web_check.py:737-744](../sistema/app/routers/web_check.py#L737-L744) e adjacências (`build_web_check_history_state`).

O response model `WebCheckHistoryResponse` precisa expor o flag `transport_enabled` do projeto ativo do usuário. Adicionar campo:

```python
# em schemas.py, na classe WebCheckHistoryResponse:
transport_enabled: bool = True
```

E em `build_web_check_history_state` (ou função equivalente que monta o state), resolver:

```python
transport_enabled = is_transport_enabled_for_project(db, projeto=user.projeto)
```

Com helper análogo ao do Forms:

```python
def is_transport_enabled_for_project(db: Session, *, projeto: str) -> bool:
    normalized = (projeto or "").strip().upper()
    if not normalized:
        return True
    row = db.execute(
        select(Project.transport_enabled).where(Project.name == normalized)
    ).scalar_one_or_none()
    return bool(row) if row is not None else True
```

**Por que no state e não em um endpoint separado:** o frontend já consome `/api/web/check/state` no boot e ao trocar projeto. Adicionar um campo é zero round-trip extra.

### 21.6 Frontend admin2 — tabela de Projetos

**Arquivos:**
- [sistema/app/static/admin2/index.html:521-527](../sistema/app/static/admin2/index.html#L521-L527) — cabeçalho da tabela.
- [sistema/app/static/admin2/app.js:4752-4766](../sistema/app/static/admin2/app.js#L4752-L4766) — `makeProjectRow`.
- [sistema/app/static/admin2/app.js:5049-5071](../sistema/app/static/admin2/app.js#L5049-L5071) — `loadProjects` e save handlers (procurar `postJson("/api/admin/projects"...)` em torno da linha 5177).

**Mudanças no `<thead>`:**

```html
<tr>
  <th>Nome do Projeto</th>
  <th>País</th>
  <th>Endereço</th>
  <th>ZIP Code</th>
  <th>Fuso horário</th>
  <th>Forms</th>
  <th>Transporte</th>
  <th>Emergência</th>
  <th>Ações</th>
</tr>
```

**Mudanças em `makeProjectRow(project)`:**

Adicionar 3 colunas antes da coluna "Ações":

```js
function makeProjectRow(project) {
  const tr = document.createElement("tr");
  const formsChecked = project.forms_enabled ? "checked" : "";
  const transportChecked = project.transport_enabled ? "checked" : "";
  const emergencyValue = escapeHtml(project.emergency_phone || "");
  tr.innerHTML = `
    <td>${escapeHtml(project.name)}</td>
    <td>${escapeHtml(project.country_name || "-")}</td>
    <td>${escapeHtml(project.address || "-")}</td>
    <td>${escapeHtml(project.zip_code || "-")}</td>
    <td>${escapeHtml(formatTimeZoneLabel(project.timezone_label))}</td>
    <td>
      <label class="toggle-switch">
        <input type="checkbox" data-project-forms-toggle="${project.id}" ${formsChecked} />
        <span class="toggle-slider"></span>
      </label>
    </td>
    <td>
      <label class="toggle-switch">
        <input type="checkbox" data-project-transport-toggle="${project.id}" ${transportChecked} />
        <span class="toggle-slider"></span>
      </label>
    </td>
    <td>
      <input type="tel" class="inline project-emergency-input" data-project-emergency-input="${project.id}" value="${emergencyValue}" maxlength="32" placeholder="—" />
    </td>
    <td class="pending-actions user-actions">
      <button type="button" class="secondary-button" data-project-edit="${project.id}">Editar</button>
      <button type="button" class="secondary-button" data-project-remove="${project.id}">Remover</button>
    </td>
  `;
  return tr;
}
```

**Handlers de evento — onde conectar:**

Em algum lugar próximo ao bloco onde se registram outros handlers de projeto (procurar `data-project-edit` listener), adicionar:

```js
projectsBody.addEventListener("change", async (evt) => {
  const formsToggle = evt.target.closest("[data-project-forms-toggle]");
  const transportToggle = evt.target.closest("[data-project-transport-toggle]");
  if (formsToggle) {
    await patchProjectFlag(formsToggle.dataset.projectFormsToggle, { forms_enabled: formsToggle.checked });
    return;
  }
  if (transportToggle) {
    await patchProjectFlag(transportToggle.dataset.projectTransportToggle, { transport_enabled: transportToggle.checked });
    return;
  }
});

projectsBody.addEventListener("blur", async (evt) => {
  const emergencyInput = evt.target.closest("[data-project-emergency-input]");
  if (emergencyInput) {
    await patchProjectFlag(emergencyInput.dataset.projectEmergencyInput, { emergency_phone: emergencyInput.value });
  }
}, true);  // useCapture para pegar blur

async function patchProjectFlag(projectId, payload) {
  try {
    await putJson(`/api/admin/projects/${projectId}`, payload);
    setStatus("Projeto atualizado.", true);
  } catch (error) {
    setStatus(error.message || "Falha ao atualizar projeto.", false);
    await loadProjects();  // resync UI ao estado real
  }
}
```

**Decisão de UX — confirmação ao desligar Forms:**

Mostrar `confirm()` (ou modal customizado) ao **desligar** Forms ou Transporte. Não confirmar ao ligar. Texto sugerido:

- Forms: "Tem certeza de que quer desligar o preenchimento do Microsoft Forms para o projeto X? Atividades dos usuários continuam sendo registradas, mas o Forms deixa de ser enviado."
- Transporte: "Tem certeza de que quer ocultar o botão de Transporte para os usuários do projeto X?"

Se o usuário cancelar, reverter o toggle no DOM (`evt.target.checked = !evt.target.checked` antes de retornar).

**CSS — toggle switch:**

Verificar se já existe `.toggle-switch` no [styles.css](../sistema/app/static/admin2/styles.css) (procurar). Se não, adicionar componente simples:

```css
.toggle-switch { position: relative; display: inline-block; width: 40px; height: 22px; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider { position: absolute; inset: 0; background: #ccc; border-radius: 22px; cursor: pointer; transition: 0.2s; }
.toggle-slider::before { content: ""; position: absolute; height: 18px; width: 18px; left: 2px; top: 2px; background: white; border-radius: 50%; transition: 0.2s; }
.toggle-switch input:checked + .toggle-slider { background: var(--accent-color, #1976d2); }
.toggle-switch input:checked + .toggle-slider::before { transform: translateX(18px); }
```

**Mobile responsive:** verificar se `applyResponsiveLabels` (que seta `data-label` em cada `<td>`) cobre as novas colunas — ele lê os headers automaticamente, então deve cobrir sem mudança ([app.js:2222-2242](../sistema/app/static/admin2/app.js#L2222-L2242)).

### 21.7 Frontend Check Web — esconder botão de Transporte e renomear label

**Arquivos:**
- [sistema/app/static/check/index.html:181-194](../sistema/app/static/check/index.html#L181-L194) — fieldset do `registrationField`.
- [sistema/app/static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js) — 6 ocorrências de `transportTestingLabel` (linhas 58, 547, 997, 1291, 1585, 1879).
- [sistema/app/static/check/app.js:1389](../sistema/app/static/check/app.js#L1389) — aplicação do label em runtime.

**Mudança 1 — renomear chave i18n:**

Renomear `transportTestingLabel` → `transportLabel` nos 6 dicionários e alterar os valores:

| Idioma | Antes | Depois |
|---|---|---|
| pt | "Em Teste" | "Transporte" |
| en | "In Testing" | "Transport" |
| zh | "测试中" | "运输" |
| ms | "Dalam Ujian" | "Pengangkutan" |
| id | "Dalam Uji Coba" | "Transportasi" |
| tl | "Sinusubukan" | "Transportasyon" |

E em [app.js:1389](../sistema/app/static/check/app.js#L1389):

```js
applyTextContent(transportActionLabel, t('registration.transportLabel'));  // antes: transportTestingLabel
```

**Mudança 2 — visibilidade controlada pelo state:**

O `state` retornado por `/api/web/check/state` já é consumido no boot do Check Web. Adicionar leitura do `transport_enabled` e aplicar:

```js
function applyTransportEnabledFlag(state) {
  const enabled = state?.transport_enabled !== false;  // default = true por segurança
  const choiceGrid = transportButton ? transportButton.closest('.choice-grid') : null;
  if (!transportButton || !choiceGrid) return;

  if (enabled) {
    transportButton.classList.remove('hidden');
    choiceGrid.classList.remove('two-columns');
    choiceGrid.classList.add('three-columns');
  } else {
    transportButton.classList.add('hidden');
    choiceGrid.classList.remove('three-columns');
    choiceGrid.classList.add('two-columns');
  }
}
```

Chamar em todo ponto que recebe um novo `state` (após login, após swap de projeto, após refresh do state via SSE/polling). O grep para confirmar pontos: `applyStateResponse`, `handleStateUpdated`, `refreshState`.

**Importante:** preservar a classe `hidden` consistente com o resto do app (procurar `.hidden { display: none; }` no styles.css; é o padrão usado em vários lugares).

### 21.8 Resumo dos pontos de mudança

| Camada | Arquivo | Mudança |
|---|---|---|
| DB | `alembic/versions/0066_add_project_forms_transport_emergency_columns.py` (novo) | 3 colunas + defaults |
| Model | `sistema/app/models.py` | 3 `mapped_column` em `Project` |
| Schema | `sistema/app/schemas.py` | `ProjectRow`, `ProjectCreate`, `ProjectUpdate` ganham 3 campos |
| Router admin | `sistema/app/routers/admin.py` | GET/POST/PUT expõem/aceitam 3 campos; PUT faz merge (`exclude_unset`); PUT dispara `notify_web_check_data_changed` + log de auditoria nas transições ON→OFF; endpoint migra para `require_admin_identity` |
| Service catalog | `sistema/app/services/project_catalog.py` | 2 helpers novos: `is_forms_enabled_for_project`, `is_transport_enabled_for_project` |
| Service forms | `sistema/app/services/forms_submit.py` | Gate `forms_enabled` antes do enqueue (skip com reason) |
| Schema web | `sistema/app/schemas.py` (`WebCheckHistoryResponse`) | Campo `transport_enabled: bool` |
| Router web | `sistema/app/routers/web_check.py` (`build_web_check_history_state`) | Popula `transport_enabled` |
| Admin2 HTML | `sistema/app/static/admin2/index.html` | 3 colunas novas no `<thead>` |
| Admin2 JS | `sistema/app/static/admin2/app.js` | `makeProjectRow` + handlers `change`/`blur` + `patchProjectFlag` |
| Admin2 CSS | `sistema/app/static/admin2/styles.css` | `.toggle-switch` + `.toggle-slider` (se não existir) |
| Check i18n | `sistema/app/static/check/i18n-dictionaries.js` | Rename `transportTestingLabel` → `transportLabel` em 6 idiomas |
| Check JS | `sistema/app/static/check/app.js` | Atualizar referência i18n + `applyTransportEnabledFlag` |

## 22. Sequência de implementação

| Passo | O quê | Onde | Risco |
|---|---|---|---|
| 1 | Migration 0066 + model `Project` com 3 campos | `alembic/versions/0066_...py`, `models.py` | baixo |
| 2 | Schemas `ProjectRow`/`Create`/`Update` com 3 campos (Update com `Optional[T] = None`) | `schemas.py` | baixo |
| 3 | PUT em `/api/admin/projects/{id}` faz merge (`exclude_unset=True`) | `routers/admin.py` | baixo |
| 4 | Endpoint usa `require_admin_identity` (não só `require_full_admin_session`) | `routers/admin.py` | baixo |
| 5 | GET/POST/PUT expõem/aceitam os 3 campos | `routers/admin.py` | baixo |
| 6 | Helpers `is_forms_enabled_for_project` e `is_transport_enabled_for_project` | `services/project_catalog.py` | baixo |
| 7 | Testes backend — modelo, schema, endpoints (incluindo merge no PUT), helpers | `tests/` | médio |
| **— Commit E — backend pronto, frontend ainda não consome —** | | | |
| 8 | Gate `forms_enabled` em `submit_forms_event` (skip path com `reason=forms_disabled_for_project`) | `services/forms_submit.py` | médio |
| 9 | Testes: `submit_forms_event` com projeto desligado vira skip; com ligado mantém comportamento atual | `tests/services/test_forms_submit_*.py` | médio |
| 10 | Campo `transport_enabled` em `WebCheckHistoryResponse` populado pelo `build_web_check_history_state` | `schemas.py`, `routers/web_check.py` | baixo |
| 11 | PUT do projeto dispara `notify_web_check_data_changed("project_transport_flag")` quando `transport_enabled` muda | `routers/admin.py` | baixo |
| 12 | PUT do projeto grava `CheckEvent` de auditoria (`proj_forms_off` / `proj_trans_off`) na transição ON→OFF | `routers/admin.py` | baixo |
| 13 | Testes: auditoria criada na transição correta; SSE disparado | `tests/routers/test_admin_projects.py` | médio |
| **— Commit F — gates ativos, observabilidade pronta, frontend ainda não consome —** | | | |
| 14 | Tabela Projetos do admin2 ganha 3 colunas (HTML + `makeProjectRow`) | `static/admin2/index.html`, `static/admin2/app.js` | médio |
| 15 | CSS `.toggle-switch` adicionado (se não existir) | `static/admin2/styles.css` | baixo |
| 16 | Handler de `change` (toggles) com `confirm()` ao desligar | `static/admin2/app.js` | médio |
| 17 | Handler de `blur` (telefone) com PUT incremental | `static/admin2/app.js` | médio |
| 18 | `patchProjectFlag(id, payload)` com tratamento de erro + resync via `loadProjects()` | `static/admin2/app.js` | baixo |
| 19 | Smoke admin2: criar projeto, alternar toggles (cancelar + confirmar), editar telefone, observar `confirm()` | navegador | — |
| **— Commit G — admin2 controlável; usuário pode desligar Forms/Transporte —** | | | |
| 20 | Rename `transportTestingLabel` → `transportLabel` em 6 idiomas + valores traduzidos | `static/check/i18n-dictionaries.js` | baixo |
| 21 | Atualizar referência `t('registration.transportLabel')` em [app.js:1389](../sistema/app/static/check/app.js#L1389) | `static/check/app.js` | baixo |
| 22 | `applyTransportEnabledFlag(state)` chamada em todos os pontos que recebem novo state (login, swap de projeto, SSE refresh) | `static/check/app.js` | médio |
| 23 | Confirmar via grep que `.choice-grid.two-columns` já existe no CSS — não criar nada novo | `static/check/styles.css` | nenhum |
| 24 | Smoke Check Web: projeto com transporte ON vs OFF; ciclo via SSE (admin desliga → UI atualiza sem F5) | navegador | — |
| **— Commit H — Check Web responde aos toggles + label renomeada —** | | | |

**Estratégia de PRs:** 2 a 4 PRs, dependendo do apetite:

- **Opção compacta (2 PRs):**
  - PR 1: Commits E + F (todo o backend; sem efeito visível para usuário final ainda, mas API completa).
  - PR 2: Commits G + H (frontend admin2 + Check Web; efeito completo).

- **Opção granular (4 PRs):** um por commit. Mais isolável, mais churn.

**Recomendação:** Opção compacta. O backend (E+F) por si só é seguro — os gates ficam ativos mas como `True` por default, nada muda em produção até alguém clicar no toggle. Depois G+H libera o uso.

## 23. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Migration 0066 roda em prod com NULLs ⇒ NOT NULL violation | Muito baixa | Migration falha | `server_default=sa.true()` e `server_default=""` cobrem rows existentes. Testado em dev SQLite + Postgres em homologação. |
| Admin desliga Forms em projeto crítico por engano | Média | Atividades param de ir para o Forms — perda silenciosa | `confirm()` no UI ao desligar. Log estruturado `project_forms_disabled` toda vez que o PUT desativa (auditoria). |
| Admin desliga Transporte em projeto com assignments ativos | Baixa | Motoristas/passageiros confusos | Documentar como follow-up; não há trava técnica nesta entrega (escopo só esconde botão). |
| Telefone de emergência exposto na API de admin sem mascaramento | Baixa | Vazamento de PII de fornecedor | Endpoint já é protegido por `require_full_admin_session`. Sem mudança de superfície de exposição. |
| Race condition entre modal "Editar" (PUT inteiro) e toggle (PUT incremental) | Média | Toggle desfaz mudança que estava sendo editada | Endpoint do PUT usa `exclude_unset=True` → campos omitidos preservam valor atual. Modal envia tudo; toggle envia só o flag. Sem sobrescrita cruzada. Coberto no passo 3 da sequência §22. |
| Rename i18n quebra eventual referência externa (mobile, testes JS, scripts de homologação) | Baixa | Label sumindo em algum canal | Grep prévio por `transportTestingLabel` em todo o repo (incluindo `tests/`, `scripts/`, `deploy/`). Atualizar todas as referências antes do merge. |
| `WebCheckHistoryResponse` ganhar campo novo quebra cliente legado | Muito baixa | App mobile não atualizado quebra | Pydantic ignora campos extras na serialização e clientes JS modernos ignoram chaves desconhecidas. Risco residual mínimo. |
| `is_forms_enabled_for_project` ser caso-insensível mas projeto vir com case incorreto | Baixa | Gate sempre devolve `True` | Normalizar `projeto.strip().upper()` no helper. Já presente na proposta (§21.4). |

## 24. Validação manual

### 24.1 Pós-Commit E+F (backend)

1. Rodar migration 0066 em dev. Validar que projetos existentes ganham `forms_enabled=True`, `transport_enabled=True`, `emergency_phone=""`.
2. `GET /api/admin/projects` retorna os 3 campos.
3. `PUT /api/admin/projects/{id}` com `{ "forms_enabled": false }` persiste sem afetar outros campos.
4. Disparar uma atividade web com `projeto=P83` quando `forms_enabled(P83)=False`. Validar:
   - `forms_submissions` não recebe linha nova.
   - `check_events` recebe linha com `forms_skipped=true; reason=forms_disabled_for_project`.
   - Resposta da API ao cliente é 200 normal.
5. Disparar atividade em `P83` com `forms_enabled(P83)=True`. Comportamento atual preservado (linha em `forms_submissions`, worker processa).
6. `GET /api/web/check/state?chave=XXXX` retorna `transport_enabled` coerente com o projeto ativo.

### 24.2 Pós-Commit G (admin2)

7. Admin2 → aba Cadastro → tabela Projetos. Validar:
   - 3 colunas novas visíveis: Forms, Transporte, Emergência.
   - Toggles refletem estado do DB.
   - Input de emergência aceita até 32 caracteres.
   - Alternar toggle → `confirm()` dispara (só ao desligar) → PUT incremental → recarrega tabela.
   - Editar telefone + blur → PUT → status "Projeto atualizado.".
   - Mobile responsive: data-labels aparecem nas 3 colunas novas.

### 24.3 Pós-Commit H (Check Web)

8. Check Web logado com usuário do projeto `P83` (transporte ON): botão "Transporte" visível (label PT). Grid em 3 colunas.
9. Admin desliga transporte de `P83`. Refresh do Check Web (manual ou via SSE): botão some, grid colapsa para 2 colunas (Check-In + Check-Out de largura igual).
10. Trocar idioma para EN/ZH/MS/ID/TL: label fica "Transport" / "运输" / etc., **não** "In Testing" etc.
11. Religar transporte do `P83`: botão volta, grid volta a 3 colunas.

## 25. O que **não** está no escopo

- **Validação rigorosa do formato do telefone de emergência.** Aceita string livre até 32 caracteres por enquanto. Quando a feature de ligação real for desenhada, decide-se formato (E.164 etc.).
- **Lógica de ligar/notificar via telefone de emergência.** Apenas cadastro. Detalhamento futuro.
- **Toggle por usuário** (granularidade fina). Hoje o flag é por projeto. Se quiserem por usuário no futuro, mexe em `user_project_memberships` ou similar.
- **Histórico de quem ligou/desligou Forms/Transporte.** Logging no `CheckEvent`/`AdminAuditLog` seria útil mas é follow-up. Por ora, basta o log do PUT (já existente em qualquer endpoint admin).
- **Reativação automática de Forms quando o projeto voltar a ter XPaths cadastrados.** São conceitos ortogonais — `forms_enabled` é decisão administrativa, XPaths é capacidade técnica.
- **Mudança no admin v1.** Continua intacto. O admin v1 não verá as 3 colunas novas. Trade-off aceitável (v1 está em sunset).

## 26. Checklist de pronto para mergear

### Commit E (model + schema + endpoints)
- [ ] Migration 0066 criada, com upgrade e downgrade testados em SQLite e Postgres
- [ ] `Project` model com 3 campos novos (com `server_default`)
- [ ] `ProjectRow` com 3 campos
- [ ] `ProjectCreate` com 3 campos (opcionais com default)
- [ ] `ProjectUpdate` com 3 campos como `Optional[T] = None` para suportar PATCH-like merge
- [ ] Handler do PUT aplica `payload.model_dump(exclude_unset=True)` (merge, não substituição)
- [ ] Endpoint do PUT migrado para `require_admin_identity` (necessário para FK de auditoria)
- [ ] `GET /api/admin/projects` retorna os 3 campos
- [ ] `POST /api/admin/projects` aceita os 3 campos (opcionais)
- [ ] Helpers `is_forms_enabled_for_project` e `is_transport_enabled_for_project` em `project_catalog.py`
- [ ] Testes backend cobrindo CRUD com flags, incluindo PUT parcial (somente um campo)
- [ ] Todos os testes existentes passando

### Commit F (gates ativos + observabilidade)
- [ ] `submit_forms_event` consulta `forms_enabled` antes do `should_enqueue_forms_for_action`
- [ ] Projeto com `forms_enabled=False` produz skip com `reason=forms_disabled_for_project`
- [ ] Projeto com `forms_enabled=True` mantém comportamento atual (sem regressão)
- [ ] `WebCheckHistoryResponse` expõe `transport_enabled` populado do projeto ativo
- [ ] PUT em `/api/admin/projects/{id}` dispara `notify_web_check_data_changed("project_transport_flag")` apenas quando `transport_enabled` muda
- [ ] PUT grava `CheckEvent` `proj_forms_off` na transição `forms_enabled: True→False`
- [ ] PUT grava `CheckEvent` `proj_trans_off` na transição `transport_enabled: True→False`
- [ ] Ações ON→ON ou OFF→OFF NÃO geram log de auditoria duplicado
- [ ] Testes cobrindo: enqueue normal (ON), skip por flag (OFF), SSE disparado, log de auditoria criado nas transições corretas

### Commit G (admin2 UI)
- [ ] Cabeçalho da tabela Projetos com 9 colunas
- [ ] `makeProjectRow` renderiza os 3 controles novos
- [ ] Handlers de toggle disparam `confirm()` antes de desligar
- [ ] PUT incremental funciona; em erro, recarrega tabela para resync
- [ ] CSS `.toggle-switch` consistente com tema do admin2
- [ ] Mobile responsive (data-labels aparecem nas 3 novas)
- [ ] Smoke manual completo (criar projeto, alternar, editar, salvar)

### Commit H (Check Web)
- [ ] Chave i18n renomeada nos 6 dicionários: `transportTestingLabel` → `transportLabel`
- [ ] Valores atualizados em 6 idiomas (Transporte/Transport/运输/...)
- [ ] `app.js` referencia `t('registration.transportLabel')`
- [ ] `applyTransportEnabledFlag(state)` chamada em todo ponto que recebe novo state
- [ ] Botão some/aparece corretamente ao alternar o flag
- [ ] Grid colapsa de 3 → 2 colunas e volta sem layout shift
- [ ] Smoke manual em PT + 1 outro idioma

## 27. Rollback

### Rollback do Commit E

- Reverter código.
- Rodar `alembic downgrade -1` para remover as 3 colunas.
- Cuidado: se Commit F já estiver em prod e algum endpoint consulta as colunas, downgrade quebra. **Ordem segura de revert: H → G → F → E.**

### Rollback do Commit F

- Reverter código. As colunas permanecem no DB sem efeito.
- Comportamento volta ao atual (Forms sempre enfileira para todo projeto; Transporte sempre visível no Check Web).

### Rollback do Commit G

- Reverter código frontend admin2. Backend continua funcional; admins perdem a UI dos toggles, mas valores em DB persistem.
- **Manual workaround:** alterar via SQL direto (`UPDATE projects SET forms_enabled = false WHERE name = 'P83';`).

### Rollback do Commit H

- Reverter código Check Web. Label volta a "Em Teste" / "In Testing" etc. Botão volta a sempre visível.
- **Atenção:** se o `WebCheckHistoryResponse` ainda incluir `transport_enabled`, o frontend revertido só ignora — sem erro.

## 28. Memória — Parte III

> Convenções globais em [§A](#apêndice--convenções-transversais). Esta seção é só o que é exclusivo da Parte III.

- **Próxima migration Alembic:** 0066 (a 0065 é `drop_users_cargo_column`).
- **Código alvo:**
  - Backend: [models.py](../sistema/app/models.py), [schemas.py](../sistema/app/schemas.py), [routers/admin.py](../sistema/app/routers/admin.py), [services/forms_submit.py](../sistema/app/services/forms_submit.py), [services/project_catalog.py](../sistema/app/services/project_catalog.py), [routers/web_check.py](../sistema/app/routers/web_check.py).
  - Frontend admin2: [static/admin2/index.html](../sistema/app/static/admin2/index.html), [static/admin2/app.js](../sistema/app/static/admin2/app.js), [static/admin2/styles.css](../sistema/app/static/admin2/styles.css).
  - Frontend Check Web: [static/check/index.html](../sistema/app/static/check/index.html), [static/check/app.js](../sistema/app/static/check/app.js), [static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js), [static/check/styles.css](../sistema/app/static/check/styles.css).
- **Decisões consolidadas:**
  - Defaults `True/True/""` para preservar comportamento em produção.
  - Gate `forms_enabled` no enqueue (`submit_forms_event`), não no worker.
  - Gate `transport_enabled` exposto via `/api/web/check/state`.
  - Telefone de emergência: cadastro apenas. Sem validação de formato.
  - Rename i18n: `transportTestingLabel` → `transportLabel`.
  - 4 commits sugeridos (E, F, G, H), agrupados em 2 PRs (E+F backend, G+H frontend).
- **Pontos críticos da implementação (esquecer = bug):**
  - PUT de `/api/admin/projects/{id}` faz **merge** com `exclude_unset=True`; campos omitidos preservam valor.
  - PUT migra para `require_admin_identity` (FK de auditoria precisa do `AdminActorIdentity`).
  - PUT dispara `notify_web_check_data_changed("project_transport_flag")` na mudança de `transport_enabled` (Check Web atualiza em tempo real).
  - PUT grava `CheckEvent` `proj_forms_off` / `proj_trans_off` na transição ON→OFF (auditoria).
  - `confirm()` no admin2 só ao **desligar** (não ao ligar) — UX defensiva.
  - Ações de auditoria com nomes ≤ 16 chars (convenção CheckEvent.action).
- **Próximo passo:** Commit E (passos 1-7 da sequência §22).
