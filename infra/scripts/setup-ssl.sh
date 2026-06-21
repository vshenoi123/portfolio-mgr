#!/bin/bash
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain>}"
EMAIL="${2:?Usage: $0 <domain> <email>}"

echo "Setting up SSL for $DOMAIN..."

# Stop nginx temporarily to free port 80
docker compose stop nginx

# Obtain certificate
docker run --rm \
    -v "$(pwd)/infra/nginx/letsencrypt:/etc/letsencrypt" \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive

# Update nginx.conf with real domain
sed -i '' "s/server_name portfolio.mgr/server_name $DOMAIN/g" infra/nginx/nginx.conf
sed -i '' "s|/etc/letsencrypt/live/portfolio.mgr|/etc/letsencrypt/live/$DOMAIN|g" infra/nginx/nginx.conf

# Start nginx
docker compose up -d nginx

# Setup auto-renewal cron
CRON_JOB="0 3 * * * cd $(pwd) && docker compose run --rm nginx certbot renew --nginx && docker compose exec nginx nginx -s reload"
(crontab -l 2>/dev/null | grep -v "certbot renew" || true; echo "$CRON_JOB") | crontab -

echo "SSL setup complete for $DOMAIN. Auto-renewal cron installed."