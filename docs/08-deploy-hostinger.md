# Néfron — Deploy na Hostinger

O Néfron tem três partes: **app Flutter web** (estático), **API FastAPI** (Python)
e **PostgreSQL**. Na Hostinger isso define duas rotas possíveis:

| Plano Hostinger | O que roda | Veredito |
|---|---|---|
| Hospedagem compartilhada / Cloud (hPanel, PHP+MySQL) | Só arquivos estáticos | Serve **apenas para o frontend** — não executa Python nem PostgreSQL |
| **VPS (KVM 1 ou superior)** | Tudo (Docker) | **Recomendado** — sistema completo em um só lugar |

> Dados de saúde: use sempre HTTPS, segredos fortes e backups (LGPD). O VPS
> da Hostinger tem data center em SP (importante para residência de dados).

---

## Opção A — VPS da Hostinger (recomendada): sistema completo

### 1. Criar o VPS
1. hPanel → **VPS** → escolha um plano (KVM 2 / 8 GB é confortável; KVM 1 roda).
2. Sistema operacional: use o template **"Ubuntu 24.04 with Docker"**
   (ou Ubuntu puro e instale Docker: `curl -fsSL https://get.docker.com | sh`).
3. Anote o IP. Em **Domínios → DNS**, crie um registro **A** apontando seu
   domínio/subdomínio (ex.: `nefron.seudominio.com.br`) para o IP do VPS.

### 2. Subir o sistema
```bash
ssh root@SEU_IP

git clone https://github.com/rafaelfurtado123-alt/rx.git && cd rx

# Segredos
cp deploy/.env.example deploy/.env
nano deploy/.env          # DOMAIN, DB_PASSWORD, JWT_SECRET (openssl rand -hex 32)

# Frontend: use o BUILD PRONTO (sem precisar de Flutter!) do branch web-dist
git clone -b web-dist --depth 1 https://github.com/rafaelfurtado123-alt/rx.git /tmp/webdist
cp -r /tmp/webdist/web deploy/web
# (o build é universal: detecta o domínio da página automaticamente)
# Alternativas: compile com ./deploy/build_web.sh, ou envie por scp

# Banco (primeira vez) + serviços
docker compose -f deploy/docker-compose.yml --env-file deploy/.env --profile bootstrap up migrate
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build

# Usuários demo (opcional)
docker compose -f deploy/docker-compose.yml --env-file deploy/.env \
  exec api python -m scripts.seed_demo
```

Acesse `http://SEU-DOMINIO` — app no ar, API em `/api/v1`, docs em `/api/v1`→`/docs`
(via `http://SEU-DOMINIO/health` para o health-check).

### 3. HTTPS (obrigatório)
```bash
apt install -y certbot python3-certbot-nginx   # se nginx no host, OU:
# Com o nginx do compose, o caminho simples é o Cloudflare (proxy + TLS)
# apontando para o VPS, ou trocar a porta 80 do serviço web por um
# reverse-proxy com TLS (caddy/traefik). Alternativa mínima com certbot
# standalone + volume dos certificados no serviço web.
```
Sugestão prática: **Cloudflare gratuito** na frente do VPS resolve TLS,
cache e proteção sem tocar no compose.

### 4. Operação
```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env logs -f api
docker compose ... restart api            # após git pull + build
docker compose ... exec db pg_dump -U nefron nefron > backup_$(date +%F).sql
```
Agende o backup no cron do VPS e teste a restauração periodicamente.

---

## Opção B — Hospedagem compartilhada: só o frontend

Use quando o backend estiver em outro lugar (VPS acima, Render, Fly.io…).

1. Frontend pronto: baixe o zip do branch `web-dist` (Code → Download ZIP) ou
   compile com `./deploy/build_web.sh https://api.seudominio.com.br` se a API
   ficar em OUTRO domínio (o build pronto assume API no MESMO domínio em /api).
2. hPanel → **Gerenciador de arquivos** (ou FTP) → envie o **conteúdo** de
   `deploy/web/` para `public_html/`.
3. No backend, inclua o domínio do site em `NEFRON_CORS_ORIGINS`
   (ex.: `'["https://seudominio.com.br"]'`).

Limitações: dois domínios/origens (site e API), CORS obrigatório, e o
backend continua precisando de um servidor Python + PostgreSQL em algum lugar.

---

## URL da API no frontend

O build é **universal por padrão**: sem `API_BASE_URL` definido, o app usa o
próprio domínio da página (o nginx do deploy faz o proxy de `/api/`). Só passe
`--dart-define=API_BASE_URL=...` quando a API estiver em outro domínio
(ex.: hospedagem compartilhada + backend externo).

Se o repositório estiver privado, o `git clone` no VPS pede um Personal Access
Token (GitHub → Settings → Developer settings → Tokens) na URL:
`https://SEU_TOKEN@github.com/rafaelfurtado123-alt/rx.git`.

## Checklist de produção
- [ ] `JWT_SECRET` forte e fora do git (`deploy/.env`)
- [ ] HTTPS ativo (Cloudflare ou certbot)
- [ ] Backup diário do PostgreSQL agendado
- [ ] `NEFRON_VIDAAS_*` reais após credenciamento na Valid (até lá: modo simulado)
- [ ] Firewall do VPS: só 22/80/443 abertas (hPanel → VPS → Firewall)
