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

# Frontend: coloque o build do Flutter em deploy/web/
#   - build feito em outra máquina: envie com scp/rsync
#   scp -r deploy/web root@SEU_IP:~/rx/deploy/
#   - ou instale o Flutter no próprio VPS e rode ./deploy/build_web.sh https://SEU-DOMINIO

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

1. Em uma máquina com Flutter: `./deploy/build_web.sh https://api.seudominio.com.br`
   (a URL é a do **backend**; o script já gera o `.htaccess` de SPA).
2. hPanel → **Gerenciador de arquivos** (ou FTP) → envie o **conteúdo** de
   `deploy/web/` para `public_html/`.
3. No backend, inclua o domínio do site em `NEFRON_CORS_ORIGINS`
   (ex.: `'["https://seudominio.com.br"]'`).

Limitações: dois domínios/origens (site e API), CORS obrigatório, e o
backend continua precisando de um servidor Python + PostgreSQL em algum lugar.

---

## Variáveis que importam no build do frontend

O app lê a URL da API em tempo de build:
```bash
flutter build web --release --dart-define=API_BASE_URL=https://nefron.seudominio.com.br
```
No deploy do VPS (Opção A) a API e o site compartilham o domínio — o nginx
faz o proxy de `/api/` — então `API_BASE_URL` é o próprio domínio do site.

## Checklist de produção
- [ ] `JWT_SECRET` forte e fora do git (`deploy/.env`)
- [ ] HTTPS ativo (Cloudflare ou certbot)
- [ ] Backup diário do PostgreSQL agendado
- [ ] `NEFRON_VIDAAS_*` reais após credenciamento na Valid (até lá: modo simulado)
- [ ] Firewall do VPS: só 22/80/443 abertas (hPanel → VPS → Firewall)
