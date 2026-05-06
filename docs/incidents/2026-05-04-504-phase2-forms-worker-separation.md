# Implementacao do worker separado do Forms - Fase 2 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado em escopo de repo.
- Tipo de mudanca: separacao do consumo da fila do Forms para processo/servico dedicado, sem mudar o contrato atual dos endpoints.
- Regra preservada: o preenchimento do Forms em `sistema/app/services/forms_worker.py` nao foi alterado.

## 2. O que mudou

### 2.1 Processo HTTP

- `sistema/app/main.py` deixou de iniciar e parar `forms_submission_worker` no `lifespan`.
- Com isso, o processo FastAPI volta a ficar restrito a aceitar requests, persistir `forms_submissions` e responder rapido.

### 2.2 Worker separado

- Foi criado o entrypoint dedicado `sistema/app/forms_worker_main.py`.
- Esse entrypoint inicializa o minimo necessario do ambiente e executa o loop do worker fora do runtime HTTP.

### 2.3 Fila com semantica de reserva mais forte

- `sistema/app/services/forms_queue.py` passou a reservar itens com uma transicao atomica `pending -> processing` baseada em `UPDATE ... WHERE status = 'pending'`.
- Se outro consumidor ganhar a corrida entre a selecao do candidato e o `UPDATE`, o codigo faz `rollback` e tenta o proximo item.
- Isso reduz o risco de dupla reserva quando a proxima etapa considerar mais de um consumidor.

### 2.4 Empacotamento

- `Dockerfile` foi dividido em targets:
  - `app-runtime` para o HTTP;
  - `forms-worker-runtime` para o worker com Chromium instalado.
- `docker-compose.yml` passou a versionar dois servicos distintos:
  - `app`
  - `forms-worker`

### 2.5 Preservacao do preenchimento do Forms

- `sistema/app/services/forms_worker.py` foi preservado.
- A unica mudanca funcional nessa superficie foi indireta: `FormsWorker` agora e importado de forma lazy em `forms_queue.py`, para o processo HTTP nao precisar carregar essa dependencia no caminho normal da API.

## 3. Arquivos alterados nesta execucao

- `sistema/app/main.py`
- `sistema/app/forms_worker_main.py`
- `sistema/app/services/forms_queue.py`
- `Dockerfile`
- `docker-compose.yml`
- `tests/test_api_flow.py`

## 4. Validacao executada nesta execucao

### 4.1 Testes focados aprovados

Comando executado:

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "http_app_lifespan_does_not_start_forms_worker or forms_queue_reservation_retries_when_candidate_was_claimed or forms_queue_processing_emits_structured_logs"
```

Resultado:

- `3 passed`

Cobertura objetiva desses testes:

- o `lifespan` do app HTTP nao inicia mais o worker do Forms;
- a reserva da fila tenta novamente quando um candidato deixa de estar disponivel entre selecao e claim;
- o processamento da fila continua funcionando e emitindo logs estruturados.

### 4.2 Checagem estatica dos arquivos alterados

- `get_errors` retornou sem erros para:
  - `sistema/app/main.py`
  - `sistema/app/forms_worker_main.py`
  - `sistema/app/services/forms_queue.py`
  - `tests/test_api_flow.py`
  - `docker-compose.yml`
  - `Dockerfile`

### 4.3 Validacao de Compose bloqueada no ambiente local

Tentativas executadas:

- `docker-compose -f docker-compose.yml config`
- `docker compose -f docker-compose.yml config`

Resultado:

- bloqueado localmente porque este ambiente nao tem `docker-compose` nem `docker` disponiveis no PATH.

## 5. Impacto operacional esperado

- backlog ou lentidao do Forms deixam de nascer dentro do processo FastAPI;
- o servico HTTP deixa de iniciar um thread local de consumo da fila;
- o consumo do Forms passa a rodar em servico separado do compose;
- a imagem do worker continua carregando Chromium;
- a imagem HTTP deixa de instalar Chromium no target usado pela API.

## 6. Rollback minimo desta execucao

Se o rollout local ou homologado do worker separado falhar, o rollback minimo desta etapa e:

1. restaurar `sistema/app/main.py` para iniciar/parar `forms_submission_worker` no `lifespan`;
2. remover o servico `forms-worker` do `docker-compose.yml`;
3. restaurar o `Dockerfile` monolitico anterior;
4. manter a tabela `forms_submissions` intacta;
5. nao alterar `forms_worker.py`, pois o comportamento de preenchimento foi preservado.

## 7. Proximo passo recomendado

O proximo prompt natural da Fase 2 e revisar a robustez do novo worker separado:

- retentativa e backoff observaveis no processo dedicado;
- health proprio do worker;
- estrategia de restart e introspecao de backlog em producao;
- validacao controlada de isolacao sob backlog.