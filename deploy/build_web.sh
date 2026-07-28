#!/usr/bin/env bash
# =============================================================================
# Néfron — build do app Flutter web para deploy
#   ./deploy/build_web.sh                      # UNIVERSAL: usa o domínio da
#                                              # própria página (nginx faz /api)
#   ./deploy/build_web.sh https://api.dominio  # API em domínio separado
# O resultado fica em deploy/web/ (servido pelo nginx do docker-compose) e
# também pode ser enviado ao public_html da hospedagem compartilhada.
# =============================================================================
set -euo pipefail

API_BASE_URL="${1:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/app"
flutter pub get
# --no-web-resources-cdn: empacota o CanvasKit localmente (sem depender do
# CDN da Google — melhor para disponibilidade, CSP e privacidade/LGPD)
DEFINES=()
if [ -n "$API_BASE_URL" ]; then
  DEFINES+=(--dart-define=API_BASE_URL="$API_BASE_URL")
fi
flutter build web --release --no-web-resources-cdn "${DEFINES[@]}"

rm -rf "$ROOT/deploy/web"
cp -r build/web "$ROOT/deploy/web"

# Hospedagem compartilhada (Apache/LiteSpeed): fallback de SPA via .htaccess
cat > "$ROOT/deploy/web/.htaccess" <<'EOF'
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^ index.html [L]
EOF

echo "OK — build em deploy/web/ (API: $API_BASE_URL)"
