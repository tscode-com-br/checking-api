# Prompts de Implementação — Plano Checking

Este arquivo contém **8 prompts auto-contidos** para um agente de IA implementar o plano completo definido em [docs/temp001.md](temp001.md). Cada prompt corresponde a um commit isolado.

## Como usar este arquivo

1. Execute os prompts **em ordem** (Prompt 1 → Prompt 2 → ... → Prompt 8). A ordem segue §A.3 do plano (ordem global recomendada para minimizar interferência cruzada).
2. Cada prompt é auto-contido: contém pré-requisitos, arquivos a ler, mudanças exatas, testes, DoD e o ponteiro para o próximo prompt.
3. **Antes** de executar qualquer prompt, leia uma única vez:
   - [docs/temp001.md §A (Apêndice — convenções transversais)](temp001.md#apêndice--convenções-transversais) — comandos pre-flight, padrão de PR, glossário.
   - [CLAUDE.md](../CLAUDE.md) — convenções de código do projeto.
4. Se um prompt requer mudanças em testes existentes, o agente **deve** atualizar tanto a implementação quanto os testes no mesmo commit.
5. Não pular prompts. Se algum pre-flight falhar, interromper e diagnosticar antes de seguir.

## Sequência

| Fase | Prompt | Commit | O quê |
|---|---|---|---|
| 1 | [Prompt 1](#prompt-1--commit-c-núcleo-do-diff-render-no-admin2) | C | Admin2: remove animação stagger + diff render |
| 1 | [Prompt 2](#prompt-2--commit-d-mitigações-secundárias-do-admin2) | D | Admin2: `document.hidden`, debounce 600 ms, `fetchSilent` |
| 2 | [Prompt 3](#prompt-3--commit-e-backend-de-projetos-com-toggles) | E | Backend: migration 0066, schemas, endpoints, helpers |
| 2 | [Prompt 4](#prompt-4--commit-f-gates-de-forms-e-transporte-ativos) | F | Gates: `forms_enabled` no enqueue, `transport_enabled` no state, SSE, auditoria |
| 2 | [Prompt 5](#prompt-5--commit-g-admin2-ui-com-toggles-e-telefone) | G | Admin2 UI: 3 colunas novas com toggles e input de telefone |
| 2 | [Prompt 6](#prompt-6--commit-h-check-web-respeita-transport_enabled-e-renomeia-label) | H | Check Web: label `transportLabel`, esconder botão dinamicamente |
| 3 | [Prompt 7](#prompt-7--commit-a-redução-de-pausas-no-forms-worker) | A | Forms worker: pausas de 3/2/5 s → 1 s, configurável |
| 3 | [Prompt 8](#prompt-8--commit-b-concorrência-no-forms-worker) | B | Forms worker: thread pool com 3 consumidoras |

---

# FASE 1 — Parte II: Correção do piscar do Admin2

## Prompt 1 — Commit C: Núcleo do diff render no Admin2

### Contexto

O painel admin v2 (`sistema/app/static/admin2/`) tem as tabelas "Usuários em Check-in" e "Usuários em Check-Out" piscando continuamente em momentos de pico. A causa é uma combinação de duas coisas:

1. Um `MutationObserver` global registrado em **todos os `<tbody>`** da página que reaplica a classe `v2-row-enter` em todas as linhas sempre que linhas são adicionadas.
2. A classe dispara animação CSS de 0,22 s × até 30 linhas escalonadas em 14 ms = até **640 ms** de fade-in por re-render.

Como o re-render acontece a cada SSE event (debounce de 250 ms < 640 ms), os ciclos de animação se sobrepõem → piscar contínuo. O admin v1 (`sistema/app/static/admin/`) não tem esses elementos e não pisca.

Referência completa: [docs/temp001.md §10–§19](temp001.md#parte-ii--correção-do-piscar-do-admin2).

### Pré-requisitos

- Branch a partir de `main`, sem alterações pendentes.
- Você não precisa de nenhum commit anterior — este é o primeiro do plano.

### Arquivos a ler ANTES de modificar (para contexto)

1. [sistema/app/static/admin2/app.js:1-143](../sistema/app/static/admin2/app.js#L1-L143) — IIFE de animações (alvo principal).
2. [sistema/app/static/admin2/app.js:3698-3740](../sistema/app/static/admin2/app.js#L3698-L3740) — `applyPresenceTableState` e `renderPresenceTable` (alvo do diff render).
3. [sistema/app/static/admin2/app.js:4979-5002](../sistema/app/static/admin2/app.js#L4979-L5002) — `loadCheckin` e `loadCheckout` (chamadores de `renderPresenceTable`).
4. [sistema/app/static/admin2/app.js:2222-2242](../sistema/app/static/admin2/app.js#L2222-L2242) — `applyResponsiveLabels` (preserva data-labels nas linhas após render).
5. [sistema/app/static/admin2/styles.css:101-125](../sistema/app/static/admin2/styles.css#L101-L125) — animação `v2-row-enter`.
6. [sistema/app/static/admin/app.js:3539-3550](../sistema/app/static/admin/app.js#L3539-L3550) — referência: como o admin v1 (que não pisca) renderiza.

### Mudanças

#### Mudança 1 — Remover `MutationObserver` global e `staggerRows`

Em [sistema/app/static/admin2/app.js](../sistema/app/static/admin2/app.js), localizar o bloco que começa em `// Row stagger animation — fires whenever a tbody gets new rows` (linha ~88) e termina antes de `// Modal card entrance animation` (linha ~103). Remover **completamente** o trecho:

```js
// Row stagger animation — fires whenever a tbody gets new rows
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

**Manter** a classe `.v2-row-enter` e o `@keyframes v2RowEnter` em `styles.css` — viram código morto controlado, sem efeito (decisão consciente: minimiza diff CSS).

#### Mudança 2 — Implementar diff render em `renderPresenceTable`

Em [sistema/app/static/admin2/app.js:3729-3740](../sistema/app/static/admin2/app.js#L3729-L3740), substituir `renderPresenceTable` por uma versão que reaproveita `<tr>` existentes quando o HTML não mudou.

Adicionar um `WeakMap` no escopo do módulo (próximo de outras variáveis globais, ex.: linha ~200):

```js
const presenceRowHtmlCache = new WeakMap();
```

Substituir a função:

```js
function renderPresenceTable(bodyId, rows, options = {}) {
  const body = document.getElementById(bodyId);
  if (!body) return;

  if (!rows.length) {
    renderEmptyStateRow(bodyId, 8, options.emptyMessage || "Nenhum registro encontrado.");
    updateUserTitle(bodyId, 0, getPresenceTotalForTitle(bodyId));
    return;
  }

  const responsiveVariant = options.responsiveVariant || "default";

  // Indexar linhas existentes por chave (data-row-key)
  const existingByKey = new Map();
  Array.from(body.children).forEach((tr) => {
    const key = tr.dataset.rowKey;
    if (key) existingByKey.set(key, tr);
  });

  // Construir / atualizar / reordenar
  const usedKeys = new Set();
  rows.forEach((row, index) => {
    const key = String(row.chave || "").trim().toUpperCase();
    if (!key) return;
    usedKeys.add(key);

    let tr = existingByKey.get(key);
    if (!tr) {
      // Linha nova: criar
      tr = buildPresenceRow(row, options);
      tr.dataset.rowKey = key;
      tr.dataset.responsiveVariant = responsiveVariant;
    } else {
      // Linha existente: comparar outerHTML cacheado com o que seria renderizado agora
      const cached = presenceRowHtmlCache.get(tr);
      const candidate = buildPresenceRow(row, options);
      candidate.dataset.rowKey = key;
      candidate.dataset.responsiveVariant = responsiveVariant;
      if (cached !== candidate.outerHTML || tr.dataset.responsiveVariant !== responsiveVariant) {
        // Conteúdo ou variante mudou: substituir conteúdo + atributos
        tr.outerHTML = candidate.outerHTML;
        // Após outerHTML, o nó antigo morreu — refetch
        tr = body.querySelector(`tr[data-row-key="${CSS.escape(key)}"]`);
      }
    }

    // Garantir posição correta no DOM
    const currentAtIndex = body.children[index];
    if (currentAtIndex !== tr) {
      body.insertBefore(tr, currentAtIndex || null);
    }

    presenceRowHtmlCache.set(tr, tr.outerHTML);
  });

  // Remover linhas que não estão mais em rows
  Array.from(body.children).forEach((tr) => {
    const key = tr.dataset.rowKey;
    if (key && !usedKeys.has(key)) {
      presenceRowHtmlCache.delete(tr);
      tr.remove();
    }
  });

  applyResponsiveLabels(bodyId);
  updateUserTitle(bodyId, rows.length, getPresenceTotalForTitle(bodyId));
}
```

> **Decisões fixadas (não revisitar):**
> - `outerHTML` como chave de cache (captura `class`, `dataset`, atributos do `<tr>` — `innerHTML` perderia mudanças de classe condicional).
> - `WeakMap<HTMLTableRowElement, string>` em vez de `dataset.lastHtml` (evita poluir DOM, GC automático).
> - Chave de identidade = `row.chave` normalizado (`trim().toUpperCase()`).
> - `responsiveVariant` no `dataset` invalida cache quando muda mobile ↔ desktop.

#### Mudança 3 — Confirmar via grep que `staggerRows` não é mais referenciado

Após remover, rodar:

```bash
grep -rn "staggerRows\|v2-row-enter" sistema/app/static/admin2/
```

Esperado: apenas em `styles.css` (definição CSS morta, mas mantida).

### Testes a adicionar/atualizar

Como o projeto não tem runner de testes JS padronizado (verificar `tests/check_admin_presence_forms_layout.test.js` se existir), foco em **smoke manual** (descrito abaixo).

Se `tests/check_admin_presence_forms_layout.test.js` referenciar `v2-row-enter` ou `staggerRows`, atualizar para refletir a remoção:

```bash
grep -n "staggerRows\|v2-row-enter" tests/
```

### Testes existentes que NÃO podem quebrar

Backend não é tocado neste prompt. Testes Python devem passar inalterados:

```bash
pytest tests/ -x -q --ignore=tests/integration
```

### Pre-flight checks

```bash
# Confirmar que não restou referência a staggerRows
grep -rn "staggerRows" sistema/app/static/admin2/

# Confirmar que renderPresenceTable foi reescrita
grep -n "presenceRowHtmlCache\|data-row-key" sistema/app/static/admin2/app.js

# Suite Python (sem regressão backend)
pytest tests/ -x -q --ignore=tests/integration
```

### Validação manual

1. Subir o app: `python -m uvicorn sistema.app.main:app --reload`.
2. Abrir `http://localhost:8000/admin2`, logar com perfil 9.
3. Em ambiente com tráfego (ou simulando via repetidas chamadas a um endpoint que dispare SSE), observar tabela "Usuários em Check-in" por 60 s.
4. **Esperado:** zero piscar. Linhas estáticas. Quando dado real muda, só a linha afetada atualiza, sem fade-in.
5. Repetir para "Usuários em Check-Out".
6. Clicar em coluna para reordenar — linhas reorganizam visualmente, sem flicker.
7. Filtrar pela barra de filtros — linhas que saem somem; as que permanecem não reanimam.
8. Redimensionar janela para forçar mobile breakpoint — linhas re-renderizam corretamente com data-labels.

### DoD (Definition of Done)

- [ ] `MutationObserver` global e função `staggerRows` removidos
- [ ] `renderPresenceTable` reescrita com diff por chave
- [ ] `WeakMap presenceRowHtmlCache` definido no escopo do módulo
- [ ] `outerHTML` usado como chave de cache (não `innerHTML`, não `dataset`)
- [ ] `tr.dataset.rowKey` e `tr.dataset.responsiveVariant` setados em cada `<tr>`
- [ ] Grep confirma ausência de `staggerRows` no código
- [ ] Smoke manual em desktop e mobile: zero piscar em 60 s de observação
- [ ] Reordenação e filtros funcionam sem piscar
- [ ] Pre-flight checks passam
- [ ] Admin v1 (`/admin`) continua intacto (smoke rápido)

### Próximo passo

Quando todos os itens do DoD estiverem marcados e os pre-flight checks passarem, **prossiga para o [Prompt 2](#prompt-2--commit-d-mitigações-secundárias-do-admin2)** (Commit D — mitigações secundárias do Admin2).

---

## Prompt 2 — Commit D: Mitigações secundárias do Admin2

### Contexto

O Commit C resolveu o piscar principal. Agora aplicamos 3 mitigações que reduzem ainda mais o "ruído visual" e a pressão sobre o backend:

1. Pular re-render via SSE quando a aba/janela está escondida (`document.hidden`).
2. Subir `REALTIME_DEBOUNCE_MS` de 250 → 600 ms para agrupar mais eventos em pico.
3. Wrapper `fetchSilent` que pula a barra de progresso superior em refreshes automáticos do SSE.

Referência completa: [docs/temp001.md §12.4 / §12.5 / §12.6](temp001.md#parte-ii--correção-do-piscar-do-admin2).

### Pré-requisitos

- Commit C (Prompt 1) mergeado e em produção (ou validado em homologação).
- Branch a partir de `main` atualizada.

### Arquivos a ler ANTES de modificar

1. [sistema/app/static/admin2/app.js:8-43](../sistema/app/static/admin2/app.js#L8-L43) — interceptador de `window.fetch` que controla a barra de progresso.
2. [sistema/app/static/admin2/app.js:197-198](../sistema/app/static/admin2/app.js#L197-L198) — constantes `AUTO_REFRESH_MS` e `REALTIME_DEBOUNCE_MS`.
3. [sistema/app/static/admin2/app.js:5717-5752](../sistema/app/static/admin2/app.js#L5717-L5752) — `requestRefreshAllTables` e `startRealtimeUpdates`.
4. [sistema/app/static/admin2/app.js:5676-5698](../sistema/app/static/admin2/app.js#L5676-L5698) — `refreshAutomaticTables` (chamada pelo SSE; precisa usar `fetchSilent`).
5. [sistema/app/static/admin2/app.js:2816-2845](../sistema/app/static/admin2/app.js#L2816-L2845) — `fetchJson` e `fetchJsonWithMeta` (alvos do wrapping).

### Mudanças

#### Mudança 1 — Guarda `document.hidden` no SSE

Em [admin2/app.js:5734-5747](../sistema/app/static/admin2/app.js#L5734-L5747), localizar `eventStream.onmessage` e adicionar a guarda no início:

```js
eventStream.onmessage = (event) => {
  realtimeConnected = true;
  updateOperationalChrome();
  if (document.hidden) return;  // NOVA GUARDA — sem refresh quando aba escondida
  try {
    const data = JSON.parse(event.data);
    if (data.reason && data.reason.startsWith("accident_")) {
      scheduleAccidentRefresh();
    } else {
      requestRefreshAllTables();
    }
  } catch {
    requestRefreshAllTables();
  }
};
```

> O `realtimeConnected = true` permanece **fora** da guarda — o chrome da UI mostra "conectado" mesmo com aba escondida. O catch-up ao voltar é coberto por `startAutoRefresh` (intervalo de 5 s).

#### Mudança 2 — Debounce 250 → 600 ms

Em [admin2/app.js:198](../sistema/app/static/admin2/app.js#L198), trocar:

```js
const REALTIME_DEBOUNCE_MS = 250;
```

por:

```js
const REALTIME_DEBOUNCE_MS = 600;
```

#### Mudança 3 — Wrapper `fetchSilent` para refreshes automáticos

Em [admin2/app.js:8-43](../sistema/app/static/admin2/app.js#L8-L43), modificar o interceptador de `window.fetch` para respeitar uma flag `__silent`:

```js
const _origFetch = window.fetch;
window.fetch = function(...args) {
  const url = String(typeof args[0] === "string" ? args[0] : args[0]?.url || "");
  const init = args[1];
  const isSilent = init && init.__silent === true;
  if (url.includes("/api/") && !isSilent) {
    _pending++;
    if (_pending === 1) progressStart();
    return _origFetch.apply(this, args).finally(() => {
      _pending = Math.max(0, _pending - 1);
      if (_pending === 0) progressDone();
    });
  }
  return _origFetch.apply(this, args);
};
```

Adicionar funções helper próximas ao `fetchJson` ([admin2/app.js:2816-2845](../sistema/app/static/admin2/app.js#L2816-L2845)):

```js
async function fetchJsonSilent(url, options = {}) {
  return fetchJson(url, { ...options, __silent: true });
}

async function fetchJsonWithMetaSilent(url, options = {}) {
  return fetchJsonWithMeta(url, { ...options, __silent: true });
}
```

E em [admin2/app.js:5676-5698](../sistema/app/static/admin2/app.js#L5676-L5698), `refreshAutomaticTables`, **trocar** chamadas para versões silenciosas. Especificamente, em [`loadCheckin`](../sistema/app/static/admin2/app.js#L4979-L4988) e [`loadCheckout`](../sistema/app/static/admin2/app.js#L4990-L5002), trocar `fetchJsonWithMeta` por `fetchJsonWithMetaSilent` **apenas quando chamado por `refreshAutomaticTables`** — para isso, é mais simples passar uma flag para `loadCheckin`/`loadCheckout`:

```js
async function loadCheckin({ silent = false } = {}) {
  const fetcher = silent ? fetchJsonWithMetaSilent : fetchJsonWithMeta;
  const { data, headers } = await fetcher("/api/admin/checkin");
  // ... resto idêntico
}

async function loadCheckout({ silent = false } = {}) {
  const fetcher = silent ? fetchJsonWithMetaSilent : fetchJsonWithMeta;
  const { data, headers } = await fetcher("/api/admin/checkout");
  // ... resto idêntico
}
```

E em `refreshAutomaticTables`:

```js
jobs.push(loadCheckin({ silent: true }));
jobs.push(loadCheckout({ silent: true }));
if (databaseEventsLoaded && isAdminTabAllowed("banco-dados")) {
  jobs.push(loadDatabaseEvents({ silent: true }));
}
// ...
```

Aplicar o mesmo padrão a `loadDatabaseEvents`, `loadPending`, `loadLocations` se forem chamados de `refreshAutomaticTables`. Verificar via grep:

```bash
grep -n "refreshAutomaticTables\|loadCheckin\|loadCheckout\|loadDatabaseEvents\|loadPending\|loadLocations" sistema/app/static/admin2/app.js
```

### Testes a adicionar/atualizar

Sem testes JS automatizados — validação 100% manual.

### Testes existentes que NÃO podem quebrar

```bash
pytest tests/ -x -q --ignore=tests/integration
```

### Pre-flight checks

```bash
# Confirmar guarda document.hidden
grep -n "if (document.hidden) return" sistema/app/static/admin2/app.js

# Confirmar debounce subiu
grep -n "REALTIME_DEBOUNCE_MS = 600" sistema/app/static/admin2/app.js

# Confirmar fetchJsonSilent definido
grep -n "fetchJsonSilent\|fetchJsonWithMetaSilent\|__silent" sistema/app/static/admin2/app.js

# Suite Python
pytest tests/ -x -q --ignore=tests/integration
```

### Validação manual

1. Abrir admin2 logado.
2. Em DevTools → Network, filtrar por `checkin` ou `checkout`. **Minimizar a janela** por 2 minutos. Voltar.
3. **Esperado:** zero requests durante o período minimizado. Ao voltar, próximo refresh acontece em até 5 s (`AUTO_REFRESH_MS`).
4. Com a aba aberta, observar a barra de progresso superior por 60 s sem interagir.
5. **Esperado:** a barra não aparece durante refreshes automáticos do SSE.
6. Clicar em um botão de ação (salvar projeto, atualizar usuários, etc.) — a barra **deve** aparecer.
7. Em DevTools → Network, contar requests por minuto a `/api/admin/checkin` em pico. Comparar com baseline pré-Commit D. **Esperado:** queda significativa (~60%) sob mesma carga.

### DoD

- [ ] Guarda `document.hidden` no handler SSE
- [ ] `REALTIME_DEBOUNCE_MS = 600`
- [ ] Interceptador de `window.fetch` respeita `init.__silent`
- [ ] `fetchJsonSilent` / `fetchJsonWithMetaSilent` definidos
- [ ] `loadCheckin`, `loadCheckout` (e correlatos) aceitam `{ silent: true }`
- [ ] `refreshAutomaticTables` chama as versões silenciosas
- [ ] Smoke manual: aba escondida não dispara fetches
- [ ] Smoke manual: barra de progresso só aparece em ações do usuário
- [ ] Pre-flight checks passam
- [ ] Sem regressão no Commit C (smoke rápido: zero piscar)

### Próximo passo

Quando todos os itens do DoD estiverem marcados, **prossiga para o [Prompt 3](#prompt-3--commit-e-backend-de-projetos-com-toggles)** (Commit E — backend de Projetos com toggles).

---

# FASE 2 — Parte III: Colunas Forms, Transporte e Emergência em Projetos

## Prompt 3 — Commit E: Backend de Projetos com toggles

### Contexto

A tabela `projects` ganha 3 colunas operacionais: `forms_enabled` (bool, default `True`), `transport_enabled` (bool, default `True`), `emergency_phone` (string até 32 chars, default `""`). Modelo, schemas Pydantic, endpoints admin e helpers de consulta são preparados — **sem efeito de comportamento ainda** (gates ativos vêm no Commit F).

Decisões fixadas:
- Defaults `True/True/""` preservam comportamento atual em produção.
- PUT em `/api/admin/projects/{id}` faz **merge** com `exclude_unset=True`, não substituição.
- Endpoint do PUT migra para `require_admin_identity` (necessário para FK de auditoria no Commit F).

Referência completa: [docs/temp001.md §20–§28](temp001.md#parte-iii--colunas-forms-transporte-e-emergência-na-tabela-de-projetos).

### Pré-requisitos

- Commits C + D mergeados (Parte II completa).
- Branch a partir de `main` atualizada.
- Próxima migration Alembic disponível: **0066** (verificar com `ls alembic/versions/ | tail -3`).

### Arquivos a ler ANTES de modificar

1. [sistema/app/models.py:10-20](../sistema/app/models.py#L10-L20) — `class Project`.
2. [sistema/app/schemas.py:1083-1180](../sistema/app/schemas.py#L1083-L1180) — `ProjectRow`, `ProjectCreate`, `ProjectUpdate`.
3. [sistema/app/routers/admin.py](../sistema/app/routers/admin.py) — grep por `/api/admin/projects` para localizar os handlers.
4. [sistema/app/services/project_catalog.py](../sistema/app/services/project_catalog.py) — onde adicionar helpers.
5. [sistema/app/services/admin_auth.py](../sistema/app/services/admin_auth.py) — para confirmar a dependência `require_admin_identity` (e `AdminActorIdentity`).
6. [alembic/versions/0065_drop_users_cargo_column.py](../alembic/versions/0065_drop_users_cargo_column.py) — referência de estilo da migration anterior.
7. [CLAUDE.md §Identidade de admin](../CLAUDE.md) — entender por que migrar para `require_admin_identity`.

### Mudanças

#### Mudança 1 — Model

Em [sistema/app/models.py](../sistema/app/models.py), `class Project` (linha 10), adicionar:

```python
import sqlalchemy as sa  # se ainda não importado
from sqlalchemy import Boolean  # se ainda não importado

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("name", name="uq_projects_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    country_name: Mapped[str] = mapped_column(String(80), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    zip_code: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    # NOVOS CAMPOS
    forms_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa.true())
    transport_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa.true())
    emergency_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
```

#### Mudança 2 — Migration 0066

Criar `alembic/versions/0066_add_project_forms_transport_emergency_columns.py`:

```python
"""add forms_enabled, transport_enabled, emergency_phone to projects

Revision ID: 0066
Revises: 0065
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("forms_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "projects",
        sa.Column("transport_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "projects",
        sa.Column("emergency_phone", sa.String(length=32), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("projects", "emergency_phone")
    op.drop_column("projects", "transport_enabled")
    op.drop_column("projects", "forms_enabled")
```

> Verificar com `head -20 alembic/versions/0065_drop_users_cargo_column.py` o formato exato da revision id usada no projeto (`"0065"` ou outro). Ajustar.

#### Mudança 3 — Schemas Pydantic

Em [sistema/app/schemas.py](../sistema/app/schemas.py), localizar `ProjectRow`, `ProjectCreate`, `ProjectUpdate` (linhas ~1083-1180).

**`ProjectRow`:**

```python
class ProjectRow(BaseModel):
    id: int
    name: str
    country_code: str
    country_name: str
    timezone_name: str
    timezone_label: str
    address: str
    zip_code: str
    forms_enabled: bool          # NOVO
    transport_enabled: bool      # NOVO
    emergency_phone: str         # NOVO
```

**`ProjectCreate`:**

```python
class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    country_name: str | None = Field(default=None, min_length=2, max_length=80)
    timezone_name: str | None = Field(default=None, min_length=1, max_length=64)
    address: str = Field(default="", max_length=255)
    zip_code: str = Field(default="", max_length=32)
    forms_enabled: bool = True                                      # NOVO
    transport_enabled: bool = True                                  # NOVO
    emergency_phone: str = Field(default="", max_length=32)         # NOVO

    # ... validators existentes (manter) ...

    @field_validator("emergency_phone", mode="before")
    @classmethod
    def validate_emergency_phone(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()[:32]
```

**`ProjectUpdate`** (mudança crítica — campos viram `Optional[T] = None` para suportar PATCH-like merge):

```python
class ProjectUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    country_name: str | None = Field(default=None, min_length=2, max_length=80)
    timezone_name: str | None = Field(default=None, min_length=1, max_length=64)
    address: str = Field(default="", max_length=255)
    zip_code: str = Field(default="", max_length=32)
    forms_enabled: bool | None = None                                # NOVO — opcional para merge
    transport_enabled: bool | None = None                            # NOVO — opcional para merge
    emergency_phone: str | None = Field(default=None, max_length=32) # NOVO — opcional para merge

    # ... validators existentes (manter) ...

    @field_validator("emergency_phone", mode="before")
    @classmethod
    def validate_emergency_phone(cls, value: object) -> str | None:
        if value is None:
            return None  # None significa "não tocar"
        return str(value).strip()[:32]
```

#### Mudança 4 — Helpers em `project_catalog.py`

Em [sistema/app/services/project_catalog.py](../sistema/app/services/project_catalog.py), adicionar:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Project


def is_forms_enabled_for_project(db: Session, *, projeto: str | None) -> bool:
    normalized = (projeto or "").strip().upper()
    if not normalized:
        return True
    row = db.execute(
        select(Project.forms_enabled).where(Project.name == normalized)
    ).scalar_one_or_none()
    return bool(row) if row is not None else True


def is_transport_enabled_for_project(db: Session, *, projeto: str | None) -> bool:
    normalized = (projeto or "").strip().upper()
    if not normalized:
        return True
    row = db.execute(
        select(Project.transport_enabled).where(Project.name == normalized)
    ).scalar_one_or_none()
    return bool(row) if row is not None else True
```

> Semântica: projeto vazio ou desconhecido = "não bloqueia" (retorna `True`). Defesa contra dados ruins.

#### Mudança 5 — Endpoints admin (GET / POST / PUT)

Em [sistema/app/routers/admin.py](../sistema/app/routers/admin.py), localizar os handlers de `/api/admin/projects`. Mudanças:

1. **GET:** o response model `ProjectRow` agora inclui os 3 campos novos automaticamente (Pydantic serializa). Conferir que a função de transformação row→`ProjectRow` (provavelmente `_project_row(project: Project) -> ProjectRow`) inclui:

```python
return ProjectRow(
    id=project.id,
    name=project.name,
    # ... campos existentes ...
    forms_enabled=project.forms_enabled,
    transport_enabled=project.transport_enabled,
    emergency_phone=project.emergency_phone,
)
```

2. **POST:** o handler aceita `ProjectCreate` que já tem os campos novos com default. Persistir:

```python
project = Project(
    name=payload.name,
    # ... campos existentes ...
    forms_enabled=payload.forms_enabled,
    transport_enabled=payload.transport_enabled,
    emergency_phone=payload.emergency_phone,
)
```

3. **PUT — mudança crítica:** trocar dependência para `require_admin_identity` e aplicar merge:

```python
@router.put("/projects/{project_id}", response_model=AdminProjectActionResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    identity: AdminActorIdentity = Depends(require_admin_identity),  # MUDANÇA
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado.")

    # MERGE — só campos enviados pelo cliente
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is None and key in {"forms_enabled", "transport_enabled", "emergency_phone"}:
            continue  # None nesses campos = "não tocar"
        setattr(project, key, value)

    db.commit()
    return AdminProjectActionResponse(ok=True, message="Projeto atualizado.")
```

> Manter o response model compatível com o que o frontend já consome. Se houver lógica adicional (validação de unicidade do nome, etc.), preservar.

### Testes a adicionar

Criar/atualizar `tests/routers/test_admin_projects.py`:

```python
def test_get_projects_returns_new_fields(client, admin_session):
    response = client.get("/api/admin/projects", cookies=admin_session)
    assert response.status_code == 200
    for project in response.json():
        assert "forms_enabled" in project
        assert "transport_enabled" in project
        assert "emergency_phone" in project


def test_post_project_with_defaults(client, admin_session):
    response = client.post(
        "/api/admin/projects",
        cookies=admin_session,
        json={"name": "P_TEST_NEW", "country_code": "BR"},
    )
    assert response.status_code == 200
    list_response = client.get("/api/admin/projects", cookies=admin_session).json()
    new_project = next(p for p in list_response if p["name"] == "P_TEST_NEW")
    assert new_project["forms_enabled"] is True
    assert new_project["transport_enabled"] is True
    assert new_project["emergency_phone"] == ""


def test_put_project_partial_update_preserves_other_fields(client, admin_session, sample_project):
    # PUT com só forms_enabled → outros campos devem ser preservados
    original_address = sample_project.address
    response = client.put(
        f"/api/admin/projects/{sample_project.id}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    assert response.status_code == 200
    refreshed = client.get("/api/admin/projects", cookies=admin_session).json()
    project = next(p for p in refreshed if p["id"] == sample_project.id)
    assert project["forms_enabled"] is False
    assert project["transport_enabled"] is True  # não tocado
    assert project["address"] == original_address  # não tocado
```

Criar `tests/services/test_project_catalog_flags.py`:

```python
def test_is_forms_enabled_for_known_project(db_session, sample_project):
    sample_project.forms_enabled = False
    db_session.commit()
    assert is_forms_enabled_for_project(db_session, projeto=sample_project.name) is False


def test_is_forms_enabled_for_unknown_project_defaults_true(db_session):
    assert is_forms_enabled_for_project(db_session, projeto="DOES_NOT_EXIST") is True


def test_is_forms_enabled_is_case_insensitive(db_session, sample_project):
    sample_project.forms_enabled = False
    db_session.commit()
    assert is_forms_enabled_for_project(db_session, projeto=sample_project.name.lower()) is False


def test_is_transport_enabled_mirrors_forms_logic(db_session, sample_project):
    sample_project.transport_enabled = False
    db_session.commit()
    assert is_transport_enabled_for_project(db_session, projeto=sample_project.name) is False
```

### Testes existentes que NÃO podem quebrar

- Qualquer teste que crie `Project(...)` precisa ainda funcionar — defaults garantem isso.
- Qualquer teste que chame `GET /api/admin/projects` continua passando (apenas ganha campos extras na resposta).

```bash
pytest tests/ -x -q --ignore=tests/integration
```

### Pre-flight checks

```bash
# Migration aplica e reverte limpamente
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head

# Suite completa
pytest tests/ -x -q --ignore=tests/integration

# Especificamente os arquivos tocados
pytest tests/routers/test_admin_projects.py tests/services/test_project_catalog_flags.py -x -v
```

### Validação manual

1. Rodar migration: `python -m alembic upgrade head`.
2. Validar no DB: `sqlite3 checking.db "SELECT name, forms_enabled, transport_enabled, emergency_phone FROM projects;"` → projetos existentes têm `forms_enabled=1, transport_enabled=1, emergency_phone=''`.
3. Subir app: `python -m uvicorn sistema.app.main:app --reload`.
4. `curl http://localhost:8000/api/admin/projects` (com cookie de sessão admin) — verificar que JSON inclui os 3 campos.
5. `curl -X PUT http://localhost:8000/api/admin/projects/{id} -d '{"forms_enabled": false}'` — verificar que retorna 200 e os outros campos do projeto **não** foram alterados.

### DoD

- [ ] Model `Project` com 3 campos novos (com `server_default`)
- [ ] Migration 0066 criada; `upgrade` e `downgrade` testados em SQLite local
- [ ] `ProjectRow` com 3 campos
- [ ] `ProjectCreate` com 3 campos (opcionais com default)
- [ ] `ProjectUpdate` com 3 campos como `Optional[T] = None`
- [ ] Handler do PUT aplica `model_dump(exclude_unset=True)` (merge)
- [ ] Handler do PUT usa `Depends(require_admin_identity)` (não mais `require_full_admin_session`)
- [ ] `GET /api/admin/projects` retorna os 3 campos
- [ ] `POST /api/admin/projects` aceita os 3 campos (opcionais)
- [ ] Helpers `is_forms_enabled_for_project` e `is_transport_enabled_for_project` em `project_catalog.py`
- [ ] Testes novos em `test_admin_projects.py` e `test_project_catalog_flags.py` passando
- [ ] Pre-flight checks (incluindo migration round-trip) passam
- [ ] Smoke manual com curl OK

### Próximo passo

Quando todos os itens do DoD estiverem marcados, **prossiga para o [Prompt 4](#prompt-4--commit-f-gates-de-forms-e-transporte-ativos)** (Commit F — gates ativos + observabilidade).

---

## Prompt 4 — Commit F: Gates de Forms e Transporte ativos

### Contexto

Com a infraestrutura do Commit E em produção, agora **ativamos os gates**:

1. `submit_forms_event` consulta `forms_enabled` antes de enfileirar — se OFF, segue skip path com `reason=forms_disabled_for_project`.
2. `WebCheckHistoryResponse` expõe `transport_enabled` lido do projeto ativo do usuário.
3. PUT em `/api/admin/projects/{id}` dispara `notify_web_check_data_changed("project_transport_flag")` quando `transport_enabled` muda.
4. PUT grava `CheckEvent` de auditoria (`proj_forms_off` / `proj_trans_off`) na transição `True → False`.

Como os defaults dos toggles são `True`, **nada muda em produção** até alguém clicar para desligar.

Referência completa: [docs/temp001.md §21.3 / §21.4 / §21.5](temp001.md#parte-iii--colunas-forms-transporte-e-emergência-na-tabela-de-projetos).

### Pré-requisitos

- Commit E (Prompt 3) mergeado e migration 0066 aplicada em produção/homologação.
- Branch a partir de `main` atualizada.

### Arquivos a ler ANTES de modificar

1. [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py) — `submit_forms_event` (alvo do gate).
2. [sistema/app/services/user_sync.py:104-117](../sistema/app/services/user_sync.py#L104-L117) — `should_enqueue_forms_for_action` (vizinho do novo gate).
3. [sistema/app/services/forms_queue.py:463-506](../sistema/app/services/forms_queue.py#L463-L506) — `record_forms_submission_skip` (caminho de skip que reaproveitamos).
4. [sistema/app/routers/web_check.py:737-744](../sistema/app/routers/web_check.py#L737-L744) — `get_web_check_state`.
5. [sistema/app/schemas.py](../sistema/app/schemas.py) — `WebCheckHistoryResponse` (grep).
6. [sistema/app/services/admin_updates.py:290-299](../sistema/app/services/admin_updates.py#L290-L299) — `notify_web_check_data_changed`.
7. [sistema/app/services/event_logger.py](../sistema/app/services/event_logger.py) — `log_event` (para auditoria).
8. [sistema/app/routers/admin.py](../sistema/app/routers/admin.py) — handler PUT de projeto (atualizado no Commit E).

### Mudanças

#### Mudança 1 — Gate `forms_enabled` em `submit_forms_event`

Em [sistema/app/services/forms_submit.py](../sistema/app/services/forms_submit.py), no início da função `submit_forms_event` (após resolver `chave`, `projeto`, etc.), adicionar a checagem:

```python
from .project_catalog import is_forms_enabled_for_project  # NOVO IMPORT

def submit_forms_event(
    db: Session,
    *,
    chave: str,
    projeto: str,
    action: str,
    informe: str,
    local: str | None,
    event_time: datetime,
    client_event_id: str,
    ensure_user: EnsureUserCallback,
    channel: FormsSubmitChannel,
) -> MobileSubmitResponse:
    ontime = informe == "normal"
    resolved_local = local or channel.default_local

    # ... checagem de duplicidade (existente, NÃO MUDAR) ...

    user, _created = ensure_user(db, chave=chave, projeto=projeto)
    project_timezone_name = resolve_project_timezone_name(db, projeto)
    normalized_event_time = normalize_event_time(event_time, timezone_name=project_timezone_name)
    ensure_current_user_state_event(db, user=user, skip_if_provider_backed=True)
    latest_activity = resolve_latest_internal_user_activity(db, user=user)

    # GATE — verificar se Forms está habilitado para o projeto
    forms_enabled = is_forms_enabled_for_project(db, projeto=user.projeto)

    skip_reason = get_forms_skip_reason(
        latest_activity=latest_activity,
        action=action,
        event_time=normalized_event_time,
        timezone_name=project_timezone_name,
    )
    should_queue_forms = should_enqueue_forms_for_action(
        latest_activity=latest_activity,
        action=action,
        event_time=normalized_event_time,
        timezone_name=project_timezone_name,
    )

    # Sobrescrever decisão se gate desligado
    if not forms_enabled:
        should_queue_forms = False
        skip_reason = "forms_disabled_for_project"

    # ... resto da função (apply_user_state, persistência, etc.) — preservado ...
```

> **Importante:** o `skip_reason` será incluído no `details` do `CheckEvent` (já é o comportamento existente). Verificar que o caminho de skip já registra `reason=` no campo `details`.

#### Mudança 2 — `transport_enabled` em `WebCheckHistoryResponse`

Em [sistema/app/schemas.py](../sistema/app/schemas.py), localizar `class WebCheckHistoryResponse` (grep). Adicionar campo:

```python
class WebCheckHistoryResponse(BaseModel):
    # ... campos existentes ...
    transport_enabled: bool = True  # NOVO — controla visibilidade do botão no Check Web
```

Em [sistema/app/routers/web_check.py](../sistema/app/routers/web_check.py), localizar `build_web_check_history_state` (grep) e adicionar:

```python
from ..services.project_catalog import is_transport_enabled_for_project  # NOVO IMPORT

def build_web_check_history_state(db: Session, *, chave: str) -> WebCheckHistoryResponse:
    # ... lógica existente que resolve user, history, etc. ...

    transport_enabled = is_transport_enabled_for_project(db, projeto=user.projeto)

    return WebCheckHistoryResponse(
        # ... campos existentes ...
        transport_enabled=transport_enabled,
    )
```

#### Mudança 3 — PUT do projeto dispara SSE quando `transport_enabled` muda

Em [sistema/app/routers/admin.py](../sistema/app/routers/admin.py), no handler `update_project` (modificado no Commit E), capturar o valor anterior antes do merge e disparar SSE se relevante:

```python
from ..services.admin_updates import notify_web_check_data_changed  # se ainda não importado

@router.put("/projects/{project_id}", response_model=AdminProjectActionResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    identity: AdminActorIdentity = Depends(require_admin_identity),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado.")

    # Capturar valores anteriores ANTES do merge (para auditoria + SSE)
    previous_forms_enabled = project.forms_enabled
    previous_transport_enabled = project.transport_enabled

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is None and key in {"forms_enabled", "transport_enabled", "emergency_phone"}:
            continue
        setattr(project, key, value)

    # Auditoria — transições ON → OFF
    if previous_forms_enabled and not project.forms_enabled:
        log_event(
            db,
            source="admin",
            action="proj_forms_off",  # ≤ 16 chars
            status="warning",
            message=f"Forms desativado para projeto {project.name}",
            project=project.name,
            details=f"actor_admin_user_id={identity.admin_user.id}",
        )

    if previous_transport_enabled and not project.transport_enabled:
        log_event(
            db,
            source="admin",
            action="proj_trans_off",  # ≤ 16 chars
            status="warning",
            message=f"Transporte desativado para projeto {project.name}",
            project=project.name,
            details=f"actor_admin_user_id={identity.admin_user.id}",
        )

    db.commit()

    # Notificação SSE — apenas se transport_enabled mudou
    if previous_transport_enabled != project.transport_enabled:
        notify_web_check_data_changed("project_transport_flag")

    return AdminProjectActionResponse(ok=True, message="Projeto atualizado.")
```

### Testes a adicionar

Em `tests/services/test_forms_submit_resilience.py` (ou novo `tests/services/test_forms_submit_gates.py`):

```python
def test_submit_forms_event_skips_when_project_forms_disabled(db_session, mock_ensure_user, sample_project):
    sample_project.forms_enabled = False
    db_session.commit()

    response = submit_forms_event(
        db_session,
        chave="WB12",
        projeto=sample_project.name,
        action="checkin",
        informe="normal",
        local="Escritório",
        event_time=now_sgt(),
        client_event_id="req-disabled-1",
        ensure_user=mock_ensure_user,
        channel=test_channel(),
    )

    assert response.ok is True
    assert response.queued_forms is False
    # Validar que CheckEvent foi gravado com reason
    events = db_session.execute(select(CheckEvent).where(CheckEvent.idempotency_key.like("%req-disabled-1%"))).scalars().all()
    assert len(events) == 1
    assert "forms_disabled_for_project" in (events[0].details or "")
    # Validar que NÃO há FormsSubmission para este request
    submissions = db_session.execute(select(FormsSubmission).where(FormsSubmission.request_id == "req-disabled-1")).scalars().all()
    assert len(submissions) == 1  # uma linha de skip (status='skipped'), não 'pending'
    assert submissions[0].status == "skipped"


def test_submit_forms_event_enqueues_when_project_forms_enabled(...):
    # mesma estrutura, mas com forms_enabled=True (default) e validar status='pending'
    ...
```

Em `tests/routers/test_admin_projects.py`:

```python
def test_put_project_logs_audit_event_on_forms_disable(client, admin_session, sample_project, db_session):
    response = client.put(
        f"/api/admin/projects/{sample_project.id}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    assert response.status_code == 200
    audit = db_session.execute(
        select(CheckEvent).where(CheckEvent.action == "proj_forms_off")
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.project == sample_project.name


def test_put_project_does_not_duplicate_audit_when_off_to_off(client, admin_session, sample_project, db_session):
    sample_project.forms_enabled = False
    db_session.commit()
    response = client.put(
        f"/api/admin/projects/{sample_project.id}",
        cookies=admin_session,
        json={"forms_enabled": False},
    )
    assert response.status_code == 200
    audits = db_session.execute(
        select(CheckEvent).where(CheckEvent.action == "proj_forms_off")
    ).scalars().all()
    assert len(audits) == 0  # já estava off → sem log


def test_put_project_notifies_web_check_when_transport_changes(client, admin_session, sample_project, monkeypatch):
    notifications = []
    monkeypatch.setattr(
        "sistema.app.routers.admin.notify_web_check_data_changed",
        lambda reason="refresh", **kwargs: notifications.append(reason),
    )
    response = client.put(
        f"/api/admin/projects/{sample_project.id}",
        cookies=admin_session,
        json={"transport_enabled": False},
    )
    assert response.status_code == 200
    assert "project_transport_flag" in notifications
```

Em `tests/routers/test_web_check_state.py`:

```python
def test_web_check_state_includes_transport_enabled_true_by_default(client, web_user_session, sample_project):
    response = client.get(f"/api/web/check/state?chave={sample_project.users[0].chave}", cookies=web_user_session)
    assert response.json()["transport_enabled"] is True


def test_web_check_state_reflects_disabled_transport(client, web_user_session, sample_project, db_session):
    sample_project.transport_enabled = False
    db_session.commit()
    response = client.get(f"/api/web/check/state?chave={sample_project.users[0].chave}", cookies=web_user_session)
    assert response.json()["transport_enabled"] is False
```

### Testes existentes que NÃO podem quebrar

- Testes em `tests/test_api_flow.py` que envolvem `/api/web/check`, `/api/mobile/events/forms-submit` — devem continuar passando pois `forms_enabled=True` (default) preserva o comportamento.
- Testes em `tests/services/test_forms_submit_*` — idem.

```bash
pytest tests/ -x -q --ignore=tests/integration
```

### Pre-flight checks

```bash
# Suite completa
pytest tests/ -x -q --ignore=tests/integration

# Testes específicos
pytest tests/services/test_forms_submit_gates.py tests/routers/test_admin_projects.py tests/routers/test_web_check_state.py -x -v

# Confirmar que o gate está no lugar
grep -n "is_forms_enabled_for_project\|forms_disabled_for_project" sistema/app/services/forms_submit.py
grep -n "is_transport_enabled_for_project" sistema/app/routers/web_check.py
grep -n "proj_forms_off\|proj_trans_off\|project_transport_flag" sistema/app/routers/admin.py
```

### Validação manual

1. Subir app: `python -m uvicorn sistema.app.main:app --reload`.
2. Desligar Forms para um projeto: `curl -X PUT http://localhost:8000/api/admin/projects/{id} -d '{"forms_enabled": false}'` (com cookie admin).
3. Disparar atividade web nesse projeto. Validar:
   - `forms_submissions` recebe linha com `status='skipped'` (não `pending`).
   - `check_events` tem entrada com `reason=forms_disabled_for_project` no campo `details`.
   - Resposta da API ao cliente é 200 normal.
4. `curl http://localhost:8000/api/web/check/state?chave=XXXX` — `transport_enabled` reflete o estado do projeto ativo.
5. Verificar no DB: `SELECT * FROM check_events WHERE action='proj_forms_off' ORDER BY id DESC LIMIT 1;` → entrada de auditoria existe.

### DoD

- [ ] `submit_forms_event` consulta `is_forms_enabled_for_project` antes de decidir `should_queue_forms`
- [ ] Quando `forms_enabled=False`: skip com `reason=forms_disabled_for_project`
- [ ] Quando `forms_enabled=True`: comportamento atual preservado (sem regressão)
- [ ] `WebCheckHistoryResponse` ganha `transport_enabled: bool = True`
- [ ] `build_web_check_history_state` popula `transport_enabled` lendo do projeto ativo
- [ ] PUT em `/api/admin/projects/{id}` dispara `notify_web_check_data_changed("project_transport_flag")` apenas quando `transport_enabled` muda
- [ ] PUT grava `CheckEvent` `proj_forms_off` na transição True→False (nunca em OFF→OFF)
- [ ] PUT grava `CheckEvent` `proj_trans_off` na transição True→False (nunca em OFF→OFF)
- [ ] Actions de auditoria são strings de ≤ 16 caracteres
- [ ] Testes novos passando
- [ ] Pre-flight checks passam
- [ ] Smoke manual completo

### Próximo passo

Quando todos os itens do DoD estiverem marcados, **prossiga para o [Prompt 5](#prompt-5--commit-g-admin2-ui-com-toggles-e-telefone)** (Commit G — admin2 UI com toggles).

---

## Prompt 5 — Commit G: Admin2 UI com toggles e telefone

### Contexto

A tabela "Projetos" na aba Cadastro do admin2 ganha 3 colunas:
- **Forms** — toggle switch on/off
- **Transporte** — toggle switch on/off
- **Emergência** — input de telefone (string até 32 chars)

Comportamento:
- Toggle dispara PUT incremental imediato (`{ forms_enabled: true/false }`).
- Ao **desligar** (não ao ligar), um `confirm()` defensivo aparece. Cancelar reverte o toggle no DOM.
- Telefone salva em `blur` (perde foco) com PUT.
- Erro em qualquer PUT recarrega a tabela inteira via `loadProjects()` para resync.

Referência completa: [docs/temp001.md §21.6](temp001.md#216-frontend-admin2--tabela-de-projetos).

### Pré-requisitos

- Commits E + F (Prompts 3 + 4) mergeados — backend completo com gates ativos.
- Branch a partir de `main` atualizada.

### Arquivos a ler ANTES de modificar

1. [sistema/app/static/admin2/index.html:519-528](../sistema/app/static/admin2/index.html#L519-L528) — `<thead>` da tabela Projetos.
2. [sistema/app/static/admin2/app.js:4752-4766](../sistema/app/static/admin2/app.js#L4752-L4766) — `makeProjectRow`.
3. [sistema/app/static/admin2/app.js:5049-5071](../sistema/app/static/admin2/app.js#L5049-L5071) — `loadProjects`.
4. [sistema/app/static/admin2/app.js:5124-5180](../sistema/app/static/admin2/app.js#L5124-L5200) — handlers de "Editar" / "Remover" projeto (procurar `data-project-edit`).
5. [sistema/app/static/admin2/styles.css](../sistema/app/static/admin2/styles.css) — grep por `toggle-switch` para ver se já existe.
6. [sistema/app/static/admin2/app.js:2222-2242](../sistema/app/static/admin2/app.js#L2222-L2242) — `applyResponsiveLabels` (cobertura mobile já automática).
7. [sistema/app/static/admin2/app.js:1860-1867](../sistema/app/static/admin2/app.js#L1860-L1867) — `setStatus` (para feedback).

### Mudanças

#### Mudança 1 — `<thead>` da tabela Projetos

Em [admin2/index.html:521-526](../sistema/app/static/admin2/index.html#L521-L526), trocar:

```html
<tr><th>Nome do Projeto</th><th>País</th><th>Endereço</th><th>ZIP Code</th><th>Fuso horário</th><th>Ações</th></tr>
```

por:

```html
<tr><th>Nome do Projeto</th><th>País</th><th>Endereço</th><th>ZIP Code</th><th>Fuso horário</th><th>Forms</th><th>Transporte</th><th>Emergência</th><th>Ações</th></tr>
```

#### Mudança 2 — `makeProjectRow` ganha 3 colunas

Em [admin2/app.js:4752-4766](../sistema/app/static/admin2/app.js#L4752-L4766), substituir por:

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
      <label class="toggle-switch" title="Habilitar/desabilitar envio ao Microsoft Forms">
        <input type="checkbox" data-project-forms-toggle="${project.id}" data-project-name="${escapeHtml(project.name)}" ${formsChecked} />
        <span class="toggle-slider"></span>
      </label>
    </td>
    <td>
      <label class="toggle-switch" title="Mostrar/ocultar botão de Transporte no Check Web">
        <input type="checkbox" data-project-transport-toggle="${project.id}" data-project-name="${escapeHtml(project.name)}" ${transportChecked} />
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

#### Mudança 3 — Handlers de toggle e blur + `patchProjectFlag`

Em [admin2/app.js](../sistema/app/static/admin2/app.js), próximo aos handlers existentes de `data-project-edit` (grep por `data-project-edit` ou `data-project-remove`), adicionar:

```js
async function patchProjectFlag(projectId, payload) {
  try {
    await putJson(`/api/admin/projects/${projectId}`, payload);
    setStatus("Projeto atualizado.", true);
  } catch (error) {
    setStatus(error.message || "Falha ao atualizar projeto.", false);
    await loadProjects();  // resync
  }
}

function bindProjectFlagHandlers() {
  const projectsBody = document.getElementById("projectsBody");
  if (!projectsBody || projectsBody.dataset.flagHandlersBound === "true") return;
  projectsBody.dataset.flagHandlersBound = "true";

  projectsBody.addEventListener("change", async (evt) => {
    const formsToggle = evt.target.closest("[data-project-forms-toggle]");
    const transportToggle = evt.target.closest("[data-project-transport-toggle]");

    if (formsToggle) {
      const projectId = formsToggle.dataset.projectFormsToggle;
      const projectName = formsToggle.dataset.projectName;
      if (!formsToggle.checked) {
        const ok = window.confirm(
          `Tem certeza de que quer desligar o preenchimento do Microsoft Forms para o projeto ${projectName}? ` +
          "Atividades dos usuarios continuam sendo registradas, mas o Forms deixa de ser enviado."
        );
        if (!ok) {
          formsToggle.checked = true;  // reverter visualmente
          return;
        }
      }
      await patchProjectFlag(projectId, { forms_enabled: formsToggle.checked });
      return;
    }

    if (transportToggle) {
      const projectId = transportToggle.dataset.projectTransportToggle;
      const projectName = transportToggle.dataset.projectName;
      if (!transportToggle.checked) {
        const ok = window.confirm(
          `Tem certeza de que quer ocultar o botao de Transporte para os usuarios do projeto ${projectName}?`
        );
        if (!ok) {
          transportToggle.checked = true;
          return;
        }
      }
      await patchProjectFlag(projectId, { transport_enabled: transportToggle.checked });
      return;
    }
  });

  projectsBody.addEventListener("blur", async (evt) => {
    const emergencyInput = evt.target.closest("[data-project-emergency-input]");
    if (emergencyInput) {
      const projectId = emergencyInput.dataset.projectEmergencyInput;
      await patchProjectFlag(projectId, { emergency_phone: emergencyInput.value });
    }
  }, true);  // useCapture pra pegar blur
}
```

Chamar `bindProjectFlagHandlers()` no fim de `loadProjects` ([admin2/app.js:5049-5071](../sistema/app/static/admin2/app.js#L5049-L5071)):

```js
async function loadProjects() {
  // ... corpo existente ...
  rows.forEach((project) => body.appendChild(makeProjectRow(project)));
  applyResponsiveLabels("projectsBody");
  bindProjectFlagHandlers();  // NOVO
  return rows;
}
```

> O bind é **idempotente** via `dataset.flagHandlersBound` para não duplicar listeners em re-renders.

#### Mudança 4 — CSS `.toggle-switch`

Verificar primeiro se já existe:

```bash
grep -n "toggle-switch\|toggle-slider" sistema/app/static/admin2/styles.css
```

Se não existir, adicionar ao final de [admin2/styles.css](../sistema/app/static/admin2/styles.css):

```css
/* ── Toggle switch (Projetos) ───────────────────────────────────────── */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  vertical-align: middle;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
  margin: 0;
}
.toggle-slider {
  position: absolute;
  inset: 0;
  background: #ccc;
  border-radius: 22px;
  cursor: pointer;
  transition: background 0.2s;
}
.toggle-slider::before {
  content: "";
  position: absolute;
  height: 18px;
  width: 18px;
  left: 2px;
  top: 2px;
  background: white;
  border-radius: 50%;
  transition: transform 0.2s;
}
.toggle-switch input:checked + .toggle-slider {
  background: var(--accent-color, #1976d2);
}
.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}
.toggle-switch input:disabled + .toggle-slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Input de telefone de emergência */
.project-emergency-input {
  width: 100%;
  min-width: 100px;
  padding: 4px 6px;
  font-family: inherit;
  font-size: 0.9em;
  border: 1px solid #ccc;
  border-radius: 4px;
}
```

> Ajustar a variável `--accent-color` para a paleta real do admin2 (verificar se outras cores estão em `:root`).

### Testes a adicionar

Sem testes JS automatizados — validação manual.

### Testes existentes que NÃO podem quebrar

Backend não é tocado. Frontend admin2: confirmar via smoke manual.

```bash
pytest tests/ -x -q --ignore=tests/integration
```

### Pre-flight checks

```bash
# Confirmar mudanças
grep -n "data-project-forms-toggle\|data-project-transport-toggle\|data-project-emergency-input" sistema/app/static/admin2/app.js
grep -n "patchProjectFlag\|bindProjectFlagHandlers" sistema/app/static/admin2/app.js
grep -n "toggle-switch" sistema/app/static/admin2/styles.css

# Suite backend
pytest tests/ -x -q --ignore=tests/integration
```

### Validação manual

1. Abrir admin2 logado com perfil 9 → aba Cadastro.
2. Tabela "Projetos" mostra 9 colunas: Nome, País, Endereço, ZIP, Fuso, Forms, Transporte, Emergência, Ações.
3. Toggles refletem estado do DB (verificar com `GET /api/admin/projects`).
4. Clicar para **desligar** Forms de algum projeto → `confirm()` aparece → cancelar → toggle volta sozinho.
5. Clicar para **desligar** novamente → confirmar → toggle persiste → status "Projeto atualizado." aparece.
6. Conferir no DB que o flag foi alterado.
7. Religar (sem `confirm()` — porque é só ao desligar).
8. Editar telefone, sair do campo (blur) → status atualizado.
9. Recarregar página — valores persistem.
10. Em mobile (DevTools responsive mode), verificar que as 3 novas colunas têm `data-label` (aparece via `applyResponsiveLabels`).
11. Forçar erro: editar projeto via DB com nome inválido, depois alternar toggle. Esperar feedback de erro + tabela recarregada.

### DoD

- [ ] `<thead>` com 9 colunas
- [ ] `makeProjectRow` renderiza os 3 controles novos
- [ ] `patchProjectFlag` definida e usada
- [ ] `bindProjectFlagHandlers` definida e chamada em `loadProjects`
- [ ] Bind é idempotente (verificado via `dataset.flagHandlersBound`)
- [ ] Handler de `change` (toggles) com `confirm()` ao desligar
- [ ] Cancelar `confirm()` reverte o toggle no DOM
- [ ] Handler de `blur` (telefone) com `useCapture: true`
- [ ] CSS `.toggle-switch` + `.toggle-slider` adicionado
- [ ] CSS `.project-emergency-input` adicionado
- [ ] Smoke manual: criar projeto, alternar toggles (cancelar e confirmar), editar telefone, recarregar
- [ ] Mobile responsive: data-labels presentes nas 3 novas colunas
- [ ] Erro em PUT recarrega tabela via `loadProjects()`
- [ ] Pre-flight checks passam

### Próximo passo

Quando todos os itens do DoD estiverem marcados, **prossiga para o [Prompt 6](#prompt-6--commit-h-check-web-respeita-transport_enabled-e-renomeia-label)** (Commit H — Check Web).

---

## Prompt 6 — Commit H: Check Web respeita `transport_enabled` e renomeia label

### Contexto

Duas mudanças no Check Web (`sistema/app/static/check/`):

1. **Renomear i18n**: chave `transportTestingLabel` → `transportLabel` em 6 dicionários (pt/en/zh/ms/id/tl), com novos valores: Transporte / Transport / 运输 / Pengangkutan / Transportasi / Transportasyon.
2. **Visibilidade dinâmica**: o botão de Transporte some quando o projeto ativo tem `transport_enabled=false`. Quando some, o grid colapsa de `three-columns` → `two-columns` (Check-In + Check-Out de largura igual). Quando o admin religa, o Check Web atualiza via SSE.

Referência completa: [docs/temp001.md §21.7](temp001.md#217-frontend-check-web--esconder-botão-de-transporte-e-renomear-label).

### Pré-requisitos

- Commits E + F + G (Prompts 3, 4, 5) mergeados — backend e admin2 prontos.
- Branch a partir de `main` atualizada.

### Arquivos a ler ANTES de modificar

1. [sistema/app/static/check/index.html:173-194](../sistema/app/static/check/index.html#L173-L194) — fieldset `registrationField` com o botão.
2. [sistema/app/static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js) — grep por `transportTestingLabel` para listar todas as 6 ocorrências.
3. [sistema/app/static/check/app.js:40](../sistema/app/static/check/app.js#L40) — referência ao `transportButton`.
4. [sistema/app/static/check/app.js:1311-1389](../sistema/app/static/check/app.js#L1311-L1389) — bloco que aplica i18n no botão (`transportActionLabel`).
5. [sistema/app/static/check/app.js:7273-7274](../sistema/app/static/check/app.js#L7273-L7274) — bind de click no botão.
6. [sistema/app/static/check/styles.css:896-908](../sistema/app/static/check/styles.css#L896-L908) — `.choice-grid.two-columns` e `.choice-grid.three-columns` (já existem).
7. [sistema/app/static/check/app.js](../sistema/app/static/check/app.js) — grep por `applyStateResponse`, `handleStateUpdated`, `refreshState`, ou nome equivalente para localizar pontos onde o state é aplicado.

### Mudanças

#### Mudança 1 — Renomear chave i18n nos 6 dicionários

Em [sistema/app/static/check/i18n-dictionaries.js](../sistema/app/static/check/i18n-dictionaries.js), buscar todas as ocorrências de `transportTestingLabel`:

```bash
grep -n "transportTestingLabel" sistema/app/static/check/i18n-dictionaries.js
```

Esperado: 6 linhas (~58, 547, 997, 1291, 1585, 1879). Em cada uma, trocar:

| Linha aproximada | Idioma | Antes | Depois |
|---|---|---|---|
| 58 | pt | `transportTestingLabel: 'Em Teste',` | `transportLabel: 'Transporte',` |
| 547 | en | `transportTestingLabel: 'In Testing',` | `transportLabel: 'Transport',` |
| 997 | zh | `transportTestingLabel: '测试中',` | `transportLabel: '运输',` |
| 1291 | ms | `transportTestingLabel: 'Dalam Ujian',` | `transportLabel: 'Pengangkutan',` |
| 1585 | id | `transportTestingLabel: 'Dalam Uji Coba',` | `transportLabel: 'Transportasi',` |
| 1879 | tl | `transportTestingLabel: 'Sinusubukan',` | `transportLabel: 'Transportasyon',` |

#### Mudança 2 — Referência no `app.js`

Em [check/app.js:1389](../sistema/app/static/check/app.js#L1389), trocar:

```js
applyTextContent(transportActionLabel, t('registration.transportTestingLabel'));
```

por:

```js
applyTextContent(transportActionLabel, t('registration.transportLabel'));
```

#### Mudança 3 — Função `applyTransportEnabledFlag(state)`

Adicionar perto das outras funções de aplicação de estado (grep por `applyStateResponse` ou similar para achar local idiomático). Sugestão de função:

```js
function applyTransportEnabledFlag(state) {
  if (!transportButton) return;
  const enabled = state?.transport_enabled !== false;  // default true por segurança
  const choiceGrid = transportButton.closest('.choice-grid');
  if (!choiceGrid) return;

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

> A classe `.hidden { display: none; }` deve já existir no projeto (convenção). Confirmar com:
> ```bash
> grep -n "\\.hidden\\s*{" sistema/app/static/check/styles.css
> ```
> Se não existir, adicionar: `.hidden { display: none !important; }` em algum lugar apropriado do styles.css.

#### Mudança 4 — Chamar `applyTransportEnabledFlag` em pontos de aplicação de state

Identificar todos os pontos onde o state é aplicado. Buscar por uma função tipo `applyStateResponse(state)`, `handleStateUpdated(state)`, ou similar:

```bash
grep -n "function applyStateResponse\|function handleStateUpdated\|function refreshState\|stateEndpoint\|loadCheckState" sistema/app/static/check/app.js
```

Em cada local que processa um state recém-recebido (após login, após swap de projeto, após SSE refresh), adicionar a chamada:

```js
applyTransportEnabledFlag(state);
```

Tipicamente: pelo menos em (a) handler do `stateEndpoint` na inicialização, (b) handler do SSE em `/api/web/check/stream` que atualiza estado.

### Testes a adicionar

Sem testes JS automatizados. Manual.

Se houver `tests/*.test.js` que verifique a label antiga, atualizar. Buscar:

```bash
grep -rn "transportTestingLabel\|Em Teste" tests/ scripts/ deploy/
```

### Testes existentes que NÃO podem quebrar

```bash
pytest tests/ -x -q --ignore=tests/integration
```

### Pre-flight checks

```bash
# Grep zero ocorrências de transportTestingLabel
grep -rn "transportTestingLabel" sistema/ tests/ scripts/ deploy/
# Esperado: 0 resultados

# Grep mostra novo nome
grep -rn "transportLabel" sistema/app/static/check/
# Esperado: 6 dicionários + 1 referência em app.js = 7 ocorrências

# applyTransportEnabledFlag definida e chamada
grep -n "applyTransportEnabledFlag" sistema/app/static/check/app.js

# Suite backend
pytest tests/ -x -q --ignore=tests/integration
```

### Validação manual

1. Subir app. Abrir `http://localhost:8000/check` em um navegador.
2. Logar com um usuário que tenha projeto com `transport_enabled=true` (default). Confirmar que botão "Transporte" aparece, grid em 3 colunas.
3. **Trocar idioma para EN/ZH/MS/ID/TL** via configurações: label fica "Transport" / "运输" / "Pengangkutan" / "Transportasi" / "Transportasyon" respectivamente — **não** "In Testing" etc.
4. Em outro browser/aba (admin2), desligar transporte do projeto.
5. Voltar ao Check Web — botão deve sumir em até alguns segundos (via SSE) sem F5. Grid colapsa para 2 colunas. Check-In e Check-Out ocupam largura igual.
6. Religar transporte no admin. Voltar ao Check Web. Botão retorna; grid volta a 3 colunas.
7. Logar com usuário de projeto com transporte OFF desde o início. Botão **nunca** aparece após login.

### DoD

- [ ] 6 ocorrências de `transportTestingLabel` renomeadas para `transportLabel` em `i18n-dictionaries.js`
- [ ] Valores traduzidos para 6 idiomas (Transporte/Transport/运输/Pengangkutan/Transportasi/Transportasyon)
- [ ] Referência em `app.js:1389` atualizada para `t('registration.transportLabel')`
- [ ] Função `applyTransportEnabledFlag` definida
- [ ] Função chamada em todos os pontos que aplicam state (login, swap de projeto, SSE refresh)
- [ ] Classe `.hidden` aplicada para esconder o botão (confirmar CSS existe)
- [ ] Grid colapsa de 3 → 2 colunas e volta sem layout shift
- [ ] Smoke manual em PT + 1 outro idioma
- [ ] Ciclo via SSE: admin desliga → UI atualiza sem F5 em até 5 s
- [ ] Pre-flight checks (grep zero de `transportTestingLabel`)

### Próximo passo

Quando todos os itens do DoD estiverem marcados, **prossiga para o [Prompt 7](#prompt-7--commit-a-redução-de-pausas-no-forms-worker)** (Commit A — redução de pausas).

---

# FASE 3 — Parte I: Otimização do Forms worker

## Prompt 7 — Commit A: Redução de pausas no Forms worker

### Contexto

O worker do Forms (`forms_worker.py`) tem 8 pausas explícitas por submissão somando ~17,5 s (caminho checkin). Três delas excedem 1 s e podem ser reduzidas para 1 s sem perda:

| Constante | Valor atual | Novo |
|---|---|---|
| `URL_LOAD_SETTLE_SECONDS` | 3.0 | **1.0** |
| `AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS` | 2.0 | **1.0** |
| `POST_SUBMIT_SETTLE_SECONDS` | 5.0 | **1.0** |

Justificativa: `page.goto`, retry interno e `_wait_for_step` já cobrem a janela. Ganho: ~7 s por submissão.

Tornamos configurável via env para permitir rollback sem deploy.

Referência completa: [docs/temp001.md §1](temp001.md#1-fase-1--redução-de-pausas).

### Pré-requisitos

- Commits C, D, E, F, G, H (Prompts 1-6) mergeados.
- Sinergia: se Parte III já está em prod, você pode desligar `forms_enabled` em projetos não-críticos durante o teste de carga isolado (ver §A.3).
- Branch a partir de `main` atualizada.

### Arquivos a ler ANTES de modificar

1. [sistema/app/services/forms_worker.py:1-30](../sistema/app/services/forms_worker.py#L1-L30) — constantes de pausa.
2. [sistema/app/services/forms_worker.py:230-360](../sistema/app/services/forms_worker.py#L230-L360) — `_submit_once` que usa as pausas.
3. [sistema/app/core/config.py:46-51](../sistema/app/core/config.py#L46-L51) — settings existentes do Forms (referência de padrão).
4. [docker-compose.yml:97-130](../docker-compose.yml#L97-L130) — bloco `forms-worker` que precisa receber env novas.
5. [.env.example](../.env.example) e [deploy/.env.production.example](../deploy/.env.production.example) — onde declarar exemplos.
6. [tests/test_forms_worker_resilience.py:1-100](../tests/test_forms_worker_resilience.py#L1-L100) — referência de FakePage para testes.

### Mudanças

#### Mudança 1 — Settings novos

Em [sistema/app/core/config.py](../sistema/app/core/config.py), após `forms_worker_unhealthy_consecutive_errors` (linha ~51):

```python
forms_settle_url_load_seconds: float = 1.0
forms_settle_after_checkout_discovery_seconds: float = 1.0
forms_settle_post_submit_seconds: float = 1.0
```

#### Mudança 2 — `forms_worker.py` lê settings inline

Em [sistema/app/services/forms_worker.py:18-24](../sistema/app/services/forms_worker.py#L18-L24), **remover** as três constantes:

```python
# REMOVER:
URL_LOAD_SETTLE_SECONDS = 3.0
AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS = 2.0
POST_SUBMIT_SETTLE_SECONDS = 5.0
```

Em `_submit_once` ([forms_worker.py:230-360](../sistema/app/services/forms_worker.py#L230-L360)), localizar os 3 usos via grep:

```bash
grep -n "URL_LOAD_SETTLE_SECONDS\|AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS\|POST_SUBMIT_SETTLE_SECONDS" sistema/app/services/forms_worker.py
```

E substituir cada um por leitura inline:

```python
# Em vez de:
self._pause(page, URL_LOAD_SETTLE_SECONDS)
# usar:
self._pause(page, settings.forms_settle_url_load_seconds)

# Idem para os outros dois
self._pause(page, settings.forms_settle_after_checkout_discovery_seconds)
self._pause(page, settings.forms_settle_post_submit_seconds)
```

> O import `from ..core.config import settings` já existe em [forms_worker.py:9](../sistema/app/services/forms_worker.py#L9) — sem necessidade de adicionar.

#### Mudança 3 — docker-compose + envs de exemplo

Em [docker-compose.yml](../docker-compose.yml), na seção `forms-worker.environment` (em torno da linha 105-121), adicionar:

```yaml
FORMS_SETTLE_URL_LOAD_SECONDS: ${FORMS_SETTLE_URL_LOAD_SECONDS:-1.0}
FORMS_SETTLE_AFTER_CHECKOUT_DISCOVERY_SECONDS: ${FORMS_SETTLE_AFTER_CHECKOUT_DISCOVERY_SECONDS:-1.0}
FORMS_SETTLE_POST_SUBMIT_SECONDS: ${FORMS_SETTLE_POST_SUBMIT_SECONDS:-1.0}
```

Em [.env.example](../.env.example) e [deploy/.env.production.example](../deploy/.env.production.example), adicionar comentários e defaults:

```bash
# Forms worker — pausas internas (segundos). Default 1.0 cada.
# Para rollback sem deploy: subir os valores e reiniciar o container forms-worker.
FORMS_SETTLE_URL_LOAD_SECONDS=1.0
FORMS_SETTLE_AFTER_CHECKOUT_DISCOVERY_SECONDS=1.0
FORMS_SETTLE_POST_SUBMIT_SECONDS=1.0
```

### Testes a adicionar

Em `tests/services/test_forms_submit_resilience.py` (ou criar `tests/services/test_forms_worker_settle.py`):

```python
from sistema.app.core.config import settings


def test_settle_defaults_are_capped_at_one_second():
    """Garante o contrato com o usuário: pausas reduzidas para máximo de 1 s."""
    assert settings.forms_settle_url_load_seconds <= 1.0
    assert settings.forms_settle_after_checkout_discovery_seconds <= 1.0
    assert settings.forms_settle_post_submit_seconds <= 1.0
```

Em `tests/test_forms_worker_resilience.py`, adicionar:

```python
def test_settle_values_come_from_settings(tmp_path, monkeypatch):
    """Verifica que os pauses obedecem aos settings, não a constantes hardcoded."""
    monkeypatch.setattr(settings, "forms_settle_url_load_seconds", 0.5)
    monkeypatch.setattr(settings, "forms_settle_after_checkout_discovery_seconds", 0.5)
    monkeypatch.setattr(settings, "forms_settle_post_submit_seconds", 0.5)

    _write_xpath_files(tmp_path)
    waits = []

    class CapturingFakePage(FakePage):  # reaproveitar FakePage do arquivo
        def wait_for_timeout(self, ms):
            waits.append(ms)

    # ... executar _submit_once com FakeBrowser ...
    # Assert que valores 500 aparecem em waits (e não 3000, 2000, 5000)
    assert 500 in waits
    assert 3000 not in waits
    assert 2000 not in waits
    assert 5000 not in waits
```

> Adapte o teste à estrutura do `FakePage` existente — pode precisar adicionar método `wait_for_timeout` se não existir.

### Testes existentes que NÃO podem quebrar

```bash
pytest tests/ -x -q --ignore=tests/integration
```

Verificar que nenhum teste verifica os valores antigos (3000, 2000, 5000) em ms:

```bash
grep -rn "wait_for_timeout(3000)\|wait_for_timeout(2000)\|wait_for_timeout(5000)" tests/
```

Esperado: 0 resultados. Se houver, atualizar.

### Pre-flight checks

```bash
# Suite completa
pytest tests/ -x -q --ignore=tests/integration

# Testes específicos
pytest tests/services/test_forms_worker_settle.py tests/test_forms_worker_resilience.py -x -v

# Confirmar substituições
grep -n "URL_LOAD_SETTLE_SECONDS\|AFTER_CHECKOUT_DISCOVERY_SETTLE_SECONDS\|POST_SUBMIT_SETTLE_SECONDS" sistema/app/services/forms_worker.py
# Esperado: 0 resultados (constantes removidas, só uso inline de settings.*)

# Confirmar settings
grep -n "forms_settle" sistema/app/core/config.py

# Confirmar docker-compose
grep -n "FORMS_SETTLE_" docker-compose.yml .env.example deploy/.env.production.example
```

### Validação manual

1. Subir o worker localmente: `python -m sistema.app.forms_worker_main` (ou via docker-compose).
2. Enfileirar 1 submissão checkin e 1 checkout (via API, script, ou fixture).
3. Cronometrar via logs `forms_queue_processed` (campo `turnaround_ms`).
4. **Esperado:** turnaround ~7 s menor que baseline atual.
5. Testar rollback via env: setar `FORMS_SETTLE_POST_SUBMIT_SECONDS=3.0`, reiniciar worker, observar que pausa aumenta. Voltar a 1.0.

### DoD

- [ ] 3 settings novos em `core/config.py`
- [ ] 3 constantes `_SETTLE_SECONDS` removidas de `forms_worker.py`
- [ ] 3 chamadas `self._pause(page, settings.forms_settle_*_seconds)` inline em `_submit_once`
- [ ] docker-compose.yml com 3 env vars novas (com defaults `1.0`)
- [ ] `.env.example` e `deploy/.env.production.example` com comentários + valores
- [ ] Teste `test_settle_defaults_are_capped_at_one_second` passando
- [ ] Teste `test_settle_values_come_from_settings` passando
- [ ] Grep confirma 0 ocorrências das constantes antigas
- [ ] Grep confirma 0 ocorrências de `wait_for_timeout(3000/2000/5000)` em testes
- [ ] Smoke manual: 1 submissão completa em ~7 s a menos que antes
- [ ] Pre-flight checks passam

### Próximo passo

Quando todos os itens do DoD estiverem marcados, **prossiga para o [Prompt 8](#prompt-8--commit-b-concorrência-no-forms-worker)** (Commit B — concorrência no worker).

---

## Prompt 8 — Commit B: Concorrência no Forms worker

### Contexto

O `FormsSubmissionWorker` atual roda single-thread. Refatoramos para uma thread pool com **3 threads consumidoras** (configurável via `FORMS_WORKER_CONCURRENCY`), cada uma executando claim atômico + `_process_submission` em loop self-watchdog (try/except envolvendo tudo; threads nunca saem voluntariamente). Backoff é per-thread — uma falhar não bloqueia as outras.

Decisões críticas (não revisitar):
- Pool DB do worker sobe de 2+1 para 5+2 conexões.
- `process_forms_submission_queue_once` permanece **serial** e intacto (testes dependem dele).
- Supervisor usa novo método público `has_alive_consumers()`.
- Snapshot agregado preserva todos os campos atuais + adiciona `concurrency` e `consumer_threads_alive`.
- Teste `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` **precisa ser atualizado**.

Referência completa: [docs/temp001.md §2](temp001.md#2-fase-2--concorrência).

### Pré-requisitos

- Commit A (Prompt 7) mergeado e estável em produção/homologação.
- Branch a partir de `main` atualizada.
- Janela de deploy: **madrugada / fim de semana** (ver §A.4).

### Arquivos a ler ANTES de modificar

1. [sistema/app/services/forms_queue.py:664-862](../sistema/app/services/forms_queue.py#L664-L862) — `FormsSubmissionWorker` + supervisor.
2. [sistema/app/services/forms_queue.py:509-561](../sistema/app/services/forms_queue.py#L509-L561) — `process_forms_submission_queue_once`, `_reserve_next_submission_id`, `_claim_submission_for_processing` (NÃO mexer; só ler para entender).
3. [sistema/app/services/forms_queue.py:205-275](../sistema/app/services/forms_queue.py#L205-L275) — `_build_observed_worker_snapshot` e `get_forms_worker_health_failure_reason`.
4. [sistema/app/core/config.py:46-54](../sistema/app/core/config.py#L46-L54) — settings do worker (referência).
5. [tests/test_api_flow.py:5776-5840](../tests/test_api_flow.py#L5776-L5840) — teste crítico `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit`.
6. [tests/services/test_forms_queue_worker_down_warning.py](../tests/services/test_forms_queue_worker_down_warning.py) — testes que NÃO devem quebrar.
7. [docker-compose.yml:97-130](../docker-compose.yml#L97-L130) — `forms-worker.environment`.

### Mudanças

#### Mudança 1 — Settings

Em [sistema/app/core/config.py](../sistema/app/core/config.py):

```python
forms_worker_concurrency: int = 3
forms_worker_idle_poll_seconds: float = 0.25
```

#### Mudança 2 — Refatorar `FormsSubmissionWorker`

Em [sistema/app/services/forms_queue.py:664-783](../sistema/app/services/forms_queue.py#L664-L783), substituir a classe inteira pelo modelo abaixo:

```python
class FormsSubmissionWorker:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._consumer_threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._status = "stopped"
        self._started_at: datetime | None = None
        self._start_count = 0
        self._per_thread: dict[int, dict] = {}
        self._supervisor_backoff_seconds = 0.0

    def start(self) -> None:
        """Idempotente. Spawna threads consumidoras faltantes até atingir concurrency."""
        with self._lock:
            if self._stop_event.is_set():
                self._stop_event = threading.Event()
            target_count = max(int(settings.forms_worker_concurrency), 1)
            alive = [t for t in self._consumer_threads if t.is_alive()]
            self._consumer_threads = alive
            if len(alive) >= target_count:
                return
            if not alive:
                self._started_at = now_sgt()
                self._per_thread = {}
                self._start_count += 1
                self._status = "starting"
            for _ in range(target_count - len(alive)):
                thread_index = len(self._consumer_threads)
                t = threading.Thread(
                    target=self._run_consumer,
                    name=f"forms-submission-worker-{thread_index}",
                    daemon=True,
                )
                self._consumer_threads.append(t)
                t.start()
        _log_forms_queue_event(
            "forms_queue_worker_started",
            poll_interval_seconds=settings.forms_worker_idle_poll_seconds,
            concurrency=target_count,
        )

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            threads = list(self._consumer_threads)
        for t in threads:
            t.join(timeout=2)
        with self._lock:
            self._consumer_threads = []
            self._status = "stopped"
        _log_forms_queue_event("forms_queue_worker_stopped")

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
        with self._lock:
            alive_count = sum(1 for t in self._consumer_threads if t.is_alive())
            states = list(self._per_thread.values())
            running = alive_count > 0
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
                "thread_name": primary_thread_name,
                "started_at": self._started_at,
                "last_loop_started_at": last_loop_started_at,
                "last_loop_completed_at": last_loop_completed_at,
                "last_loop_processed_count": processed_total,
                "consecutive_error_count": max_consecutive_errors,
                "current_backoff_seconds": max(max_backoff, self._supervisor_backoff_seconds),
                "restart_count": max(self._start_count - 1, 0),
                "last_error": last_error,
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
```

#### Mudança 3 — Supervisor usa `has_alive_consumers()`

Em [sistema/app/services/forms_queue.py:789-862](../sistema/app/services/forms_queue.py#L789-L862), substituir:

```python
thread = forms_submission_worker._thread
if thread is not None and thread.is_alive():
```

por:

```python
if forms_submission_worker.has_alive_consumers():
```

Conferir que `forms_submission_worker._stop_event.wait(...)` ainda funciona (esse atributo continua existindo).

#### Mudança 4 — `_build_observed_worker_snapshot` reflete novos campos

Em [sistema/app/services/forms_queue.py:205-245](../sistema/app/services/forms_queue.py#L205-L245), no dict de retorno, adicionar:

```python
"concurrency": int(raw_snapshot.get("concurrency") or settings.forms_worker_concurrency),
"consumer_threads_alive": int(raw_snapshot.get("consumer_threads_alive") or 0),
```

#### Mudança 5 — Atualizar teste `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit`

Em [tests/test_api_flow.py:5776-5840](../tests/test_api_flow.py#L5776-L5840), localizar a `FakeWorker` e adicionar:

```python
class FakeWorker:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread = None
        self._consumer_threads = []  # NOVO
        self.start_calls = 0
        self.stop_calls = 0
        self.backoff_waits: list[float] = []

    def start(self) -> None:
        self.start_calls += 1
        self._thread = DeadThread()
        self._consumer_threads = [DeadThread()]  # NOVO
        if self.start_calls >= 2:
            self._stop_event.set()

    def stop(self) -> None:
        self.stop_calls += 1
        self._stop_event.set()
        self._thread = None
        self._consumer_threads = []  # NOVO

    def stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def has_alive_consumers(self) -> bool:  # NOVO
        return False

    def mark_supervisor_restart_wait(self, *, backoff_seconds: float) -> None:
        self.backoff_waits.append(backoff_seconds)

    def snapshot(self) -> dict[str, object]:
        return {
            "running": False,
            "status": "stopped",
            "thread_name": "forms-submission-worker",
            "started_at": now_sgt(),
            "last_loop_started_at": None,
            "last_loop_completed_at": None,
            "last_loop_processed_count": 0,
            "consecutive_error_count": 0,
            "current_backoff_seconds": 0.0,
            "restart_count": max(self.start_calls - 1, 0),
            "last_error": "thread exited unexpectedly",
            "concurrency": 1,            # NOVO
            "consumer_threads_alive": 0, # NOVO
        }
```

#### Mudança 6 — docker-compose pool DB + concurrency env

Em [docker-compose.yml:107-121](../docker-compose.yml#L107-L121), seção `forms-worker.environment`:

```yaml
FORMS_WORKER_CONCURRENCY: ${FORMS_WORKER_CONCURRENCY:-3}
FORMS_WORKER_IDLE_POLL_SECONDS: ${FORMS_WORKER_IDLE_POLL_SECONDS:-0.25}
FORMS_WORKER_DATABASE_POOL_SIZE: ${FORMS_WORKER_DATABASE_POOL_SIZE:-5}    # antes 2
FORMS_WORKER_DATABASE_MAX_OVERFLOW: ${FORMS_WORKER_DATABASE_MAX_OVERFLOW:-2}  # antes 1
```

Também em [.env.example](../.env.example) e [deploy/.env.production.example](../deploy/.env.production.example).

### Testes a adicionar

Criar `tests/services/test_forms_worker_concurrency.py`:

```python
import threading
import time
from unittest.mock import patch

import pytest

from sistema.app.core.config import settings
from sistema.app.services import forms_queue as forms_queue_module
from sistema.app.services.forms_queue import FormsSubmissionWorker


def _enqueue_n_fake_submissions(db_session, n):
    # helper que cria N linhas em forms_submissions com status='pending'
    ...


def test_three_pending_items_processed_concurrently(db_session, monkeypatch):
    monkeypatch.setattr(settings, "forms_worker_concurrency", 3)
    monkeypatch.setattr(settings, "forms_worker_idle_poll_seconds", 0.05)
    _enqueue_n_fake_submissions(db_session, 3)

    process_times = []
    def slow_process(submission_id):
        process_times.append(time.monotonic())
        time.sleep(2.0)

    with patch.object(forms_queue_module, "_process_submission", slow_process):
        worker = FormsSubmissionWorker()
        worker.start()
        time.sleep(3.5)
        worker.stop()

    # Esperado: 3 processados em ~2-3 s (paralelo), não 6 s sequencial
    assert len(process_times) == 3
    span = max(process_times) - min(process_times)
    assert span < 1.0  # iniciaram dentro de uma janela pequena (paralelo)


def test_atomic_claim_under_thread_pressure(db_session):
    _enqueue_n_fake_submissions(db_session, 10)
    claimed = []
    claim_lock = threading.Lock()

    def claim_loop():
        while True:
            sid = forms_queue_module._reserve_next_submission_id()
            if sid is None:
                break
            with claim_lock:
                claimed.append(sid)

    threads = [threading.Thread(target=claim_loop) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert len(claimed) == 10
    assert len(set(claimed)) == 10  # zero duplicação


def test_one_consumer_error_does_not_block_others(db_session, monkeypatch):
    monkeypatch.setattr(settings, "forms_worker_concurrency", 2)
    monkeypatch.setattr(settings, "forms_worker_idle_poll_seconds", 0.05)
    _enqueue_n_fake_submissions(db_session, 5)

    call_count = {"n": 0}
    def maybe_failing_process(submission_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated failure")
        time.sleep(0.1)

    with patch.object(forms_queue_module, "_process_submission", maybe_failing_process):
        worker = FormsSubmissionWorker()
        worker.start()
        time.sleep(3.0)
        worker.stop()

    # Esperado: 5 processados (incluindo o que falhou pode ter retornado para pending, mas eventualmente todos drenam)
    assert call_count["n"] >= 5


def test_snapshot_aggregates_concurrency_info(monkeypatch):
    monkeypatch.setattr(settings, "forms_worker_concurrency", 3)
    worker = FormsSubmissionWorker()
    worker.start()
    time.sleep(0.5)
    snap = worker.snapshot()
    assert snap["concurrency"] == 3
    assert snap["consumer_threads_alive"] == 3
    worker.stop()
    snap = worker.snapshot()
    assert snap["running"] is False
    assert snap["consumer_threads_alive"] == 0


def test_start_is_idempotent_and_respawns_missing_threads(monkeypatch):
    monkeypatch.setattr(settings, "forms_worker_concurrency", 3)
    worker = FormsSubmissionWorker()
    worker.start()
    time.sleep(0.3)
    assert worker.consumer_threads_alive_count() == 3

    # Forçar morte de uma thread (não trivial; alternativa: stop + restart parcial)
    # Aqui só re-chamamos start e verificamos idempotência:
    worker.start()
    assert worker.consumer_threads_alive_count() == 3  # não duplicou

    worker.stop()
```

> Adapte `_enqueue_n_fake_submissions` à fixture de DB do projeto. Os testes devem ser rápidos (< 5 s no total).

### Testes existentes que NÃO podem quebrar

**Crítico:** `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` em `tests/test_api_flow.py:5776` — já atualizado na Mudança 5.

Demais:
- `tests/services/test_forms_queue_worker_down_warning.py` — mocka snapshot inteiro; passa sem mudança.
- ~10 testes que chamam `process_forms_submission_queue_once(...)` — função intocada.

```bash
pytest tests/ -x -q --ignore=tests/integration
```

### Pre-flight checks

```bash
# Suite completa
pytest tests/ -x -q --ignore=tests/integration

# Testes específicos
pytest tests/services/test_forms_worker_concurrency.py tests/test_api_flow.py::test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit -x -v

# Confirmar substituições
grep -n "has_alive_consumers\|consumer_threads_alive\|_per_thread" sistema/app/services/forms_queue.py
grep -n "FORMS_WORKER_CONCURRENCY\|FORMS_WORKER_DATABASE_POOL_SIZE" docker-compose.yml

# Build do container
docker compose build forms-worker
```

### Validação manual (homologação)

**Janela:** madrugada / fim de semana (ver §A.4).

1. Deploy em homologação com `FORMS_WORKER_CONCURRENCY=1`. Confirmar comportamento idêntico ao Commit A (sem regressão).
2. Subir para `FORMS_WORKER_CONCURRENCY=3`. Reiniciar `forms-worker`.
3. Injetar 10 submissões via script (`scripts/load/phase10_forms_backlog.example.json` se existir).
4. Medir `oldest_backlog_age_seconds` via `GET /api/admin/forms/queue/diagnostics`. **Esperado:** drena em ~33% do tempo vs concurrency=1.
5. Monitorar `docker stats forms-worker` durante drenagem. Anotar pico de RAM/CPU.
6. **Resiliência:** forçar erro em 1 submissão (ex: chave inválida que dispara `FormsStepTimeoutError`). Validar via logs `forms_queue_consumer_error` que só uma thread aplicou backoff; outras continuaram drenando.
7. **Health:** `docker kill forms-worker`. Diagnóstico do admin mostra `worker.running=false`. Aviso `forms_warn` dispara na próxima enqueue.
8. Validar via `GET /api/admin/forms/queue/diagnostics`:
   - `worker.concurrency = 3`
   - `worker.consumer_threads_alive = 3`
   - `worker.status = "running"` ou `"idle"`

### DoD

- [ ] 2 settings novos em `core/config.py` (`forms_worker_concurrency`, `forms_worker_idle_poll_seconds`)
- [ ] `FormsSubmissionWorker` refatorada (pool, self-watchdog, snapshot agregado)
- [ ] Métodos públicos novos: `has_alive_consumers()`, `consumer_threads_alive_count()`
- [ ] Supervisor usa `has_alive_consumers()` (não mais `_thread.is_alive()`)
- [ ] Snapshot inclui `concurrency` e `consumer_threads_alive`
- [ ] Backoff per-thread (uma thread em backoff não bloqueia as outras)
- [ ] `start()` idempotente (testado)
- [ ] Teste `test_run_forms_submission_worker_forever_restarts_after_unexpected_thread_exit` atualizado com `has_alive_consumers` e novos campos no snapshot
- [ ] 5 testes novos em `test_forms_worker_concurrency.py` passando
- [ ] docker-compose com `FORMS_WORKER_CONCURRENCY=3`, pool DB 5+2
- [ ] `.env.example` + `deploy/.env.production.example` atualizados
- [ ] Pre-flight checks (incluindo build do container) passam
- [ ] Smoke manual em homologação: drenagem ~3× mais rápida; sem regressão com `concurrency=1`
- [ ] `docs/forms_routine.md` §9.3 e §13 atualizados (mencionar multi-thread)
- [ ] `docker stats forms-worker` durante teste: pico abaixo do limite do droplet

### Próximo passo

Este é o **último prompt** do plano `temp001.md`.

Quando todos os itens do DoD estiverem marcados:

1. Confirmar que todos os 8 commits (A-H) foram mergeados em produção e estão estáveis.
2. Atualizar a tabela de Status no topo de [docs/temp001.md](temp001.md) — todas as Partes para "Concluído".
3. Considerar mover [docs/temp001.md](temp001.md) e [docs/temp001a.md](temp001a.md) para `docs/done/` ou similar, mantendo como histórico das decisões.
4. Arquivar memórias relevantes no sistema de memória do agente para futuras sessões.

**Plano de melhorias do Checking concluído.** 🎯
