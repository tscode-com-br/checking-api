# M4 — Variáveis de Ambiente em Produção: Modo Acidente

## Contexto

A feature Modo Acidente requer dois grupos de variáveis de ambiente que **não existiam** no `.env.production` antes desta release:

1. **DigitalOcean Spaces** — para upload/download de vídeos e ZIPs de archive.
2. **SMTP** — para envio de e-mails de alerta quando um usuário reporta `status=help`.

Ambos os grupos são **opcionais** no sentido em que o sistema não quebra sem eles (usa fallback para disco local e desativa e-mail), mas são **obrigatórios para o Modo Acidente funcionar corretamente em produção**.

---

## Referência de variáveis

### DO Spaces (`object_storage.py`)

| Variável env | Config field | Obrigatório | Descrição |
|---|---|---|---|
| `DO_SPACES_ENDPOINT_URL` | `do_spaces_endpoint_url` | Sim | Ex.: `https://sfo3.digitaloceanspaces.com` |
| `DO_SPACES_REGION` | `do_spaces_region` | Sim | Ex.: `sfo3` |
| `DO_SPACES_BUCKET` | `do_spaces_bucket` | Sim | Nome do bucket |
| `DO_SPACES_ACCESS_KEY` | `do_spaces_access_key` | Sim | Access Key ID (DO Spaces) |
| `DO_SPACES_SECRET_KEY` | `do_spaces_secret_key` | Sim | Secret Access Key |
| `DO_SPACES_PUBLIC_BASE_URL` | `do_spaces_public_base_url` | Não | URL CDN pública; fallback para endpoint URL |

**Comportamento sem as variáveis:** `_use_remote()` retorna `False` → arquivos salvos em disco local em `event_archives_dir/accidents_local_storage/` e servidos pelo endpoint `/api/admin/accidents/local-asset/{path}`. **Não funciona em produção multi-instância.**

### SMTP (`email_sender.py`)

| Variável env | Config field | Padrão | Obrigatório | Descrição |
|---|---|---|---|---|
| `SMTP_HOST` | `smtp_host` | `None` | Sim | Servidor SMTP. Se ausente, e-mails são silenciosamente descartados |
| `SMTP_PORT` | `smtp_port` | `587` | Não | Porta SMTP |
| `SMTP_USER` | `smtp_user` | `None` | Sim | Usuário de autenticação |
| `SMTP_PASSWORD` | `smtp_password` | `None` | Sim | Senha SMTP |
| `SMTP_FROM_EMAIL` | `smtp_from_email` | `None` | Sim | Endereço remetente (ex.: `alerts@example.com`) |
| `SMTP_FROM_NAME` | `smtp_from_name` | `CheckCheck` | Não | Nome exibido no campo From |
| `SMTP_USE_TLS` | `smtp_use_tls` | `false` | Não | `true` para SSL direto na porta 465 |
| `SMTP_USE_STARTTLS` | `smtp_use_starttls` | `true` | Não | Recomendado: STARTTLS na porta 587 |
| `SMTP_TIMEOUT_SECONDS` | `smtp_timeout_seconds` | `30` | Não | Timeout de conexão |
| `SMTP_MAX_RETRIES` | `smtp_max_retries` | `3` | Não | Tentativas antes de marcar como `failed` |
| `SMTP_ACCIDENT_NOTIFY_EMAIL` | `smtp_accident_notify_email` | `None` | Sim* | E-mail que recebe cópia de todos os alertas `status=help`. *Se omitido, nenhuma notificação é enviada |

**Comportamento sem `SMTP_HOST`:** `send_pending_emails()` retorna imediatamente sem enviar nada. `EmailDeliveryLog` terá registros com `delivery_status='queued'` que nunca progridem.

---

## Procedimento de atualização em produção

### Passo 1 — Editar `.env.production` no servidor

```bash
# Conectar ao droplet via SSH
ssh root@<IP_DO_DROPLET>

# Editar o arquivo .env de produção
nano /opt/checking/.env
```

Adicionar (ou atualizar) os blocos abaixo, substituindo os valores `CHANGE_ME_*`:

```dotenv
# DigitalOcean Spaces
DO_SPACES_ENDPOINT_URL=https://sfo3.digitaloceanspaces.com
DO_SPACES_REGION=sfo3
DO_SPACES_BUCKET=<nome-do-bucket>
DO_SPACES_ACCESS_KEY=<access-key-id>
DO_SPACES_SECRET_KEY=<secret-key>
DO_SPACES_PUBLIC_BASE_URL=https://<nome-do-bucket>.sfo3.cdn.digitaloceanspaces.com

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=<app-password>
SMTP_FROM_EMAIL=alerts@example.com
SMTP_FROM_NAME=CheckCheck
SMTP_USE_TLS=false
SMTP_USE_STARTTLS=true
SMTP_TIMEOUT_SECONDS=30
SMTP_MAX_RETRIES=3
SMTP_ACCIDENT_NOTIFY_EMAIL=safety-team@example.com
```

> **Nota de segurança:** O arquivo `.env` **não deve ser versionado** com valores reais. O arquivo `deploy/.env.production.example` no repositório contém apenas placeholders `CHANGE_ME_*`.

### Passo 2 — Restart da API

```bash
# Via docker-compose
cd /opt/checking
docker compose -f docker-compose.api.yml restart api

# Verificar que o container subiu sem erros
docker compose -f docker-compose.api.yml logs --tail=50 api
```

Aguardar as linhas de startup nos logs:
```
INFO:     Application startup complete.
INFO:     Checking Admin SSE broker started
INFO:     Checking Web Check SSE broker started
```

### Passo 3 — Verificação rápida

```bash
# Deve retornar 401 (não 500 — 500 indicaria erro de configuração)
curl -s -o /dev/null -w "%{http_code}" \
    https://<dominio>/api/admin/accidents/active
# Esperado: 401

# Verificar logs de SMTP (executar o smoke test para disparar um e-mail de teste)
docker compose -f docker-compose.api.yml exec api \
    python -c "
from sistema.app.core.config import settings
print('smtp_host:', settings.smtp_host)
print('smtp_user:', settings.smtp_user)
print('smtp_from_email:', settings.smtp_from_email)
print('smtp_accident_notify_email:', settings.smtp_accident_notify_email)
print('do_spaces_bucket:', settings.do_spaces_bucket)
print('do_spaces_region:', settings.do_spaces_region)
print('Storage mode:', 'REMOTE (DO Spaces)' if settings.do_spaces_bucket and settings.do_spaces_access_key else 'LOCAL FALLBACK')
"
```

### Passo 4 — Teste SMTP de conectividade

```bash
# Dentro do container, testar conexão SMTP
docker compose -f docker-compose.api.yml exec api python -c "
import smtplib
from sistema.app.core.config import settings
with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
    if settings.smtp_use_starttls:
        s.starttls()
    s.login(settings.smtp_user, settings.smtp_password)
    print('SMTP OK: login bem-sucedido')
"
```

### Passo 5 — Teste DO Spaces de conectividade

```bash
docker compose -f docker-compose.api.yml exec api python -c "
import boto3
from sistema.app.core.config import settings
client = boto3.client(
    's3',
    endpoint_url=settings.do_spaces_endpoint_url,
    region_name=settings.do_spaces_region,
    aws_access_key_id=settings.do_spaces_access_key,
    aws_secret_access_key=settings.do_spaces_secret_key,
)
resp = client.list_objects_v2(Bucket=settings.do_spaces_bucket, MaxKeys=1)
print('DO Spaces OK: bucket', settings.do_spaces_bucket, 'acessível')
"
```

---

## Checklist Go/No-Go

| # | Item | OK? |
|---|------|-----|
| 1 | `.env.production` editado com todos os valores DO Spaces | `[ ]` |
| 2 | `.env.production` editado com todos os valores SMTP | `[ ]` |
| 3 | Container reiniciado sem erros no log | `[ ]` |
| 4 | `curl /api/admin/accidents/active` → 401 (não 500) | `[ ]` |
| 5 | `settings.do_spaces_bucket` imprime nome correto | `[ ]` |
| 6 | Teste de conexão SMTP → "SMTP OK" | `[ ]` |
| 7 | Teste de conexão DO Spaces → "DO Spaces OK" | `[ ]` |

---

## Referências

- `sistema/app/core/config.py` — definição de todos os campos `Settings`
- `sistema/app/services/object_storage.py` — lógica de fallback local vs. remoto
- `sistema/app/services/email_sender.py` — lógica de envio e retry
- `.env.example` — template para desenvolvimento local (atualizado com M4)
- `deploy/.env.production.example` — template para produção (atualizado com M4)
- `scripts/smoke_test_accident_mode.py` — smoke test pós-deploy (Task M2)
