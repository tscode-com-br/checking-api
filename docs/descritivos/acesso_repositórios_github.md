# Acesso aos repositorios GitHub do projeto

Status deste documento: reconciliado com a conta GitHub, com os remotes locais e com o fluxo operacional de commit/push apos a separacao da API em repositorio proprio em 2026-05-24.

Este arquivo substitui o antigo guia `instrucoes_commit_push.md` e consolida quatro coisas diferentes que nao devem mais ser misturadas:

1. as pastas Git locais que ainda existem no workspace;
2. os repositorios que ainda existem de fato na conta GitHub `tscode-com-br`;
3. quais repositorios GitHub ja estao ligados a remotes ativos neste workspace;
4. qual repositorio realmente aciona deploy de producao.

## 1. Realidade atual: workspace local versus conta GitHub

O workspace possui seis pastas que sao repositorios Git locais. A conta GitHub `tscode-com-br` expõe onze repositorios; seis deles ja estao conectados a remotes ativos neste workspace.

| Escopo | Pasta local | Branch local | Remotes ativos | Repo GitHub | Deploy automatico |
| --- | --- | --- | --- | --- | --- |
| Infraestrutura / monorepo espelho | `c:\dev\projetos\checkcheck` | `main` | `origin = checking` | `tscode-com-br/checking` | `deploy-oceandrive.yml` na branch `main` do `origin`; guarda `if: github.repository == 'tscode-com-br/checking'` |
| API (Sistema Principal) | `c:\dev\projetos\checkcheck` | `main` | `api = checking-api` | `tscode-com-br/checking-api` | `deploy.yml` na branch `main` do `api`; builda `ghcr.io/tscode-com-br/checking-api` e `checking-api-forms`; usa `docker-compose.api.yml` |
| Admin v2 | `sistema\app\static\admin2` | `main` | `origin = checking-admin2` | `tscode-com-br/checking-admin2` (privado) | `deploy.yml` do sub-repo; push em `main` reinicia conteiner `admin2-web` |
| Check Web | `sistema\app\static\check` | `main` | `origin = checking-webapp` | `tscode-com-br/checking-webapp` | `deploy.yml` do sub-repo; push em `main` reinicia conteiner `user-web` |
| Transport | `sistema\app\static\transport` | `main` | `origin = checking-transport` | `tscode-com-br/checking-transport` | `deploy.yml` do sub-repo; push em `main` reinicia conteiner `transport-web` |
| App Flutter | `checking_android_new` | `main` | `origin = checking_app_flutter` | `tscode-com-br/checking_app_flutter` | Build de APK/AAB via GitHub Actions do proprio repo |
| App Kotlin legado | `checking_kotlin` | `main` | `archived-origin` (morto) | Nao existe mais | Local-only; sem deploy |
| App Kotlin novo | `checking_kotlin_new` | `web-parity-spa-baseline` | `archived-origin` (morto) | Nao existe mais | Local-only; sem deploy |

Observacao sobre o workspace raiz: a pasta `c:\dev\projetos\checkcheck` e simultaneamente o repo de infraestrutura (`origin = checking`) **e** o repo da API (`api = checking-api`). Os dois remotes coexistem no mesmo diretorio Git local. O commit e unico; o destino do push depende de qual remote voce usa.

Repositorios que existem no GitHub, mas sem branch configurada (vazios/legado):

| Repo GitHub | Situacao |
| --- | --- |
| `tscode-com-br/checking_api` | Vazio (criado antes da separacao; substituido por `checking-api` com hifem) |
| `tscode-com-br/checking_transport` | Vazio (substituido por `checking-transport` com hifem) |
| `tscode-com-br/checking_webapplication` | Vazio (substituido por `checking-webapp`) |
| `tscode-com-br/checking_admin` | Vazio (substituido por `checking-admin2`) |

Esses quatro repos legados (com underscore) nao recebem push e nao acionam deploy. Ignore-os.

### 1.1 Modificacoes mapeadas nesta revisao (2026-05-24)

1. **API separada em repositorio proprio**: `tscode-com-br/checking-api` criado e conectado como remote `api` do workspace raiz; workflow `deploy.yml` criado no root com guarda `if: github.repository == 'tscode-com-br/checking-api'`; primeiro deploy completo validado (7m16s, todos os steps ✓).
2. **Check Web e Transport conectados como sub-repos**: `sistema/app/static/check` agora tem `origin = checking-webapp`; `sistema/app/static/transport` tem `origin = checking-transport`; ambos possuem `deploy.yml` proprio.
3. **`.gitignore` do root atualizado**: excluidas as tres pastas de sub-repos estaticos (`admin2/`, `check/`, `transport/` dentro de `sistema/app/static/`) para que nao entrem em commits do root nem do `checking-api`.
4. **`deploy-oceandrive.yml` protegido**: adicionado `if: github.repository == 'tscode-com-br/checking'` para nao executar no `checking-api`.

Consequencias praticas:

- mudancas no codigo Python (API, routers, services, models, alembic) devem ser commitadas no root e publicadas com `git push api main`; o push para `origin` e opcional (mantem espelho de infraestrutura sincronizado);
- mudancas na infra (docker-compose, nginx, deploy scripts, Dockerfile) devem ser commitadas no root e publicadas com `git push origin main`;
- mudancas no frontend Check Web devem ser commitadas em `sistema/app/static/check` e publicadas com `git push origin main` naquela pasta;
- mudancas no frontend Transport devem ser commitadas em `sistema/app/static/transport` e publicadas com `git push origin main` naquela pasta;
- mudancas no frontend Admin v2 devem ser commitadas em `sistema/app/static/admin2` e publicadas com `git push origin main` naquela pasta;
- os sub-repos estaticos sao invisíveis ao root (`.gitignore`); nao misturar commits.

## 2. Regra de ouro

Antes de qualquer commit ou push, responda primeiro:

1. A mudanca pertence ao codigo da API (Python, alembic, modelos, routers)?
2. A mudanca pertence a um dos frontends estaticos (admin2, check, transport)?
3. A mudanca pertence a infra/deploy (docker-compose, nginx, Dockerfiles, workflows)?
4. A mudanca pertence ao app Flutter?

Cada mudanca deve ser commitada apenas no repositorio dono do escopo.

Regra operacional por escopo:

- **API (codigo Python, modelos, services, routers, alembic)**: commit no root (`c:\dev\projetos\checkcheck`) + `git push api main`; opcionalmente `git push origin main` para manter espelho `checking` em sincronia;
- **Infra/deploy (docker-compose, nginx, Dockerfiles, workflows, scripts de deploy)**: commit no root + `git push origin main`; nao aciona deploy automatico — dispare manualmente se necessario via `gh workflow run`;
- **Admin v2**: commit em `sistema\app\static\admin2` + `git push origin main` naquela pasta; deploy automatico acionado;
- **Check Web**: commit em `sistema\app\static\check` + `git push origin main` naquela pasta; deploy automatico acionado;
- **Transport**: commit em `sistema\app\static\transport` + `git push origin main` naquela pasta; deploy automatico acionado;
- **Flutter**: commit em `checking_android_new` + `git push origin main` naquela pasta;
- **Kotlin legado**: commit local em `checking_kotlin`; criar novo `origin` antes de qualquer push;
- **Kotlin novo**: commit local em `checking_kotlin_new`; criar novo `origin` antes de qualquer push;
- nao usar `git subtree`;
- nao tentar publicar apps moveis a partir do root;
- nao misturar arquivos de sub-repos no stage do root.

## 3. Qual repo aciona producao

### 3.1 API — repositorio `checking-api`

Workflow:

- `.github/workflows/deploy.yml` (no root workspace, guarda `if: github.repository == 'tscode-com-br/checking-api'`)

Gatilho:

- `push` em `main` via remote `api`

Imagens geradas:

- `ghcr.io/tscode-com-br/checking-api:<sha>` e `:main`
- `ghcr.io/tscode-com-br/checking-api-forms:<sha>` e `:main`

Compose file usado no servidor:

- `docker-compose.api.yml` (servicos: `db`, `api`, `forms-worker`)

Fluxo de commit/push para alteracoes na API:

```powershell
Set-Location c:\dev\projetos\checkcheck
git add <arquivos-python-ou-alembic>
git commit -m "feat: descricao da mudanca"
git push api main
# deploy automatico disparado em checking-api

# Opcional: manter espelho de infraestrutura sincronizado
git push origin main
```

Para verificar o ultimo deploy da API:

```powershell
gh run list --repo tscode-com-br/checking-api --limit 5
gh run view --repo tscode-com-br/checking-api <run-id>
```

### 3.2 Check Web — repositorio `checking-webapp`

Workflow:

- `.github/workflows/deploy.yml` (dentro de `sistema\app\static\check`)

Gatilho:

- `push` em `main` do repositorio `checking-webapp`

Fluxo de commit/push:

```powershell
Set-Location c:\dev\projetos\checkcheck\sistema\app\static\check
git add .
git commit -m "web: descricao da mudanca"
git push origin main
# deploy automatico disparado em checking-webapp
```

Para verificar:

```powershell
gh run list --repo tscode-com-br/checking-webapp --limit 5
```

### 3.3 Transport — repositorio `checking-transport`

Workflow:

- `.github/workflows/deploy.yml` (dentro de `sistema\app\static\transport`)

Gatilho:

- `push` em `main` do repositorio `checking-transport`

Fluxo de commit/push:

```powershell
Set-Location c:\dev\projetos\checkcheck\sistema\app\static\transport
git add .
git commit -m "transport: descricao da mudanca"
git push origin main
# deploy automatico disparado em checking-transport
```

Para verificar:

```powershell
gh run list --repo tscode-com-br/checking-transport --limit 5
```

### 3.4 Admin v2 — repositorio `checking-admin2`

Workflow:

- `.github/workflows/deploy.yml` (dentro de `sistema\app\static\admin2`)

Gatilho:

- `push` em `main` do repositorio `checking-admin2`

Fluxo de commit/push:

```powershell
Set-Location c:\dev\projetos\checkcheck\sistema\app\static\admin2
git add .
git commit -m "admin2: descricao da mudanca"
git push origin main
# deploy automatico disparado em checking-admin2
```

Para verificar:

```powershell
gh run list --repo tscode-com-br/checking-admin2 --limit 5
```

### 3.5 Infraestrutura — repositorio `checking`

O repositorio `checking` (remote `origin` do root) hospeda configuracoes de infraestrutura: docker-compose files, nginx, Dockerfiles, scripts de deploy e workflows secundarios para deploy individual de cada servico.

Workflows disponiveis (todos em `.github/workflows/`):

| Workflow | Gatilho | Efeito |
| --- | --- | --- |
| `deploy-oceandrive.yml` | `push main` ou `workflow_dispatch` | Deploy completo do stack legado (monolito) |
| `deploy-oceandrive-api-only.yml` | `workflow_dispatch` | Reinicia apenas o servico `api` |
| `deploy-oceandrive-admin2-only.yml` | `workflow_dispatch` | Reinicia apenas o conteiner `admin2-web` |
| `deploy-oceandrive-user-only.yml` | `workflow_dispatch` | Reinicia apenas o conteiner `user-web` |
| `deploy-oceandrive-transport-only.yml` | `workflow_dispatch` | Reinicia apenas o conteiner `transport-web` |

Disparo manual via CLI:

```powershell
gh workflow run deploy-oceandrive-api-only.yml --repo tscode-com-br/checking
gh workflow run deploy-oceandrive-admin2-only.yml --repo tscode-com-br/checking
```

Fluxo de commit/push para alteracoes de infraestrutura:

```powershell
Set-Location c:\dev\projetos\checkcheck
git add docker-compose*.yml deploy\ nginx\ .github\workflows\
git commit -m "infra: descricao da mudanca"
git push origin main
```

## 4. Como confirmar pasta local, branch, remote e existencia no GitHub antes de publicar

### 4.1 API / Infraestrutura (workspace raiz)

```powershell
Set-Location c:\dev\projetos\checkcheck
git branch --show-current      # deve ser: main
git remote -v                  # deve mostrar origin (checking) E api (checking-api)
git status --short
gh repo view tscode-com-br/checking-api
gh repo view tscode-com-br/checking
```

### 4.2 Check Web

```powershell
Set-Location c:\dev\projetos\checkcheck\sistema\app\static\check
git branch --show-current      # deve ser: main
git remote -v                  # deve mostrar: origin = checking-webapp
git status --short
gh repo view tscode-com-br/checking-webapp
```

### 4.3 Transport

```powershell
Set-Location c:\dev\projetos\checkcheck\sistema\app\static\transport
git branch --show-current      # deve ser: main
git remote -v                  # deve mostrar: origin = checking-transport
git status --short
gh repo view tscode-com-br/checking-transport
```

### 4.4 Admin v2

```powershell
Set-Location c:\dev\projetos\checkcheck\sistema\app\static\admin2
git branch --show-current      # deve ser: main
git remote -v                  # deve mostrar: origin = checking-admin2
git log --oneline -5
gh repo view tscode-com-br/checking-admin2
```

Obs.: a pasta `sistema/app/static/admin2` e um repositorio Git aninhado dentro do root. O `.gitignore` do root exclui essa pasta. Verifique:

```powershell
git -C c:\dev\projetos\checkcheck check-ignore -v sistema/app/static/admin2
```

### 4.5 Flutter

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git branch --show-current
git remote -v
git status --short
gh repo view tscode-com-br/checking_app_flutter
```

### 4.6 Kotlin legado local

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git branch -vv
git remote -v
git status --short
```

Resultado esperado:

- aparece `archived-origin`, nao `origin`;
- a branch `main` aparece sem `[remote/branch]` ao lado;
- `gh repo view tscode-com-br/checking_app_kotlin` falha — repositorio nao existe mais.

### 4.7 Kotlin novo local

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git branch -vv
git remote -v
git status --short
```

Resultado esperado:

- aparece `archived-origin`, nao `origin`;
- a branch local confirmada e `web-parity-spa-baseline`;
- `gh repo view tscode-com-br/checking_kotlin_new` falha — repositorio nao existe mais.

## 5. Repositorios GitHub confirmados hoje

Repositorios ativos (possuem branch `main` configurada):

| Repo | Visibilidade | Ligacao local |
| --- | --- | --- |
| `tscode-com-br/checking` | publico | remote `origin` do root |
| `tscode-com-br/checking-api` | publico | remote `api` do root |
| `tscode-com-br/checking-webapp` | publico | remote `origin` de `sistema/app/static/check` |
| `tscode-com-br/checking-admin2` | privado | remote `origin` de `sistema/app/static/admin2` |
| `tscode-com-br/checking-transport` | publico | remote `origin` de `sistema/app/static/transport` |
| `tscode-com-br/checking_app_flutter` | publico | remote `origin` de `checking_android_new` |

Repositorios vazios / legados (sem branch; nao usar):

- `tscode-com-br/checking_api` (substituido por `checking-api`)
- `tscode-com-br/checking_transport` (substituido por `checking-transport`)
- `tscode-com-br/checking_webapplication` (substituido por `checking-webapp`)
- `tscode-com-br/checking_admin` (substituido por `checking-admin2`)

Remotes locais mortos (sem repo correspondente no GitHub):

- `checking_kotlin: archived-origin = https://github.com/tscode-com-br/checking_app_kotlin.git`
- `checking_kotlin_new: archived-origin = https://github.com/tscode-com-br/checking_kotlin_new.git`

Comando de auditoria rapida:

```powershell
gh repo list tscode-com-br --limit 20 --json name,defaultBranchRef,isPrivate |
  ConvertFrom-Json |
  Format-Table name, @{n='branch';e={$_.defaultBranchRef.name}}, isPrivate -AutoSize
```

Se um novo repositorio GitHub for criado para qualquer app Kotlin, a reativacao recomendada e:

```powershell
Set-Location <pasta-do-repo-kotlin>
git remote remove archived-origin
git remote add origin <novo-url-github>
git push -u origin <branch-atual>
```

## 6. Pre-condicoes antes de qualquer push

Checklist minimo:

1. pasta correta;
2. branch correta;
3. remote correto e existente no GitHub;
4. para o workspace raiz: identificar se o push vai para `origin` (infra) ou `api` (API) ou ambos;
5. stage apenas do escopo desejado (nao misturar Python + frontend + infra num so commit);
6. testes relevantes executados;
7. ausencia de `.env`, chaves, bancos locais e artefatos de build no commit.

Comandos uteis:

```powershell
git branch --show-current
git branch -vv
git remote -v
git status --short
git diff --cached --stat
gh repo list tscode-com-br --limit 20
```

Regra adicional importante:

- se o `gh repo view` do remote falhar, nao tente `git push` antes de criar um novo repositorio ou apontar o remote para um destino valido;
- se existir apenas `archived-origin`, trate o repositorio como local-only ate a criacao de um novo `origin`;
- os repos com underscore (`checking_api`, `checking_transport`, `checking_webapplication`, `checking_admin`) sao legados vazios — nao confundir com os repos ativos de mesmo escopo com hifem.

## 7. Como fazer commit e push em cada repositorio

As sequencias abaixo assumem PowerShell no Windows e stage explicito por arquivo ou pasta.

Regra importante:

- no root, prefira `git add <arquivos>` em vez de `git add .` quando houver outras mudancas locais nao relacionadas;
- nos repositorios Kotlin, o commit local funciona hoje, mas o push depende primeiro de recriar um `origin` valido.

### 7.1 Sistema principal `checkcheck`

Quando usar:

- API
- transport
- admin
- webapplication
- websites do sistema
- deploy
- documentacao do repo principal
- qualquer area que ainda nao tenha sido fisicamente extraida para `checking_api`, `checking_transport`, `checking_webapplication` ou `checking_admin`

Fluxo recomendado:

```powershell
Set-Location c:\dev\projetos\checkcheck
git status --short
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
git push origin main
```

Observacoes:

- `git push origin main` neste repo aciona o deploy de producao;
- a existencia dos repositorios `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin` no GitHub nao transfere ownership automaticamente para fora do root;
- se houver outros arquivos modificados no root e eles nao fizerem parte da entrega, nao use `git add .`.

### 7.2 App Flutter `checking_android_new`

Quando usar:

- app Flutter
- testes Flutter
- assets e configuracoes do projeto Flutter

Fluxo recomendado:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git status --short
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking_app_flutter

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
git push origin main
```

Observacoes:

- este push publica apenas o repositorio Flutter;
- ele nao aciona o deploy da API nem do website principal.

### 7.3 Repositorios GitHub criados para particionamento futuro

Estado atual:

- `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin` existem no GitHub;
- nenhum deles possui hoje pasta Git dedicada nem `origin` configurado neste workspace;
- portanto, ainda nao existe fluxo direto de `git add`/`git commit`/`git push` para esses repositorios a partir da arvore atual.

Regra pratica:

1. enquanto o codigo continuar dentro de `c:\dev\projetos\checkcheck`, o dono operacional continua sendo o root `checkcheck`;
2. a independencia de commit/push so comeca quando o escopo for realmente extraido para uma pasta Git propria;
3. criar o repo no GitHub foi apenas a primeira metade do isolamento; a segunda metade e mover o codigo e ligar o remote certo.

Fluxo recomendado para ativar qualquer um desses repositorios no futuro:

1. criar ou clonar a pasta Git dedicada fora do root atual;
2. mover apenas o escopo daquele repositorio para a nova pasta;
3. configurar `origin` para o repo GitHub correspondente;
4. fazer o primeiro commit/push nesse repo novo;
5. remover do root a ownership operacional daquele escopo para evitar duplicidade.

### 7.4 App Kotlin legado `checking_kotlin`

Estado atual:

- branch local confirmada: `main`
- remote ativo de publicacao: inexistente
- remote historico preservado: `archived-origin`

Commit local hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git status --short
git branch -vv
git remote -v

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
```

Push so depois de recriar `origin`:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin main
```

Observacoes:

- nao tente `git push origin main` antes de recriar `origin`;
- se quiser manter o remote historico apenas como referencia, renomeie em vez de apagar e adapte o comando acima.

### 7.5 App Kotlin novo `checking_kotlin_new`

Estado atual:

- branch local confirmada: `web-parity-spa-baseline`
- remote ativo de publicacao: inexistente
- remote historico preservado: `archived-origin`

Commit local hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git status --short
git branch -vv
git remote -v

git add <arquivo-ou-pasta>
git commit -m "<mensagem>"
```

Push so depois de recriar `origin`:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin web-parity-spa-baseline
```

Observacoes:

- nao trocar a branch por `main` sem confirmar antes o fluxo desejado;
- hoje o caminho seguro e tratar esse repo como local-only ate existir um novo repositorio GitHub.

## 8. O que nao deve entrar em commit

Itens normalmente excluidos:

- `.env`
- `.venv/`
- `deploy/keys/`
- arquivos `*.db`, `*.sqlite`, `*.sqlite3`
- artefatos de build
- caches locais
- qualquer arquivo de repositorio aninhado quando voce estiver no root

## 9. Dono de GitHub Actions e Secrets

O dono operacional de GitHub Actions e Secrets do deploy e o repo principal `checkcheck`.

Estado confirmado no ambiente atual:

- a conta autenticada `tscode-com-br` no GitHub CLI tem permissao `admin` no repo `tscode-com-br/checking`;
- o endpoint `repos/tscode-com-br/checking/actions/secrets/public-key` responde corretamente;
- a leitura da lista de secrets do deploy esta funcionando.

Isso nao muda a regra de escopo:

- Actions e Secrets de deploy pertencem ao repo principal;
- o app Flutter continua fora do fluxo de deploy da DigitalOcean;
- as pastas Kotlin locais nao controlam deploy, nao tem `origin` ativo e hoje tambem nao possuem repositorio GitHub correspondente confirmado.

## 10. Playbook detalhado para quando um agente de IA for fazer commit, push e acompanhar deploy

As secoes anteriores explicam quem e o dono de cada repositorio.

Esta secao nova define o comportamento operacional esperado quando o pedido ao agente de IA incluir explicitamente:

- fazer commit;
- fazer push;
- acompanhar o deploy;
- validar se a publicacao terminou bem.

Regra principal:

- no repo principal, push em `main` e operacao sensivel de producao;
- no repo Flutter, push publica apenas o app Flutter;
- nos repositorios GitHub-only `checking_api`, `checking_transport`, `checking_webapplication` e `checking_admin`, o playbook so passa a valer como repo independente depois que existir pasta Git local propria e o codigo daquele escopo sair do root;
- nos repositorios Kotlin locais, commit local ainda e valido, mas push continua bloqueado ate existir um `origin` real.

### 10.1 Sequencia obrigatoria antes de qualquer stage

Quando um agente de IA receber pedido de commit/push, ele deve comecar sempre pela auditoria abaixo no repositorio correto.

#### Sistema principal

```powershell
Set-Location c:\dev\projetos\checkcheck
git status -sb
git branch --show-current
git remote -v
git diff --stat
git diff --cached --stat
gh repo view tscode-com-br/checking
```

#### Flutter

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git status -sb
git branch --show-current
git remote -v
git diff --stat
git diff --cached --stat
gh repo view tscode-com-br/checking_app_flutter
```

#### Kotlin legado local-only

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git status -sb
git branch -vv
git remote -v
git diff --stat
git diff --cached --stat
```

#### Kotlin novo local-only

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git status -sb
git branch -vv
git remote -v
git diff --stat
git diff --cached --stat
```

Saida esperada antes de prosseguir:

1. a pasta atual e o repo dono da mudanca;
2. a branch atual foi confirmada e nao esta sendo assumida por memoria;
3. o `origin` existe quando houver intencao de push;
4. o `archived-origin` isolado continua sendo tratado como local-only;
5. o agente ja sabe quais arquivos mudaram antes de adicionar qualquer coisa ao stage.

### 10.2 Situacoes em que o agente deve parar antes do push

O agente nao deve improvisar push se qualquer um dos pontos abaixo acontecer:

1. a mudanca esta no repo errado;
2. existe mistura de arquivos do root com arquivos de repositorios aninhados;
3. o `gh repo view` falha para um destino que deveria receber push;
4. o repositorio esta local-only e ainda nao existe `origin` valido;
5. ha alteracoes locais nao relacionadas que o usuario nao pediu para publicar;
6. testes relevantes ainda nao foram rodados;
7. a entrega depende tambem de `.env`, secret do GitHub, dado manual de banco ou alteracao de host e isso ainda nao foi tratado.

Em qualquer uma dessas situacoes, o comportamento certo e resolver a pendencia primeiro ou informar claramente que commit/push sozinho nao fecha a entrega.

O mesmo bloqueio vale quando o repo ja existe no GitHub, mas o workspace ainda nao possui checkout Git dedicado para ele.

### 10.3 Como o agente deve montar o stage

Regra geral:

- preferir `git add <arquivo>` ou `git add <pasta-especifica>`;
- evitar `git add .` no root sempre que houver qualquer risco de capturar mudancas nao relacionadas;
- conferir o stage antes do commit;
- conferir tambem os untracked files para garantir que nenhum artefato local entrou por engano.

Sequencia recomendada:

```powershell
git status --short
git add <arquivo-ou-pasta>
git status --short
git diff --cached --stat
git diff --cached
```

Conferencia minima esperada:

1. so os arquivos da entrega aparecem staged;
2. nada de `.env`, `deploy/keys/`, `*.db`, cache, build output ou repositorio aninhado entrou no commit;
3. a diff staged bate com a explicacao funcional da entrega;
4. se houver mudanca de deploy ou infraestrutura, ela foi revisada com mais cuidado do que uma mudanca comum de app.

### 10.4 Como o agente deve escolher a mensagem de commit

A mensagem de commit deve ser curta, especifica e alinhada ao efeito real do change set.

Padrao recomendado:

- usar verbo de acao;
- mencionar o escopo principal;
- evitar mensagens vagas como `update`, `fixes`, `changes` ou `ajustes` sem contexto.

Exemplos bons:

```text
fix(transport-ai): corrige indices da matrix do Mapbox
docs(github): detalha fluxo de commit push e deploy
fix(admin): preserva scroll no refresh automatico
```

Fluxo de commit:

```powershell
git commit -m "<mensagem>"
git rev-parse HEAD
```

O `git rev-parse HEAD` deve ser guardado no relatorio final do agente para facilitar rastreio do deploy.

### 10.5 Como o push deve acontecer em cada repo

#### Sistema principal `checkcheck`

Use apenas quando a mudanca pertence ao repo root e o usuario quer publicar no repo principal.

Fluxo detalhado:

```powershell
Set-Location c:\dev\projetos\checkcheck
git status -sb
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
git push origin main
```

Observacoes obrigatorias:

1. `git push origin main` neste repo aciona o workflow de deploy de producao;
2. se a branch atual nao for `main`, o agente nao deve afirmar que houve deploy automatico de producao so porque houve push;
3. se o agente estiver em branch diferente e o pedido do usuario for acompanhar deploy de producao, ele precisa deixar claro que o deploy automatico depende do update em `main`;
4. se existir sujeira nao relacionada no root, o stage deve continuar explicito por arquivo.

#### Flutter `checking_android_new`

Fluxo detalhado:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_android_new
git status -sb
git branch --show-current
git remote -v
gh repo view tscode-com-br/checking_app_flutter
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
git push origin main
```

Observacoes obrigatorias:

1. esse push nao faz deploy da API;
2. esse push nao publica websites do sistema principal;
3. o agente nao deve prometer deploy na DigitalOcean ao publicar o repo Flutter.

#### Kotlin legado `checking_kotlin`

Fluxo detalhado hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin
git status -sb
git branch -vv
git remote -v
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
```

Push so depois de recriar `origin`:

```powershell
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin main
```

#### Kotlin novo `checking_kotlin_new`

Fluxo detalhado hoje:

```powershell
Set-Location c:\dev\projetos\checkcheck\checking_kotlin_new
git status -sb
git branch -vv
git remote -v
git diff --cached --stat
git commit -m "<mensagem>"
git rev-parse HEAD
```

Push so depois de recriar `origin`:

```powershell
git remote remove archived-origin
git remote add origin <novo-url-github>
gh repo view <owner>/<repo>
git push -u origin web-parity-spa-baseline
```

### 10.6 O que o agente deve fazer imediatamente depois do push no repo principal

No repo principal, o trabalho nao termina no `git push origin main`.

O agente deve acompanhar o workflow de producao ate conclusao ou falha clara.

Sequencia recomendada:

```powershell
Set-Location c:\dev\projetos\checkcheck
gh run list --workflow deploy-oceandrive.yml --limit 5
gh run watch <run-id> --exit-status
gh run view <run-id> --log-failed
```

Comportamento esperado:

1. identificar o run disparado pelo commit enviado;
2. acompanhar o workflow ate `success` ou `failure`;
3. se falhar, capturar o passo exato que falhou e os logs relevantes;
4. se passar, validar a saude publica antes de encerrar o trabalho.

O agente nao deve parar logo apos o push dizendo apenas que o deploy foi "disparado".

O encerramento correto para o repo principal exige pelo menos:

1. SHA do commit enviado;
2. id ou URL do run do GitHub Actions;
3. conclusao do run;
4. resultado da validacao de health.

### 10.7 Como validar o deploy depois do Actions verde

Validacao minima do sistema principal:

```powershell
curl.exe -fsS https://tscode.com.br/api/health
```

Se houver necessidade de confirmacao no host:

```powershell
ssh -i .\deploy\keys\do_checkcheck root@157.230.35.21 "curl -fsS http://127.0.0.1:8000/api/health"
```

Se a entrega afetar uma funcionalidade critica, o agente deve fazer tambem uma validacao funcional focada, nao apenas o health.

Exemplos:

- rota HTTP especifica da feature alterada;
- smoke de autenticacao;
- fluxo do Transport AI, quando a entrega mexer nele;
- pagina publica impactada pela mudanca.

Regra importante:

- health verde prova que a aplicacao subiu;
- health verde sozinho nao prova que a funcionalidade alterada ficou correta.

## 11. O que o deploy principal realmente faz no repo root

O fluxo de producao confirmado em `.github/workflows/deploy-oceandrive.yml` faz hoje, em linhas gerais:

1. checkout do repo;
2. build e push da imagem `ghcr.io/tscode-com-br/checkcheck-app:<sha>`;
3. criacao do diretorio remoto;
4. remocao no host de `checking_android_new`, `checking_kotlin` e `checking_kotlin_new` legados;
5. `rsync --delete` do projeto para o host;
6. materializacao do `.env` a partir do secret `OCEAN_APP_ENV_B64`, se esse secret estiver preenchido;
7. pull da imagem no host;
8. migracao do banco;
9. restart do `app`;
10. validacao de health local e publica;
11. limpeza de residuos de deploy e guarda de SSD.

Consequencias praticas para qualquer agente de IA:

1. arquivo apagado do repo pode ser apagado no host por causa do `rsync --delete`;
2. `.env` nao vai pelo `rsync`;
3. se `OCEAN_APP_ENV_B64` estiver configurado, o `.env` do host pode ser sobrescrito no deploy;
4. push de codigo nao garante, sozinho, que uma mudanca manual de ambiente sera preservada;
5. o deploy principal e sensivel e deve ser tratado como publicacao de producao real.

## 12. O que commit e push NAO levam sozinhos para producao

Mesmo com commit correto e Actions verde, ha classes de mudanca que nao sao cobertas apenas pelo push do repo.

### 12.1 Ajustes de `.env` e secrets

Esses itens nao devem ser tratados como automaticamente resolvidos por commit/push:

- `.env` local;
- secret `OCEAN_APP_ENV_B64`;
- quaisquer secrets do GitHub Actions;
- qualquer valor configurado manualmente so no host.

Exemplos reais sensiveis neste projeto:

- `MAPBOX_ACCESS_TOKEN`;
- `TRANSPORT_AI_SETTINGS_ENCRYPTION_KEY`;
- `TRANSPORT_AI_AGENT_MODE`;
- `TRANSPORT_AI_OPERATIONAL_APPROVAL_EVIDENCE`.

Se uma entrega depende de um desses valores, o agente deve dizer explicitamente no relatorio final se:

1. o valor ja estava sincronizado no secret/fonte de verdade;
2. o valor foi alterado somente no host;
3. o deploy seguinte pode sobrescrever o ajuste.

### 12.2 Ajustes de banco e dados operacionais

O deploy normal preserva o banco porque o Postgres usa volume persistente, mas commit/push nao recria automaticamente uma correcao de dado feita manualmente em producao.

Exemplos:

- correcoes em linhas da tabela `projects`;
- backfills manuais;
- limpeza de dados inconsistentes;
- mudancas em tabelas de configuracao operacional.

Regra esperada do agente:

1. se a entrega depender de dado ajustado manualmente, registrar isso;
2. se possivel, codificar a correcao em migration, seed controlado ou script de saneamento;
3. nao afirmar que "o deploy sozinho resolve" algo que na verdade ainda depende do estado atual do banco.

### 12.3 Ajustes de host e infraestrutura

Esses pontos tambem nao devem ser confundidos com commit/push simples:

- nginx editado manualmente no droplet;
- unit file do systemd;
- arquivos fora do diretorio do app;
- manutencao manual de volumes, caches ou backups.

## 13. Checklists operacionais para agentes de IA

### 13.1 Checklist minimo antes do commit

1. confirmar repo correto;
2. confirmar branch correta;
3. confirmar remote correto;
4. revisar `git status -sb`;
5. revisar `git diff --stat`;
6. rodar testes relevantes;
7. stage explicito apenas dos arquivos desejados;
8. revisar `git diff --cached --stat`;
9. garantir que nenhum artefato local entrou no commit.

### 13.2 Checklist minimo antes do push no root

1. o usuario realmente pediu publicacao no repo principal;
2. o commit staged e o commit final batem com a entrega esperada;
3. `git push origin main` foi entendido como deploy de producao;
4. nao ha dependencia oculta de `.env`, secret ou dado manual nao mencionada;
5. o agente sabe qual validacao funcional devera executar depois do Actions verde.

### 13.3 Checklist minimo depois do push no root

1. obter o `run-id` do workflow;
2. acompanhar o workflow ate terminar;
3. se falhar, coletar o passo e o log;
4. se passar, validar `https://tscode.com.br/api/health`;
5. se a feature exigir, validar tambem o fluxo funcional alterado;
6. relatar SHA, run, resultado e qualquer pendencia de ambiente ou dados.

## 14. Prompt recomendado quando voce pedir a um agente de IA para fazer commit, push e acompanhar deploy

Se quiser maximizar a chance de um agente executar corretamente, use um pedido proximo deste modelo:

```text
Trabalhe apenas no repositorio dono desta mudanca.
Antes de commitar, audite pasta atual, branch, remote, arquivos modificados e arquivos staged.
Faca stage explicito apenas dos arquivos desta entrega.
Nao use git add . no repo root se houver qualquer outro arquivo modificado fora do escopo.
Rode os testes relevantes antes do commit.
Depois faca o commit com mensagem especifica.
Se for o repo principal, faca push em main somente se a entrega estiver pronta para deploy de producao.
Depois acompanhe o workflow deploy-oceandrive.yml ate o fim.
Valide https://tscode.com.br/api/health e, se a feature exigir, rode tambem uma validacao funcional focada.
No final, me informe: repo, branch, SHA, arquivos commitados, run-id ou URL do Actions, resultado do deploy e qualquer ajuste que ainda dependa de .env, secret ou banco.
```

Complemento importante para pedidos envolvendo Transport AI:

```text
Se a entrega depender de configuracao de ambiente, secret ou dado manual de producao, nao trate commit/push como suficiente. Diga explicitamente o que ficou fora do Git e o que precisa ser sincronizado para o proximo deploy nao reverter o comportamento.
```

## 15. Regras criticas aprendidas na pratica sobre GitHub Actions neste repositorio

Esta secao documenta armadilhas reais que quebraram o pipeline de producao e que nao sao obvias lendo a documentacao oficial do GitHub Actions.

### 15.1 NUNCA use `secrets.*` diretamente em condicoes `if:` de steps

**Regra:**

```yaml
# ERRADO — o GitHub Actions nao avalia secrets em condicoes if:
- name: Meu step
  if: ${{ secrets.MINHA_VARIAVEL != '' }}

# CERTO — exponha o secret como env var e verifique a env var
- name: Meu step
  env:
    MINHA_VARIAVEL: ${{ secrets.MINHA_VARIAVEL }}
  if: env.MINHA_VARIAVEL != ''
```

**Por que isso importa:**

Quando um step usa `secrets.*` diretamente em `if:`, o GitHub Actions falha ao parsear o workflow
inteiro. O resultado e um run com duracao de `0s` e a mensagem "This run likely failed because of a
workflow file issue". Nenhum job e executado, nenhum log e gerado, e o erro e silencioso.

Isso aconteceu com o step "Apply nginx edge routes" em `deploy-oceandrive.yml` em 2026-05-11.
A consequencia foi que TODOS os deploys falharam silenciosamente por horas sem que nenhum passo
chegasse a rodar.

**Como identificar esse problema:**

```powershell
gh run list --workflow deploy-oceandrive.yml --limit 5
```

Se a coluna de duracao mostrar `0s` para varios runs consecutivos, e o `gh run view <id>` mostrar
"This run likely failed because of a workflow file issue" com `total_count: 0` jobs, e um erro de
parse YAML no workflow — nao um erro de execucao.

**Regra para uso de secrets dentro de `script:` de steps:**

Dentro do campo `script:` de um step que usa `uses: appleboy/ssh-action`, secrets podem ser
referenciados normalmente via `${{ secrets.X }}`. O problema ocorre APENAS no campo `if:`.

Se voce precisar usar o secret tanto no `if:` quanto no `script:`, declare-o como env var e use
`${{ env.X }}` nos dois lugares:

```yaml
- name: Aplica nginx
  env:
    OCEAN_NGINX_SERVER_CONFIG: ${{ secrets.OCEAN_NGINX_SERVER_CONFIG }}
  if: env.OCEAN_NGINX_SERVER_CONFIG != ''
  uses: appleboy/ssh-action@...
  with:
    script: |
      bash manage.sh --server-config '${{ env.OCEAN_NGINX_SERVER_CONFIG }}'
```

### 15.2 O deploy agora aplica nginx automaticamente se o secret estiver configurado

O step "Apply nginx edge routes" foi adicionado em `deploy-oceandrive.yml` (entre "Start application
runtime" e "Snapshot disk usage after restart"). Ele roda apenas quando o secret
`OCEAN_NGINX_SERVER_CONFIG` esta preenchido.

**O que o step faz:**

1. executa `manage_checking_edge_cutover.sh apply` no host remoto;
2. aplica o conteudo de `deploy/nginx/checking-edge-routes.conf` dentro do bloco
   `# BEGIN CHECKCHECK EDGE ROUTES` / `# END CHECKCHECK EDGE ROUTES` do arquivo nginx;
3. roda `nginx -t` para validar;
4. recarrega nginx com `systemctl reload nginx`.

**Estado atual do secret:**

| Secret | Valor atual | Funcao |
|---|---|---|
| `OCEAN_NGINX_SERVER_CONFIG` | `/etc/nginx/sites-enabled/checkcheck` | Caminho do arquivo de configuracao nginx do servidor que serve `tscode.com.br` |

**Consequencia pratica:**

Qualquer alteracao em `deploy/nginx/checking-edge-routes.conf` e automaticamente aplicada no
proximo deploy, sem necessidade de workflow manual separado. O reload do nginx faz parte do
fluxo de deploy normal.

### 15.3 Backups do nginx nunca devem ficar em `sites-enabled/`

O script `deploy/nginx/manage_checking_edge_cutover.sh` cria um backup do arquivo de configuracao
antes de modificar. O backup padrao fica em `/tmp/`, NAO no mesmo diretorio do arquivo original.

**Por que isso importa:**

nginx carrega todos os arquivos dentro de `sites-enabled/` sem excecao, incluindo arquivos `.bak`.
Se um backup como `checkcheck.bak.20260511082439` for criado dentro de `sites-enabled/`, nginx
detectara um `default_server` duplicado e recusara recarregar, com erro:

```
[emerg] a duplicate default server for 0.0.0.0:80 in
/etc/nginx/sites-enabled/checkcheck.bak.20260511082439:2
nginx: configuration file /etc/nginx/nginx.conf test failed
```

O script ja foi corrigido para usar `/tmp/nginx-<nome>.bak.<timestamp>` como destino padrao.
Nao reverter esse comportamento.

### 15.4 Como diagnosticar um deploy que falhou em 0 segundos

Sequencia de diagnostico quando o run aparece com `0s`:

```powershell
# 1. Verificar se jobs foram criados
gh api repos/tscode-com-br/checking/actions/runs/<run-id>/jobs --jq '.total_count'
# Se retornar 0, e erro de parse do workflow

# 2. Tentar obter logs (vai falhar com "log not found" se for erro de parse)
gh run view <run-id> --log-failed

# 3. Validar o YAML do workflow localmente antes de commitar
# (GitHub Actions nao tem validator CLI oficial, mas o erro mais comum
#  e secrets.* em condicoes if: — revise todos os steps com if: no arquivo)
```

### 15.5 Fluxo do deploy atualizado (maio 2026)

O fluxo atual do `deploy-oceandrive.yml`, na ordem de execucao, inclui agora o step de nginx:

1. Checkout do repositorio
2. Build e push da imagem Docker para `ghcr.io/tscode-com-br/checkcheck-app:<sha>`
3. Verificacao de fingerprint SSH do host
4. Criacao do diretorio remoto
5. Remocao de diretorios legados (`checking_android_new`, `checking_kotlin`, `checking_kotlin_new`)
6. `rsync --delete` do projeto para o host (inclui `deploy/nginx/checking-edge-routes.conf`)
7. Preflight de disco (limpeza e verificacao de espaco livre)
8. Snapshot de disco antes do restart
9. Materializacao do `.env` a partir do secret `OCEAN_APP_ENV_B64`
10. Pull da imagem no host
11. Migracao do banco (`alembic upgrade head`)
12. Start do runtime (`docker compose up`)
13. **[NOVO] Apply nginx edge routes** (se `OCEAN_NGINX_SERVER_CONFIG` estiver configurado)
14. Snapshot de disco depois do restart
15. Validacao de health local
16. Validacao de health publica (`https://tscode.com.br/api/health`)
17. Marcacao do release
18. Instalacao do SSD cleanup automation
19. Execucao do SSD cleanup
20. Verificacao de residuos de deploy