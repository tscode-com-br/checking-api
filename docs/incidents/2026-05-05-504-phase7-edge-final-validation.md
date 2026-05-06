# Validacao final do edge - Fase 7 - incidente 504 de 2026-05-04

## 1. Status desta execucao

- Resultado atual: bloqueado para execucao no droplet nesta sessao por ausencia de credenciais/acesso SSH configurado aqui.
- Acao util entregue mesmo assim: foi versionado um runner unico para a validacao final do edge em `deploy/nginx/validate_checking_edge_final.sh`.

## 2. O que o runner faz

Quando executado no host com acesso operacional valido, o script:

1. gera backup explicito do `server` config e do include `http` do edge;
2. aplica o cutover versionado com `nginx -t` e reload seguro;
3. salva `curl -i` locais e publicos para:
   - `/api/health`
   - `/checking/admin`
   - `/checking/user`
   - `/checking/transport`
4. executa os smoke tests versionados de `deploy/nginx/verify_checking_edge_cutover.sh`;
5. executa a reconciliacao do `nginx -T` ativo contra o repo;
6. falha se houver drift no bloco `server` ou se as zonas `limit_req_zone` do include `http` nao aparecerem na configuracao ativa.

## 3. Comando pronto para execucao no droplet

```bash
bash deploy/nginx/validate_checking_edge_final.sh \
  --evidence-dir /root/checkcheck_incidents/2026-05-05-504-phase7-edge-final \
  --server-config /etc/nginx/sites-enabled/tscode.com.br.conf \
  --http-config-target /etc/nginx/conf.d/checkcheck-edge-http.conf
```

## 4. Evidencias esperadas

O diretorio de evidencia gerado pelo runner deve conter, no minimo:

- `10_apply_cutover.txt`
- `11_post_apply_nginx_t.txt`
- `20_local_api_health.txt`
- `21_local_checking_admin.txt`
- `22_local_checking_user.txt`
- `23_local_checking_transport.txt`
- `30_public_api_health.txt`
- `31_public_checking_admin.txt`
- `32_public_checking_user.txt`
- `33_public_checking_transport.txt`
- `40_verify_local.txt`
- `41_verify_full.txt`
- `nginx_reconciliation/99_nginx_summary.txt`
- `99_edge_final_validation_summary.txt`

## 5. Dependencias manuais que ainda restam

Essas dependencias continuam sendo debito operacional, nao solucao definitiva:

1. credencial SSH/acesso ao droplet segue fora do repo;
2. o caminho real do `server` config HTTPS ainda precisa ser informado no host;
3. o caminho de include `http` do host ainda depende do layout real do `nginx.conf` no droplet;
4. se o ambiente exigir cookies, auth adicional ou origem publica alternativa, isso ainda precisa ser passado como argumento ao runner.

## 6. Resultado desta execucao

- Runner versionado: concluido.
- Validacao real no host: bloqueada nesta sessao por ausencia de acesso operacional.