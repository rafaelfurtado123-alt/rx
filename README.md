# Néfron — build web pronto (deploy sem Flutter)

Conteúdo de `web/`: app Flutter compilado (universal — detecta o domínio
automaticamente; o backend deve responder em `/api` no mesmo domínio, como no
nginx do deploy). Gerado por `deploy/build_web.sh` no branch principal.

Uso no VPS:
  git clone -b web-dist --depth 1 <repo> webdist
  cp -r webdist/web deploy/web
Hospedagem compartilhada: envie o CONTEÚDO de `web/` para `public_html/`.
