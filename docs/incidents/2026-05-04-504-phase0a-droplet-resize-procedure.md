# Procedimento operacional - Fase 0A - ampliacao do droplet

## 1. Status desta execucao

- Resultado desta execucao: procedimento preparado, nao executado.
- Motivo: esta sessao nao tem acesso ao painel nem a CLI autenticada da DigitalOcean.
- Objetivo deste documento: permitir que outro executor realize o resize do droplet com trilha minima de evidencias, campos obrigatorios preenchidos e validacao tecnica antes e depois.

## 2. Escopo e regra desta mudanca

- Mudanca pretendida: ampliar o droplet para `2 GB RAM / 2 vCPU`.
- Natureza da mudanca: mitigacao imediata de capacidade e headroom, nao correcao da causa raiz.
- Regra operacional: nao alterar disco se isso nao for estritamente necessario. O alvo desta fase e CPU/RAM, preservando a possibilidade de downscale posterior quando a politica da DigitalOcean permitir.
- Fonte da decisao tecnica: `docs/incidents/2026-05-04-504-phase0a-droplet-resize-decision.md`.

## 3. Campos obrigatorios que o executor deve preencher

Antes de iniciar a mudanca, registrar explicitamente:

- `droplet_name`:
- `droplet_id`:
- `region`:
- `public_ipv4`:
- `current_plan_slug`:
- `current_memory_mb`:
- `current_vcpu_count`:
- `target_plan_slug`:
- `target_memory_mb`:
- `target_vcpu_count`:
- `maintenance_window_start_utc`:
- `maintenance_window_end_utc`:
- `operator_name`:
- `execution_path`: `control_panel` ou `doctl`
- `power_off_required_by_platform`: `yes` ou `no`, com evidencia capturada
- `resize_disk`: `false` por padrao nesta fase

Se qualquer um desses campos nao puder ser preenchido com evidencia objetiva, parar e reportar bloqueio.

## 4. Pre-requisitos obrigatorios

1. Acesso valido ao painel da DigitalOcean ou a uma instalacao autenticada de `doctl`.
2. Acesso SSH funcional ao droplet.
3. Janela operacional aprovada com ciencia de que a DigitalOcean recomenda contar aproximadamente um minuto de indisponibilidade por GB usado em disco, embora a duracao real possa ser menor.
4. Evidencias da Fase 0 guardadas ou, se ainda nao existirem, execucao dos coletores da Fase 0 antes da mudanca.
5. Confirmacao explicita de que a mudanca e apenas de CPU/RAM nesta fase, sem resize de disco.
6. Snapshot ou outro backup aprovado pela equipe antes da mudanca. A documentacao da DigitalOcean recomenda fortemente snapshot antes do resize.
7. Freeze temporario de deploy durante a janela da mudanca.

## 5. Evidencias obrigatorias antes da mudanca

Criar um diretorio de evidencias dedicado, por exemplo:

`/root/checkcheck_incidents/2026-05-04-504-phase0a-resize`

Salvar, no minimo, os seguintes artefatos antes de tocar no droplet:

### 5.1 Evidencias operacionais do host e da stack

- Rodar os coletores ja preparados no repo, se ainda nao tiverem sido executados ou se a equipe quiser recongelar o estado imediatamente antes da mudanca:
  - `deploy/maintenance/capture_phase0_baseline.sh`
  - `deploy/maintenance/capture_phase0_docker_state.sh`
  - `deploy/maintenance/capture_phase0_nginx_config.sh`
  - `deploy/maintenance/capture_phase0_nginx_logs.sh`
  - `deploy/maintenance/capture_phase0_edge_http_checks.sh`

### 5.2 Evidencias especificas da capacidade atual

Salvar em arquivos separados:

- `date -u` -> `60_resize_pre_date_utc.txt`
- `free -m` -> `61_resize_pre_free_m.txt`
- `nproc` -> `62_resize_pre_nproc.txt`
- `lscpu` -> `63_resize_pre_lscpu.txt`
- `df -h /` -> `64_resize_pre_df_root.txt`
- `docker compose ps` -> `65_resize_pre_docker_compose_ps.txt`
- `curl -i http://127.0.0.1:8000/api/health` -> `66_resize_pre_local_health.txt`
- `curl -i https://tscode.com.br/api/health` -> `67_resize_pre_public_health.txt`

### 5.3 Evidencias da DigitalOcean

Salvar em arquivos separados:

- tipo atual do droplet;
- tipo alvo do droplet;
- confirmacao de que o resize e somente CPU/RAM;
- confirmacao se a plataforma exige desligamento/power off para o caminho escolhido;
- identificador do snapshot ou backup criado antes da mudanca.

Se o executor usar painel, capturar screenshots ou exportar texto equivalente para os campos acima.

Se o executor usar `doctl`, salvar no minimo:

- `doctl compute droplet list` -> `70_doctl_droplet_list.txt`
- `doctl compute droplet get <droplet_id> --output json` -> `71_doctl_droplet_get.json`
- `doctl compute size list` -> `72_doctl_size_list.txt`

## 6. Caminho A - Execucao via painel da DigitalOcean

Usar este caminho se o executor tiver acesso ao painel e preferir o fluxo visual.

1. Confirmar que o droplet correto foi identificado por nome, ID e IP publico.
2. Confirmar que existe snapshot ou backup valido antes da mudanca.
3. Conectar no droplet via SSH e fazer desligamento limpo do sistema:

```bash
sudo shutdown -h now
```

4. No painel da DigitalOcean, abrir o droplet correto.
5. Ir para `Settings` e localizar `Resize configuration`.
6. Registrar o plano atual exibido pelo painel.
7. Escolher a opcao de manter o tamanho do disco fixo, se a interface oferecer essa escolha e isso continuar compativel com o plano alvo.
8. Escolher o plano alvo equivalente a `2 GB / 2 vCPU`.
9. Registrar explicitamente se a interface exigiu que o droplet estivesse desligado antes do resize.
10. Executar o resize.
11. Aguardar a conclusao da operacao.
12. Ligar o droplet novamente pelo painel.
13. Registrar horario UTC de inicio e fim do resize.

## 7. Caminho B - Execucao via doctl

Usar este caminho se o executor tiver `doctl` autenticado e preferir trilha CLI.

### 7.1 Descoberta e registro do alvo

```bash
doctl compute droplet list
doctl compute droplet get <droplet_id> --output json
doctl compute size list
```

Registrar o slug exato do plano alvo equivalente a `2 GB / 2 vCPU`. Exemplo comum da documentacao: `s-2vcpu-2gb`. Nao assumir slug sem confirmar na saida real do `doctl compute size list`.

### 7.2 Desligamento controlado

Fazer primeiro desligamento limpo no guest:

```bash
ssh <user>@<droplet_ip> 'sudo shutdown -h now'
```

Em seguida, registrar o power off da DigitalOcean para deixar a trilha auditavel:

```bash
doctl compute droplet-action power-off <droplet_id> --wait
```

### 7.3 Resize de CPU/RAM sem resize de disco

```bash
doctl compute droplet-action resize <droplet_id> --size <target_plan_slug> --wait
```

Observacoes:

- Pela referencia do `doctl`, o comando `resize` trabalha por padrao apenas com CPU/RAM; `--resize-disk` deve permanecer ausente nesta fase.
- Se o executor optar por comportamento diferente, isso sai do escopo desta Fase 0A e precisa de aprovacao explicita.

### 7.4 Power on e registro

```bash
doctl compute droplet-action power-on <droplet_id> --wait
doctl compute droplet get <droplet_id> --output json
```

Salvar tambem a saida da acao de resize e do estado final do droplet.

## 8. Checklist tecnico pos-mudanca

Depois que o host voltar, executar e salvar em arquivos separados:

- `date -u` -> `80_resize_post_date_utc.txt`
- `free -m` -> `81_resize_post_free_m.txt`
- `nproc` -> `82_resize_post_nproc.txt`
- `lscpu` -> `83_resize_post_lscpu.txt`
- `df -h /` -> `84_resize_post_df_root.txt`
- `docker compose ps` -> `85_resize_post_docker_compose_ps.txt`
- `curl -i http://127.0.0.1:8000/api/health` -> `86_resize_post_local_health.txt`
- `curl -i https://tscode.com.br/api/health` -> `87_resize_post_public_health.txt`

Verificar explicitamente e registrar em resumo final:

1. se a memoria total observada passou a refletir o plano alvo;
2. se o total de vCPUs passou a refletir o plano alvo;
3. se `docker compose ps` voltou com os servicos esperados;
4. se o health local respondeu;
5. se o health publico respondeu;
6. se houve efeito colateral em Docker, Nginx, mounts, rede ou healthchecks;
7. se foi necessario qualquer passo adicional de recovery fora do plano.

## 9. Checklist operacional pos-mudanca

Marcar cada item como `ok`, `nao ok` ou `nao verificado`:

- SSH voltou no host.
- `free -m` reflete o alvo de memoria.
- `nproc` e `lscpu` refletem o alvo de CPU.
- `docker compose ps` mostra `app` e `db` em estado esperado.
- `curl -i http://127.0.0.1:8000/api/health` responde utilmente.
- `curl -i https://tscode.com.br/api/health` responde utilmente.
- Nginx esta roteando sem erro novo evidente.
- Nao houve quebra de mount, IP, DNS, firewall ou rota publica.
- Nao houve necessidade de resize de disco.
- Snapshot/backup previo permanece identificado ate o aceite final da mudanca.

## 10. Artefatos que o executor deve devolver

1. Nome, ID, regiao e IP do droplet afetado.
2. Tipo atual confirmado e tipo alvo confirmado.
3. Janela executada em UTC.
4. Evidencia se o caminho escolhido exigiu power off.
5. Identificador do snapshot ou backup previo.
6. Arquivos `60` a `87` descritos neste documento.
7. Resumo final com resultado `aprovado`, `parcialmente aprovado` ou `bloqueado`.
8. Lista objetiva de qualquer efeito colateral observado.

## 11. Condicoes de parada obrigatoria nesta fase

Parar e nao executar o resize se qualquer uma das situacoes abaixo ocorrer:

1. o droplet atual nao puder ser identificado com seguranca;
2. o plano alvo `2 GB / 2 vCPU` nao estiver disponivel para resize no droplet real;
3. nao houver snapshot ou backup aprovado antes da mudanca;
4. nao houver janela operacional aprovada;
5. os coletores de baseline falharem e o estado pre-mudanca ficar desconhecido;
6. o executor descobrir que o droplet ja esta em `2 GB / 2 vCPU` ou acima.

## 12. Resultado esperado desta fase

Ao fim da execucao real deste procedimento, a equipe deve ter:

- um resize executado ou bloqueado com justificativa objetiva;
- evidencias pre e pos-mudanca salvas em caminho conhecido;
- tipo atual, tipo alvo, janela e necessidade de power off documentados;
- insumos suficientes para rodar a validacao da proxima etapa da Fase 0A.