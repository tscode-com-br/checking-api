# 504 Phase 6 - Restricao da exposicao do Postgres

## Objetivo

Reduzir risco operacional do Postgres exposto no host sem quebrar a conectividade interna entre API, worker e banco na rede Docker Compose.

## Diagnostico

### Evidencia confirmada no repo

1. O servico `db` publicava `5432` no host em todas as interfaces por default em `docker-compose.yml` e `docker-compose.api.yml`.
2. A API HTTP e o worker de Forms usam `DATABASE_URL=...@db:5432/...`, ou seja, falam com o Postgres pelo nome do servico Docker e nao pelo endereco publicado no host.
3. O exemplo de producao em `deploy/.env.production.example` tambem mantinha `DATABASE_URL=...@db:5432/...`, reforcando que a conectividade normal da aplicacao e interna a rede Compose.
4. Nos scripts e docs do repo, nao apareceu dependencia operacional forte de um Postgres publicado publicamente. Os utilitarios encontrados preferem `docker compose exec db psql` ou consumo interno da rede Docker.

### Sobre o ruido com o usuario inexistente `reader`

1. O pedido do usuario menciona ruido observado com o usuario `reader`, o que e compativel com tentativa externa automatizada contra um Postgres publicado.
2. Nesta workspace, nao apareceu artefato versionado ou log salvo contendo a linha original desse evento.
3. Portanto, a exposicao do `5432` esta confirmada pelo repo, mas a evidencia textual exata do `reader` nao ficou localizada nos artefatos acessiveis daqui.
4. Mesmo sem a linha original, o risco operacional continua real: manter `5432` publicado em todas as interfaces permite autenticacoes externas indesejadas, ruido em log e superficie de ataque desnecessaria.

## Menor mudanca correta

### Decisao

Restringir a publicacao do Postgres a loopback por default, em vez de continuar publicando em todas as interfaces.

### Implementacao aplicada

1. `docker-compose.yml` agora publica o banco como `${POSTGRES_BIND_ADDRESS:-127.0.0.1}:${POSTGRES_PORT:-5432}:5432`.
2. `docker-compose.api.yml` recebeu a mesma restricao.
3. `deploy/.env.production.example` agora explicita `POSTGRES_BIND_ADDRESS=127.0.0.1`.

### Justificativa tecnica

1. Esta e a menor mudanca segura porque preserva acesso local do proprio host, caso manutencao manual seja realmente necessaria.
2. Ao mesmo tempo, fecha a exposicao externa por default sem depender primeiro de firewall, `ufw` ou ajuste manual fora do repo.
3. A aplicacao continua usando `db:5432` internamente, entao a conectividade entre containers nao depende do bind do host.
4. Remover completamente `ports:` seria uma opcao mais restritiva, mas tem risco maior de surpreender manutencao local legitima. Por isso, loopback foi escolhido como passo minimo e correto.

## Onde o controle deve viver

### Controle primario

O controle primario deve viver no Compose versionado do repo.

Motivo:

1. e a fonte de verdade da publicacao de portas;
2. evita drift entre host e repositorio;
3. reduz a superficie exposta por default antes mesmo de qualquer regra adicional de firewall;
4. continua claro para futuros deploys e reprovisionamentos.

### Controle secundario

Firewall do host pode continuar existindo como defesa em profundidade, mas nao deve ser a unica linha de defesa.

Motivo:

1. firewall sozinho nao corrige o fato de o repositorio ainda ensinar a publicar em todas as interfaces;
2. firewall e mais suscetivel a drift manual;
3. o bind em loopback no Compose reduz o risco no ponto mais proximo da causa.

## Validacao recomendada no host apos deploy

### Validar que o `5432` nao esta mais exposto externamente

Executar no host:

```bash
docker compose ps
docker compose port db 5432
ss -ltnp | grep 5432
```

Resultado esperado:

1. o mapeamento do `db` deve aparecer como `127.0.0.1:5432` ou equivalente em loopback;
2. `ss -ltnp` nao deve mostrar `0.0.0.0:5432` nem o IP publico do host ligado ao Postgres.

Se houver acesso a partir de outra maquina fora do host, validar tambem:

```bash
nc -vz <host-ou-ip-publico> 5432
```

Resultado esperado:

1. conexao recusada ou indisponivel a partir de fora;
2. nenhuma nova tentativa externa deve mais atingir o Postgres via interface publica.

### Validar que a aplicacao interna continua funcionando

Para a stack principal:

```bash
docker compose exec db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
docker compose exec app python -c "from sqlalchemy import text; from sistema.app.database import engine; conn = engine.connect(); print(conn.execute(text('select 1')).scalar()); conn.close()"
docker compose exec app python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=5).status)"
```

Para a stack API-only, trocar `app` por `api` no segundo e no terceiro comando.

Resultado esperado:

1. `pg_isready` retorna pronto;
2. `select 1` retorna `1` a partir do container HTTP;
3. `/api/health/ready` continua respondendo `200`.

## Validacao executada nesta workspace

1. As duas Compose editadas foram parseadas com sucesso como YAML no ambiente Python do workspace.
2. A mudanca foi aplicada sem tocar no `DATABASE_URL` interno, justamente para preservar `db:5432` entre containers.

## Resultado

O repo deixa de publicar o Postgres em todas as interfaces por default e passa a restringi-lo a loopback, que e o menor endurecimento correto dado o desenho atual da stack.