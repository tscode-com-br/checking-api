# Validacao da isolacao do Forms sob backlog controlado - Fase 2 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: aprovado em experimento local controlado.
- Objetivo desta etapa: provar que backlog e drenagem lenta da fila `forms_submissions` nao voltam a degradar o runtime HTTP de forma comparavel ao incidente original.
- Escopo validado aqui: app FastAPI em servidor HTTP real local, fila persistida em `forms_submissions` e consumidor separado em subprocesso Python usando o mesmo caminho de processamento da fila.

## 2. Hipotese validada

Hipotese desta etapa:

- mesmo com backlog real em `forms_submissions` e consumo lento do worker, o app HTTP continua respondendo rapido porque as rotas criticas nao dependem do processamento do Forms para completar.

Checagem discriminante usada:

- manter backlog ativo enquanto um consumidor separado drena a fila lentamente;
- durante esse backlog, medir `GET /api/health`, `POST /api/web/auth/login`, `GET /api/web/check/state`, `POST /api/admin/auth/login`, `GET /api/admin/projects`, `GET /api/admin/checkin` e `GET /api/mobile/state`;
- falhar a validacao se qualquer rota se aproximar de latencias de segundos ou se o backlog nao permanecer ativo durante as medições.

## 3. Desenho do experimento

O experimento foi automatizado no teste:

- `tests/test_api_flow.py::test_forms_backlog_pressure_keeps_http_routes_responsive`

Desenho aplicado:

1. criar 20 itens `pending` em `forms_submissions`;
2. iniciar um subprocesso Python separado para drenar a fila com `process_forms_submission_queue_once(max_items=1)`;
3. nesse subprocesso, substituir `FormsWorker.submit_with_retries(...)` por uma versao controlada que dorme `150 ms` por item antes de retornar sucesso;
4. subir a API em Uvicorn local real via `live_app_server()`;
5. esperar ate existir backlog ativo com `processing_count >= 1`;
6. medir 5 amostras por rota critica e por login enquanto o backlog segue maior que zero;
7. confirmar que a fila ainda estava pressionada ao fim das medições e depois drenar ate zero.

Importante:

- este experimento valida a isolacao HTTP contra backlog do Forms em ambiente local controlado;
- ele nao substitui validacao de Compose, container healthcheck, Nginx ou host DigitalOcean.

## 4. Comando reprodutivel

```powershell
c:/dev/projetos/checkcheck/.venv/Scripts/python.exe -m pytest tests/test_api_flow.py -k "forms_backlog_pressure_keeps_http_routes_responsive" -s
```

## 5. Evidencia objetiva observada

Payload emitido pelo teste nesta execucao:

```json
{
  "backlog_after_drain": 0,
  "backlog_after_requests": 11,
  "event": "forms_isolation_validation",
  "initial_backlog": 20,
  "latency_summary": {
    "admin_checkin": {
      "average_ms": 9,
      "count": 5,
      "max_ms": 10,
      "min_ms": 8,
      "p95_ms": 10
    },
    "admin_login": {
      "average_ms": 99,
      "count": 5,
      "max_ms": 110,
      "min_ms": 82,
      "p95_ms": 110
    },
    "admin_projects": {
      "average_ms": 6,
      "count": 5,
      "max_ms": 6,
      "min_ms": 5,
      "p95_ms": 6
    },
    "health": {
      "average_ms": 24,
      "count": 5,
      "max_ms": 35,
      "min_ms": 17,
      "p95_ms": 35
    },
    "mobile_state": {
      "average_ms": 27,
      "count": 5,
      "max_ms": 42,
      "min_ms": 22,
      "p95_ms": 42
    },
    "web_login": {
      "average_ms": 94,
      "count": 5,
      "max_ms": 111,
      "min_ms": 73,
      "p95_ms": 111
    },
    "web_state": {
      "average_ms": 12,
      "count": 5,
      "max_ms": 25,
      "min_ms": 7,
      "p95_ms": 25
    }
  },
  "pressure_backlog": 20,
  "pressure_processing": 1
}
```

Leitura direta da evidencia:

- o backlog estava efetivamente ativo durante as medições: `pressure_backlog=20`, `pressure_processing=1`;
- ao fim das requests ainda restavam 11 itens de backlog, logo as medições ocorreram sob pressão real da fila;
- depois disso a fila drenou para zero sem exigir nenhuma ajuda do app HTTP;
- nenhuma rota medida chegou perto de latencias de segundos ou do perfil observado em `504`.

## 6. Resultado tecnico

Neste experimento local:

- `GET /api/health` ficou com máximo de `35 ms`;
- `POST /api/web/auth/login` ficou com máximo de `111 ms`;
- `GET /api/web/check/state` ficou com máximo de `25 ms`;
- `POST /api/admin/auth/login` ficou com máximo de `110 ms`;
- `GET /api/admin/projects` ficou com máximo de `6 ms`;
- `GET /api/admin/checkin` ficou com máximo de `10 ms`;
- `GET /api/mobile/state` ficou com máximo de `42 ms`.

Conclusao objetiva:

- o app HTTP permaneceu responsivo enquanto o backlog do Forms era drenado lentamente por um consumidor separado;
- a validacao local sustenta que a separacao do Forms removeu o acoplamento operacional que antes permitia backlog do Forms competir diretamente com as rotas quentes do HTTP.

## 7. Limitacoes declaradas

1. esta etapa nao mede Nginx, rede publica, container restart policy nem healthcheck de Compose;
2. o consumidor usado no experimento e um subprocesso Python controlado, nao o servico Docker completo;
3. a carga aqui valida isolamento funcional do HTTP contra backlog do Forms, nao throughput maximo de producao.

## 8. Proximo passo recomendado

O proximo passo natural e seguir para a Fase 3 do plano, focando hardening do runtime HTTP e consistencia de realtime cross-worker. A isolacao local do Forms ficou validada o suficiente para parar de tratar o worker como bloqueador do caminho critico HTTP.