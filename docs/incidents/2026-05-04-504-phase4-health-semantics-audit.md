# Auditoria da semantica de saude da aplicacao - Fase 4 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado como auditoria e proposta tecnica.
- Tipo desta etapa: leitura e definicao de semantica; sem alteracao de runtime nesta execucao.
- Objetivo desta etapa: redefinir com clareza o que significa `liveness`, `readiness` e `degraded` para a API, auditando o endpoint atual `/api/health`, o healthcheck do compose, o startup real e as dependencias que de fato precisam estar saudaveis para o app receber trafego util.

## 2. Objetivo executado

Foi auditado o comportamento atual de:

1. `GET /api/health` em `sistema/app/routers/health.py`;
2. o healthcheck do `app` em `docker-compose.yml`;
3. o healthcheck do `api` em `docker-compose.api.yml`;
4. o startup real do backend em `sistema/app/http_runtime.py`;
5. o lifecycle da aplicacao em `sistema/app/main.py`;
6. os sinais ja existentes de fila do Forms e banco em `sistema/app/services/forms_queue.py` e `sistema/app/database.py`.

## 3. Hipotese ou risco atacado

Hipotese central desta etapa:

- o `/api/health` atual representa apenas que um worker HTTP conseguiu responder, mas nao representa com fidelidade se a aplicacao esta apta a receber trafego util nem separa degradacao parcial de indisponibilidade real.

Risco operacional atacado:

- continuar usando um endpoint binario e raso para tudo mistura tres estados diferentes:
  1. processo vivo;
  2. API realmente pronta para trafego;
  3. plataforma funcional, mas degradada em componentes nao binarios, como worker do Forms, fila, pressao do banco ou barramento realtime.

## 4. Auditoria do estado atual

## 4.1 O que `/api/health` mede hoje

Hoje `GET /api/health` retorna apenas:

```json
{
  "status": "ok",
  "app": "checking-sistema"
}
```

Consequencias objetivas:

1. nao verifica conectividade com o banco;
2. nao verifica se o schema ficou pronto apos `alembic upgrade head`;
3. nao verifica saude do barramento realtime cross-worker;
4. nao verifica fila do Forms, backlog nem worker separado;
5. nao distingue `ok` de `degraded`.

Conclusao:

- hoje `/api/health` equivale, na pratica, a um `process is answering HTTP`, e nao a um readiness real da aplicacao.

## 4.2 Como o compose usa esse endpoint hoje

Tanto `docker-compose.yml` quanto `docker-compose.api.yml` usam o mesmo healthcheck para o container HTTP:

```sh
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)"
```

Parametros atuais:

- `interval: 20s`
- `timeout: 10s`
- `retries: 6`
- `start_period: 30s`

Conclusao:

- o compose hoje trata `/api/health` como um sinal binario de saude do container HTTP, mesmo que esse endpoint ainda nao meca readiness real.

## 4.3 O que o startup real faz antes de o app aceitar trafego

O processo HTTP nao sobe direto em `uvicorn` puro. Hoje o startup versionado e:

1. `python -m sistema.app.http_runtime`;
2. esse entrypoint roda `python -m alembic upgrade head`;
3. so depois faz `exec` para `gunicorn` com workers ASGI do Uvicorn.

Dentro do `lifespan` de `sistema/app/main.py`, cada worker ainda executa:

1. `ensure_event_archives_dir()`;
2. `seed_default_projects()`;
3. `seed_default_admin()`;
4. `start_realtime_brokers()`.

Conclusao:

- o app ja depende, na pratica, de preflight de migracao, acesso ao banco e inicializacao do lifecycle antes de responder requests;
- porem o health atual nao expõe isso como contrato operacional claro.

## 4.4 Componentes que ja tem health ou diagnostico proprio

### A. Worker separado do Forms

Ja existe health proprio do worker em:

- `python -m sistema.app.forms_worker_healthcheck`

Esse check consulta:

- `running`
- `stale`
- `heartbeat_age_seconds`
- `consecutive_error_count`
- `restart_count`

Conclusao:

- o worker do Forms ja e um componente separado e nao deve voltar a ser tratado como pre-requisito binario do HTTP.

### B. Diagnostico do banco

Ja existem helpers internos e endpoint admin autenticado para:

- pool;
- saturacao;
- latencia recente;
- conexoes ativas e em espera no Postgres.

Conclusao:

- o backend ja sabe medir sinais de degradacao do banco; falta apenas encaixar parte disso na semantica publica de saude sem expor dados sensiveis demais.

## 5. Dependencias essenciais da API

## 5.1 O que e indispensavel para `liveness`

Para `liveness`, a API so precisa provar que o processo atual esta vivo o suficiente para responder um request simples.

Isso inclui apenas:

1. processo Python vivo;
2. loop ASGI capaz de atender uma rota;
3. serializacao minima da resposta.

Isso nao deve depender de:

1. query no banco;
2. worker do Forms;
3. broker realtime;
4. backlog da fila;
5. checks de filesystem mais pesados.

Justificativa:

- `liveness` serve para detectar processo travado ou morto, nao para dizer se o sistema inteiro esta operacionalmente perfeito.

## 5.2 O que e indispensavel para `readiness`

Para `readiness`, a API precisa provar que esta apta a receber trafego util agora, sem depender de componentes opcionais ou laterais.

Dependencias indispensaveis propostas:

1. o startup preflight do runtime ja terminou;
2. o worker HTTP atual completou o `lifespan` e consegue responder requests;
3. o banco esta acessivel e aceita ao menos uma consulta leve;
4. se a topologia atual espera servir os sites estaticos dentro da propria API, os diretorios exigidos por `SERVE_ADMIN_SITE_IN_API`, `SERVE_USER_SITE_IN_API` e `SERVE_TRANSPORT_SITE_IN_API` precisam existir.

Interpretacao pratica:

- sem banco, a maior parte das rotas quentes do sistema deixa de ser util;
- sem preflight concluido, a versao de schema e o runtime ainda nao estao prontos;
- sem os sites estaticos, quando esta API tambem for responsavel por `/admin`, `/user` e `/transport`, a aplicacao nao esta pronta para a topologia monolitica;
- o worker do Forms nao entra aqui porque foi explicitamente desacoplado do caminho critico HTTP.

## 5.3 O que deve ser tratado como `degraded`, nao como `not ready`

Estados de degradacao propostos:

1. worker do Forms habilitado, mas `unhealthy`;
2. backlog do Forms acima dos thresholds operacionais definidos na Fase 1;
3. banco acessivel, mas com sinais de pressao relevante, como `pool.usage_ratio` em `warning`, `recent_p95_query_ms` alto ou conexoes esperando;
4. listener do barramento realtime em estado ruim no modo PostgreSQL multiworker;
5. diretorio de arquivos operacionais ou snapshots do worker com falha de escrita, sem quebrar o request path principal;
6. qualquer componente nao binario cuja falha nao justifique retirar todo o HTTP do ar imediatamente.

Justificativa:

- se esses estados derrubarem o readiness binario do container, o sistema pode retirar trafego ou estimular restarts cegos mesmo quando o HTTP principal ainda esta util para as rotas criticas;
- `degraded` precisa virar sinal operacional forte, mas nao o mesmo que `not ready`.

## 6. Modelo proposto de semantica

## 6.1 `GET /api/health/live`

Objetivo:

- provar apenas que o worker HTTP atual esta vivo.

Contrato proposto:

- responder `200` se o processo consegue atender a rota;
- nao tocar banco, fila, broker ou filesystem externo;
- payload pequeno, sem diagnostico pesado.

Uso correto:

- debug local;
- futura semantica de `liveness` para orquestradores que suportem probes separados.

## 6.2 `GET /api/health/ready`

Objetivo:

- provar se este processo HTTP esta apto a receber trafego util agora.

Contrato proposto:

- responder `200` quando todos os requisitos indispensaveis de readiness estiverem `ok`;
- responder `503` quando qualquer requisito indispensavel falhar.

Checks minimos propostos:

1. `database`: `SELECT 1` ou equivalente leve usando a configuracao real atual;
2. `startup_preflight`: refletido implicitamente pelo fato de o runtime so bindar depois de `alembic upgrade head`, mas exposto no payload como estado conhecido do processo;
3. `static_sites`: check condicional apenas quando a API estiver configurada para servir as superficies web diretamente.

Uso correto:

- healthcheck binario do container HTTP no compose;
- gate de entrada de trafego;
- criterio de indisponibilidade real da API.

## 6.3 `GET /api/health`

Objetivo:

- entregar um resumo operacional da saude da aplicacao, incluindo `ok`, `degraded` ou `unready`.

Contrato proposto:

- `200` quando `overall_status` for `ok` ou `degraded`;
- `503` quando `overall_status` for `unready`.

Estado agregado proposto:

1. `ok`: readiness passou e nenhum componente relevante esta degradado;
2. `degraded`: readiness passou, mas ao menos um componente secundario ou de capacidade esta degradado;
3. `unready`: readiness falhou.

Componentes sugeridos no payload:

1. `http_runtime`
2. `database`
3. `realtime`
4. `forms_worker`
5. `forms_queue`
6. `static_sites`

Cada componente deve usar um conjunto pequeno de estados, por exemplo:

- `ok`
- `degraded`
- `failed`
- `disabled`
- `unknown`

## 7. Decisao operacional central

O healthcheck binario do compose deve representar `readiness`, e nao o resumo operacional completo.

Traducao pratica da decisao:

1. o compose nao deve continuar apontando para um endpoint que apenas responde `status=ok` sem provar utilidade real;
2. o compose tambem nao deve apontar para um endpoint que fique `503` por qualquer degradacao secundaria, como worker do Forms indisponivel ou warning de capacidade do banco;
3. o endpoint publico de resumo operacional pode e deve expor `degraded`, mas isso nao deve sozinho tirar o container do ar.

Conclusao objetiva:

- `docker-compose.yml` e `docker-compose.api.yml` devem, na proxima etapa de implementacao, usar `GET /api/health/ready` como probe do container HTTP.

## 8. Matriz de classificacao proposta

| Situacao | Liveness | Readiness | Saude agregada |
| --- | --- | --- | --- |
| Processo HTTP responde rota minima | ok | depende dos checks indispensaveis | depende |
| Banco inacessivel | ok se rota minima responder | failed | unready |
| Startup ainda em migracao ou boot | failed ou indisponivel | failed | unready |
| Worker do Forms unhealthy com HTTP e banco ok | ok | ok | degraded |
| Backlog do Forms alto com HTTP e banco ok | ok | ok | degraded |
| Broker realtime cross-worker indisponivel com CRUD basico ok | ok | ok | degraded |
| Sites estaticos obrigatorios ausentes quando a API os serve | ok | failed | unready |
| Pool do banco em warning, mas ainda respondendo | ok | ok | degraded |

## 9. Riscos e observacoes especificas do estado atual

1. O `start_period: 30s` atual pode ficar apertado dependendo do tempo de `alembic upgrade head` e do cold start do runtime; isso precisa ser revisto na etapa de implementacao, mas nao foi alterado nesta execucao.
2. `depends_on: db: service_healthy` so protege a ordem de boot do compose; nao substitui um readiness real do HTTP em runtime.
3. O barramento realtime cross-worker hoje sobe no `lifespan`, mas ainda nao expoe um estado operacional publico proprio; por isso ele entra nesta proposta como componente a medir na proxima etapa, nao como fato ja implementado.
4. O worker do Forms ja possui health separado e nao deve voltar a contaminar a disponibilidade binaria da API HTTP.

## 10. Arquivos alterados

- `docs/incidents/2026-05-04-504-phase4-health-semantics-audit.md`

## 11. Comandos executados

Nao houve comando mutante nesta etapa. A auditoria foi feita por leitura focada do repo sobre:

- `sistema/app/routers/health.py`
- `sistema/app/main.py`
- `sistema/app/http_runtime.py`
- `sistema/app/database.py`
- `sistema/app/services/forms_queue.py`
- `sistema/app/forms_worker_healthcheck.py`
- `sistema/app/schemas.py`
- `docker-compose.yml`
- `docker-compose.api.yml`

## 12. Evidencias geradas

- `docs/incidents/2026-05-04-504-phase4-health-semantics-audit.md`

## 13. Validacao executada

- Validacao de consistencia por auditoria local do codigo versionado.
- Nenhum teste executavel foi necessario nesta etapa porque nao houve mudanca de runtime nem de endpoint; a saida desta execucao e uma proposta semantica versionada para a proxima etapa de implementacao.

## 14. Resultado

- aprovado.
- A semantica proposta fica definida assim:
  - `liveness`: processo HTTP vivo.
  - `readiness`: API realmente apta a receber trafego util.
  - `degraded`: API pronta, mas com componente secundario ou de capacidade em pior estado.

## 15. Rollback

Rollback desta execucao, se desejado:

1. remover `docs/incidents/2026-05-04-504-phase4-health-semantics-audit.md`.

Nenhum componente de producao, host, banco, edge ou compose foi alterado nesta etapa.

## 16. Proximo passo recomendado

Executar a proxima acao da Fase 4:

1. implementar `GET /api/health/live`, `GET /api/health/ready` e o novo resumo operacional de `GET /api/health`;
2. ligar o healthcheck do compose ao readiness binario;
3. manter o worker do Forms com health separado;
4. preparar a estrategia de auto-recuperacao da fase seguinte sem usar `degraded` como gatilho cego de restart.