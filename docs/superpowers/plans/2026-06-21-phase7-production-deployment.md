# Phase 7: Production Deployment, OCI + Advanced Features — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the full platform to OCI Free Tier with CI/CD, then add 6 advanced analytical features: Monte Carlo simulation, stress testing, economic calendar, earnings calendar, sector rotation analysis, and trade journal enhancements.

**Architecture:** Two work streams — (A) infra/deployment/CI/CD, (B) advanced feature engines under `backend/app/engines/`. Each new engine follows the package pattern: `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py`. Existing `docker-compose.yml` is restructured to include nginx + frontend + redis + backend. CI/CD via GitHub Actions to OCI Container Registry + SSH deploy. Monitoring via health checks + cron backups to OCI Object Storage.

**Tech Stack:** Docker Compose, nginx, Let's Encrypt (certbot), GitHub Actions, OCI CLI, numpy, scipy, httpx, pandas, FastAPI, Celery, pytest

**Testing Requirement:** Every major component must have tests covering normal operation, edge cases, and error states (including API failures for calendar features).

---

## Part A: OCI Deployment & CI/CD

### Task A1: Restructure Docker Compose — Add Frontend + Nginx

**Files:**
- Modify: `docker-compose.yml`
- Create: `infra/nginx/nginx.conf`
- Create: `infra/nginx/Dockerfile`
- Create: `infra/scripts/healthcheck.sh`
- Test: manual verification via `docker compose config`

- [ ] **Step 1: Verify docker compose config fails with current file referencing frontend**

Run: `cd /Users/vinayak.shenoi/Documents/workspace/portfolio-mgr && docker compose config 2>&1 | grep -q "frontend" && echo "PRESENT" || echo "MISSING"`
Expected: "MISSING" (frontend service not yet defined)

- [ ] **Step 2: Create nginx configuration**

Create `infra/nginx/nginx.conf`:
```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name portfolio.mgr;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name portfolio.mgr;

    ssl_certificate /etc/letsencrypt/live/portfolio.mgr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portfolio.mgr/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
}
```

- [ ] **Step 3: Create nginx Dockerfile**

Create `infra/nginx/Dockerfile`:
```dockerfile
FROM nginx:1.27-alpine

RUN apk add --no-cache certbot certbot-nginx

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 4: Create health check script**

Create `infra/scripts/healthcheck.sh`:
```bash
#!/bin/bash
set -euo pipefail

ENDPOINT="${1:-http://localhost:8000/health}"
MAX_RETRIES="${2:-30}"
SLEEP_SECONDS="${3:-5}"

echo "Health-checking $ENDPOINT..."

for i in $(seq 1 "$MAX_RETRIES"); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT" || true)
    if [ "$STATUS" = "200" ]; then
        echo "OK (attempt $i)"
        exit 0
    fi
    echo "Attempt $i: got $STATUS, retrying in ${SLEEP_SECONDS}s..."
    sleep "$SLEEP_SECONDS"
done

echo "FAILED after $MAX_RETRIES attempts"
exit 1
```

- [ ] **Step 5: Make healthcheck script executable**

Run: `chmod +x infra/scripts/healthcheck.sh`

- [ ] **Step 6: Rewrite docker-compose.yml with all 4 services**

Replace `docker-compose.yml`:
```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    expose:
      - "6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.25"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    expose:
      - "8000"
    env_file:
      - ./backend/.env
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_PATH=/data/portfolio.db
      - DATA_DIR=/data
    volumes:
      - data_volume:/data
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - ./backend/.env
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_PATH=/data/portfolio.db
      - DATA_DIR=/data
    volumes:
      - data_volume:/data
    depends_on:
      redis:
        condition: service_healthy
      backend:
        condition: service_started
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "0.5"

  beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - ./backend/.env
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_PATH=/data/portfolio.db
      - DATA_DIR=/data
    volumes:
      - data_volume:/data
    depends_on:
      redis:
        condition: service_healthy
      backend:
        condition: service_started
    command: celery -A app.celery_app beat --loglevel=info
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.25"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    expose:
      - "3000"
    environment:
      - NEXT_PUBLIC_API_URL=/api/v1
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000',r=>process.exit(r.statusCode===200?0:1))"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"

  nginx:
    build:
      context: ./infra/nginx
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - nginx_logs:/var/log/nginx
      - letsencrypt_data:/etc/letsencrypt
    depends_on:
      backend:
        condition: service_healthy
      frontend:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: "0.25"

volumes:
  redis_data:
  data_volume:
  nginx_logs:
  letsencrypt_data:
```

- [ ] **Step 7: Verify docker compose config**

Run: `cd /Users/vinayak.shenoi/Documents/workspace/portfolio-mgr && docker compose config --services | sort`
Expected output (order-independent):
```
backend
beat
frontend
nginx
redis
worker
```

- [ ] **Step 8: Commit**

```
git add docker-compose.yml infra/nginx/ infra/scripts/
git commit -m "feat: restructure docker-compose with frontend, nginx, resource limits, health checks"
```

---

### Task A2: Backend Health Endpoint + Config Updates for Production

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/health.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing test for health endpoint**

Create `backend/tests/test_health.py`:
```python
import pytest


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data

    def test_health_has_db_check(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "database" in data["checks"]
        assert data["checks"]["database"] in ("connected", "error")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: FAIL (no health.py, no client fixture)

- [ ] **Step 3: Add client fixture to conftest.py**

Append to `backend/tests/conftest.py`:
```python
@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 4: Create health.py**

Create `backend/app/health.py`:
```python
import time
import platform

_start_time: float = time.time()


def get_health() -> dict:
    from app.database import get_connection, close_connection
    from app.config import settings

    db_status = "error"
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "error"
    finally:
        try:
            close_connection()
        except Exception:
            pass

    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time, 2),
        "python_version": platform.python_version(),
        "checks": {
            "database": db_status,
        },
    }
```

- [ ] **Step 5: Update main.py to include health route**

Replace `backend/app/main.py`:
```python
from fastapi import FastAPI
from app.health import get_health

app = FastAPI(title="AI Portfolio Manager", version="1.0.0")


@app.get("/health")
async def health():
    return get_health()
```

- [ ] **Step 6: Update config.py with production settings**

Replace `backend/app/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    redis_url: str = "redis://localhost:6379/0"
    database_path: str = "/data/portfolio.db"
    data_dir: str = "/data"
    log_level: str = "INFO"
    environment: str = "development"

    # OCI
    oci_bucket_namespace: str = ""
    oci_bucket_name: str = ""
    oci_region: str = "us-ashburn-1"

    # FRED API
    fred_api_key: str = ""

    # Phase 4: Risk limits
    max_position_size_pct: float = 15.0
    max_sector_exposure_pct: float = 30.0
    max_portfolio_delta: float = 500.0
    max_portfolio_beta: float = 1.5
    max_concentration_pct: float = 40.0
    min_cash_reserve_pct: float = 10.0
    max_leverage: float = 1.0
    kelly_fraction: float = 0.25
    correlation_threshold: float = 0.80

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 7: Run tests to verify pass**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Run all existing tests to confirm no regressions**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 9: Commit**

```
git add backend/app/config.py backend/app/main.py backend/app/health.py backend/tests/test_health.py backend/tests/conftest.py
git commit -m "feat: add health endpoint, production config, test client fixture"
```

---

### Task A3: Let's Encrypt SSL Setup Script

**Files:**
- Create: `infra/scripts/setup-ssl.sh`
- Test: manual review (can't run without real domain)

- [ ] **Step 1: Create the SSL setup script**

Create `infra/scripts/setup-ssl.sh`:
```bash
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x infra/scripts/setup-ssl.sh`

- [ ] **Step 3: Commit**

```
git add infra/scripts/setup-ssl.sh
git commit -m "feat: add Let's Encrypt SSL setup script with auto-renewal cron"
```

---

### Task A4: OCI Object Storage Backup Script

**Files:**
- Create: `infra/scripts/backup-to-oci.sh`
- Create: `infra/scripts/schedule-backup.sh`
- Test: manual (requires OCI credentials)

- [ ] **Step 1: Create backup script**

Create `infra/scripts/backup-to-oci.sh`:
```bash
#!/bin/bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/portfolio-backup-${TIMESTAMP}.tar.gz"

echo "Starting backup at $TIMESTAMP..."

# Compress data directory (Parquet + DuckDB)
tar -czf "$BACKUP_FILE" \
    -C "$(dirname "$DATA_DIR")" \
    "$(basename "$DATA_DIR")"

# Upload to OCI Object Storage
oci os object put \
    --namespace "$OCI_BUCKET_NAMESPACE" \
    --bucket-name "$OCI_BUCKET_NAME" \
    --file "$BACKUP_FILE" \
    --name "backups/daily/$(date +%Y/%m)/portfolio-${TIMESTAMP}.tar.gz" \
    --region "$OCI_REGION"

# Cleanup local backup
rm -f "$BACKUP_FILE"

# Prune backups older than 90 days
BACKUP_PREFIX="backups/daily"
OLDER_THAN=$(date -d "-90 days" +%Y/%m/%d)
oci os object list \
    --namespace "$OCI_BUCKET_NAMESPACE" \
    --bucket-name "$OCI_BUCKET_NAME" \
    --prefix "$BACKUP_PREFIX" \
    --region "$OCI_REGION" \
    --query "data[?contains(name,'${OLDER_THAN}')].name" \
    --raw-output | while IFS= read -r obj; do
    oci os object delete \
        --namespace "$OCI_BUCKET_NAMESPACE" \
        --bucket-name "$OCI_BUCKET_NAME" \
        --object-name "$obj" \
        --region "$OCI_REGION" \
        --force
done

echo "Backup complete: $BACKUP_FILE uploaded, old backups pruned."
```

- [ ] **Step 2: Create backup scheduler script**

Create `infra/scripts/schedule-backup.sh`:
```bash
#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$PROJECT_DIR/backend/.env"

# Source environment variables for OCI
set -a
source "$ENV_FILE"
set +a

CRON_EXPR="0 4 * * *"
CRON_JOB="$CRON_EXPR cd $PROJECT_DIR && OCI_BUCKET_NAMESPACE=\"$OCI_BUCKET_NAMESPACE\" OCI_BUCKET_NAME=\"$OCI_BUCKET_NAME\" OCI_REGION=\"$OCI_REGION\" DATA_DIR=\"$DATA_DIR\" bash infra/scripts/backup-to-oci.sh >> /var/log/portfolio-backup.log 2>&1"

(crontab -l 2>/dev/null | grep -v "backup-to-oci" || true; echo "$CRON_JOB") | crontab -

echo "Daily backup cron installed (4 AM UTC, 90-day retention)."
```

- [ ] **Step 3: Make executable**

Run: `chmod +x infra/scripts/backup-to-oci.sh infra/scripts/schedule-backup.sh`

- [ ] **Step 4: Commit**

```
git add infra/scripts/backup-to-oci.sh infra/scripts/schedule-backup.sh
git commit -m "feat: add OCI Object Storage backup with 90-day retention and scheduler"
```

---

### Task A5: GitHub Actions CI/CD Pipeline

**Files:**
- Create: `.github/workflows/deploy.yml`
- Create: `infra/scripts/deploy-vm.sh`
- Test: manual (GitHub Actions can't run locally)

- [ ] **Step 1: Write the deploy workflow**

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to OCI

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  OCI_REGION: us-ashburn-1
  BACKEND_IMAGE: ${{ vars.OCI_REGISTRY }}/portfolio-mgr-backend
  FRONTEND_IMAGE: ${{ vars.OCI_REGISTRY }}/portfolio-mgr-frontend
  NGINX_IMAGE: ${{ vars.OCI_REGISTRY }}/portfolio-mgr-nginx

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - run: pip install -r backend/requirements.txt
        working-directory: backend

      - run: pip install pytest httpx
        working-directory: backend

      - run: python -m pytest tests/ -v
        working-directory: backend
        env:
          POLYGON_API_KEY: test
          DATABASE_PATH: /tmp/test.db
          DATA_DIR: /tmp/data

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install OCI CLI
        run: |
          curl -L -O https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh
          bash install.sh --accept-all-defaults
          echo "$HOME/bin" >> $GITHUB_PATH

      - name: Configure OCI CLI
        run: |
          oci setup config --cli-rc-file /dev/null \
            --region ${{ env.OCI_REGION }} \
            --tenancy-id ${{ secrets.OCI_TENANCY_ID }} \
            --user-id ${{ secrets.OCI_USER_ID }} \
            --key-file /dev/stdin \
            --pass-phrase "" <<< "${{ secrets.OCI_KEY_FILE }}"

      - name: Login to OCI Registry
        run: |
          oci auth session authenticate
          docker login ${{ vars.OCI_REGISTRY }} \
            -u ${{ secrets.OCI_USER }} \
            -p ${{ secrets.OCI_AUTH_TOKEN }}

      - name: Build and push backend
        run: |
          docker build -t $BACKEND_IMAGE:latest -t $BACKEND_IMAGE:${{ github.sha }} ./backend
          docker push $BACKEND_IMAGE:latest
          docker push $BACKEND_IMAGE:${{ github.sha }}

      - name: Build and push frontend
        run: |
          docker build -t $FRONTEND_IMAGE:latest -t $FRONTEND_IMAGE:${{ github.sha }} ./frontend
          docker push $FRONTEND_IMAGE:latest
          docker push $FRONTEND_IMAGE:${{ github.sha }}

      - name: Build and push nginx
        run: |
          docker build -t $NGINX_IMAGE:latest -t $NGINX_IMAGE:${{ github.sha }} ./infra/nginx
          docker push $NGINX_IMAGE:latest
          docker push $NGINX_IMAGE:${{ github.sha }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.VM_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.VM_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to VM
        run: |
          ssh opc@${{ secrets.VM_HOST }} bash -s << 'DEPLOY_SCRIPT'
            set -euo pipefail
            cd /home/opc/portfolio-mgr

            export OCI_REGISTRY=${{ vars.OCI_REGISTRY }}
            export BACKEND_IMAGE=${{ vars.OCI_REGISTRY }}/portfolio-mgr-backend
            export FRONTEND_IMAGE=${{ vars.OCI_REGISTRY }}/portfolio-mgr-frontend
            export NGINX_IMAGE=${{ vars.OCI_REGISTRY }}/portfolio-mgr-nginx

            echo "${{ secrets.OCI_AUTH_TOKEN }}" | docker login $OCI_REGISTRY \
              -u ${{ secrets.OCI_USER }} --password-stdin

            docker compose pull
            docker compose up -d --remove-orphans

            echo "Waiting for services..."
            sleep 10
            for i in $(seq 1 12); do
              STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || true)
              if [ "$STATUS" = "200" ]; then
                echo "Backend healthy (attempt $i)"
                break
              fi
              echo "Attempt $i: got $STATUS, retrying..."
              sleep 5
            done

            docker image prune -f
            echo "Deploy complete."
          DEPLOY_SCRIPT

      - name: Post-deploy health check
        run: |
          sleep 15
          curl -f --retry 5 --retry-delay 10 \
            "https://${{ secrets.VM_DOMAIN }}/health" || \
            curl -f --retry 5 --retry-delay 10 \
            "http://${{ secrets.VM_HOST }}:8000/health" || \
            (echo "Health check failed!" && exit 1)
```

- [ ] **Step 2: Create deploy helper script for VM**

Create `infra/scripts/deploy-vm.sh`:
```bash
#!/bin/bash
set -euo pipefail

echo "Pulling latest images..."
docker compose pull

echo "Restarting services..."
docker compose up -d --remove-orphans

echo "Running health checks..."
sleep 10
for i in $(seq 1 12); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || true)
    if [ "$STATUS" = "200" ]; then
        echo "Backend healthy (attempt $i)"
        break
    fi
    echo "Attempt $i: got $STATUS, retrying..."
    sleep 5
done

echo "Cleaning up old images..."
docker image prune -f

echo "Deploy complete."
```

- [ ] **Step 3: Make executable**

Run: `chmod +x infra/scripts/deploy-vm.sh`

- [ ] **Step 4: Commit**

```
git add .github/workflows/deploy.yml infra/scripts/deploy-vm.sh
git commit -m "feat: add GitHub Actions CI/CD pipeline to OCI with test, build, push, deploy"
```

---

### Task A6: Uptime Monitoring Cron

**Files:**
- Create: `infra/scripts/uptime-monitor.sh`
- Test: manual

- [ ] **Step 1: Create uptime monitoring script**

Create `infra/scripts/uptime-monitor.sh`:
```bash
#!/bin/bash
set -euo pipefail

HEALTH_URL="${1:-http://localhost:8000/health}"
LOG_FILE="${2:-/var/log/portfolio-uptime.log}"
TIMESTAMP=$(date +%Y-%m-%d_%H:%M:%S)

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$HEALTH_URL" || echo "-1")

if [ "$STATUS" = "200" ]; then
    echo "$TIMESTAMP | UP | ${RESPONSE_TIME}s | $HEALTH_URL" >> "$LOG_FILE"
else
    echo "$TIMESTAMP | DOWN ($STATUS) | ${RESPONSE_TIME}s | $HEALTH_URL" >> "$LOG_FILE"
fi

# Trim log to last 10000 lines
tail -n 10000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x infra/scripts/uptime-monitor.sh`
Review: The script is callable from crontab every 5 minutes: `*/5 * * * * /path/to/infra/scripts/uptime-monitor.sh`

- [ ] **Step 3: Commit**

```
git add infra/scripts/uptime-monitor.sh
git commit -m "feat: add uptime monitoring script with log rotation"
```

---

### Task A7: VM First-Run Init Script

**Files:**
- Create: `infra/setup/vm-init.sh`

- [ ] **Step 1: Create VM init script**

Create `infra/setup/vm-init.sh`:
```bash
#!/bin/bash
set -euo pipefail

echo "=== AI Portfolio Manager — OCI VM Initialization ==="

echo "[1/6] Updating system packages..."
sudo dnf update -y

echo "[2/6] Installing Docker..."
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker opc

echo "[3/6] Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo "[4/6] Installing OCI CLI..."
curl -L -O https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh
bash install.sh --accept-all-defaults
rm install.sh

echo "[5/6] Creating project directory..."
mkdir -p /home/opc/portfolio-mgr
git clone https://github.com/your-org/portfolio-mgr.git /home/opc/portfolio-mgr

echo "[6/6] Setting up backup cron..."
cd /home/opc/portfolio-mgr
bash infra/scripts/schedule-backup.sh

echo "=== Init complete! ==="
echo "Next steps:"
echo "  1. cd /home/opc/portfolio-mgr"
echo "  2. cp backend/.env.example backend/.env && vi backend/.env"
echo "  3. Copy GitHub Actions secrets from the repo settings"
echo "  4. Run: docker compose up -d"
echo "  5. Run: bash infra/scripts/setup-ssl.sh yourdomain.com you@email.com"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x infra/setup/vm-init.sh`

- [ ] **Step 3: Commit**

```
git add infra/setup/vm-init.sh
git commit -m "feat: add VM initialization and first-run setup script"
```

---

## Part B: Advanced Features

### Task B1: Monte Carlo Simulation Engine

**Files:**
- Create: `backend/app/engines/monte_carlo/__init__.py`
- Create: `backend/app/engines/monte_carlo/schemas.py`
- Create: `backend/app/engines/monte_carlo/service.py`
- Create: `backend/app/engines/monte_carlo/router.py`
- Create: `backend/app/engines/monte_carlo/tasks.py`
- Test: `backend/tests/engines/monte_carlo/__init__.py`
- Test: `backend/tests/engines/monte_carlo/test_service.py`
- Test: `backend/tests/engines/monte_carlo/test_schemas.py`
- Test: `backend/tests/engines/monte_carlo/test_router.py`

- [ ] **Step 1: Write failing tests for Monte Carlo schemas**

Create `backend/tests/engines/monte_carlo/__init__.py` (empty file)

Create `backend/tests/engines/monte_carlo/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError


class TestMonteCarloRequest:
    def test_valid_request(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        req = MonteCarloRequest(
            ticker="SPY",
            days=252,
            simulations=10000,
            method="historical",
        )
        assert req.ticker == "SPY"
        assert req.simulations == 10000

    def test_default_values(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        req = MonteCarloRequest(ticker="AAPL")
        assert req.days == 252
        assert req.simulations == 10000
        assert req.method == "historical"

    def test_invalid_method(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        with pytest.raises(ValidationError):
            MonteCarloRequest(ticker="AAPL", method="bayesian")

    def test_invalid_simulations_count(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        with pytest.raises(ValidationError):
            MonteCarloRequest(ticker="AAPL", simulations=50)

    def test_negative_days(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        with pytest.raises(ValidationError):
            MonteCarloRequest(ticker="AAPL", days=-1)


class TestMonteCarloResult:
    def test_valid_result(self):
        from app.engines.monte_carlo.schemas import MonteCarloResult
        import numpy as np
        result = MonteCarloResult(
            ticker="SPY",
            simulations=1000,
            days=252,
            method="historical",
            final_prices=np.array([100.0, 110.0, 95.0]),
            returns=np.array([0.01, 0.10, -0.05]),
            var_95=0.05,
            var_99=0.08,
            cvar_95=0.07,
            max_drawdowns=np.array([0.10, 0.15, 0.08]),
            median_final=105.0,
            mean_final=106.0,
            std_final=15.0,
        )
        assert result.var_95 == 0.05
        assert result.ticker == "SPY"

    def test_var_95_less_than_var_99(self):
        from app.engines.monte_carlo.schemas import MonteCarloResult
        import numpy as np
        with pytest.raises(ValidationError):
            MonteCarloResult(
                ticker="SPY",
                simulations=1000,
                days=252,
                method="historical",
                final_prices=np.array([100.0]),
                returns=np.array([0.01]),
                var_95=0.10,
                var_99=0.05,
                cvar_95=0.07,
                max_drawdowns=np.array([0.10]),
                median_final=105.0,
                mean_final=106.0,
                std_final=15.0,
            )


class TestPortfolioMonteCarloRequest:
    def test_valid_request(self):
        from app.engines.monte_carlo.schemas import PortfolioMonteCarloRequest
        req = PortfolioMonteCarloRequest(
            positions=[{"ticker": "AAPL", "weight": 0.6}, {"ticker": "MSFT", "weight": 0.4}],
            days=252,
            simulations=10000,
        )
        assert len(req.positions) == 2

    def test_weights_must_sum_to_one(self):
        from app.engines.monte_carlo.schemas import PortfolioMonteCarloRequest
        with pytest.raises(ValidationError):
            PortfolioMonteCarloRequest(
                positions=[{"ticker": "AAPL", "weight": 0.8}, {"ticker": "MSFT", "weight": 0.3}],
                days=252,
                simulations=10000,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/engines/monte_carlo/ -v`
Expected: FAIL (no module)

- [ ] **Step 3: Create Monte Carlo schemas**

Create `backend/app/engines/monte_carlo/__init__.py` (empty)

Create `backend/app/engines/monte_carlo/schemas.py`:
```python
from pydantic import BaseModel, field_validator, model_validator
from typing import Literal
import numpy as np


class MonteCarloRequest(BaseModel):
    ticker: str
    days: int = 252
    simulations: int = 10000
    method: Literal["historical", "parametric"] = "historical"

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("simulations")
    @classmethod
    def simulations_must_be_at_least_1000(cls, v: int) -> int:
        if v < 1000:
            raise ValueError("simulations must be >= 1000")
        return v

    @field_validator("days")
    @classmethod
    def days_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("days must be positive")
        return v


class MonteCarloResult(BaseModel):
    ticker: str
    simulations: int
    days: int
    method: str
    final_prices: np.ndarray
    returns: np.ndarray
    var_95: float
    var_99: float
    cvar_95: float
    max_drawdowns: np.ndarray
    median_final: float
    mean_final: float
    std_final: float

    @model_validator(mode="after")
    def var_95_less_than_var_99(self):
        if self.var_95 >= self.var_99:
            raise ValueError("var_95 must be less than var_99")
        return self

    class Config:
        arbitrary_types_allowed = True


class PortfolioMonteCarloRequest(BaseModel):
    positions: list[dict]
    days: int = 252
    simulations: int = 10000

    @field_validator("simulations")
    @classmethod
    def simulations_must_be_at_least_1000(cls, v: int) -> int:
        if v < 1000:
            raise ValueError("simulations must be >= 1000")
        return v

    @model_validator(mode="after")
    def weights_must_sum_to_one(self):
        total = sum(p["weight"] for p in self.positions)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"position weights must sum to 1.0, got {total}")
        return self
```

- [ ] **Step 4: Write failing tests for Monte Carlo service**

Create `backend/tests/engines/monte_carlo/test_service.py`:
```python
import pytest
import numpy as np


class TestHistoricalBootstrap:
    def test_simulate_returns_array_of_correct_shape(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        returns = np.array([0.01, -0.02, 0.005, -0.01, 0.02, 0.015, -0.005, 0.008])
        paths = service.historical_bootstrap(returns, days=252, simulations=1000)
        assert paths.shape == (1000, 252)

    def test_historical_bootstrap_uses_empirical_returns(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        returns = np.array([0.01])
        paths = service.historical_bootstrap(returns, days=10, simulations=5)
        assert np.allclose(paths, 0.01)

    def test_historical_bootstrap_with_zero_returns(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        returns = np.zeros(10)
        paths = service.historical_bootstrap(returns, days=100, simulations=100)
        assert np.allclose(paths, 0.0)


class TestParametricMethod:
    def test_simulate_returns_array_of_correct_shape(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        mu = 0.0005
        sigma = 0.015
        paths = service.parametric_simulation(mu, sigma, days=252, simulations=1000)
        assert paths.shape == (1000, 252)

    def test_parametric_uses_log_normal_property(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        paths = service.parametric_simulation(0.0, 0.0, days=10, simulations=10)
        assert np.allclose(paths, 0.0)

    def test_parametric_positive_std(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        with pytest.raises(ValueError):
            service.parametric_simulation(0.0, -0.01, days=10, simulations=10)


class TestVaRCVaR:
    def test_var_95_is_negative_or_zero(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        np.random.seed(42)
        paths = np.random.randn(10000, 252) * 0.02
        metrics = service.compute_risk_metrics(paths)
        assert metrics["var_95"] <= 0
        assert metrics["var_99"] <= metrics["var_95"]

    def test_cvar_95_is_below_var_95(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        np.random.seed(42)
        paths = np.random.randn(10000, 252) * 0.02
        metrics = service.compute_risk_metrics(paths)
        assert metrics["cvar_95"] <= metrics["var_95"]

    def test_max_drawdown_is_negative_or_zero(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        np.random.seed(42)
        paths = np.random.randn(1000, 252) * 0.02
        metrics = service.compute_risk_metrics(paths)
        assert np.all(metrics["max_drawdowns"] <= 0)
        assert len(metrics["max_drawdowns"]) == 1000


class TestFullSimulation:
    def test_run_simulation_returns_monte_carlo_result(self):
        from app.engines.monte_carlo.service import MonteCarloService
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        service = MonteCarloService()
        np.random.seed(42)
        req = MonteCarloRequest(ticker="SPY", days=252, simulations=1000, method="historical")
        result = service.run_simulation(req, historical_returns=np.random.randn(500) * 0.01)
        assert result.ticker == "SPY"
        assert result.var_95 <= 0
        assert result.var_99 <= result.var_95
        assert result.cvar_95 <= result.var_95
        assert len(result.final_prices) == 1000
        assert result.method == "historical"

    def test_run_simulation_parametric(self):
        from app.engines.monte_carlo.service import MonteCarloService
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        service = MonteCarloService()
        np.random.seed(42)
        req = MonteCarloRequest(ticker="SPY", days=252, simulations=1000, method="parametric")
        result = service.run_simulation(req, historical_returns=np.random.randn(500) * 0.01)
        assert result.ticker == "SPY"
        assert result.method == "parametric"
        assert result.var_95 <= 0

    def test_run_portfolio_simulation(self):
        from app.engines.monte_carlo.service import MonteCarloService
        from app.engines.monte_carlo.schemas import PortfolioMonteCarloRequest
        service = MonteCarloService()
        np.random.seed(42)
        req = PortfolioMonteCarloRequest(
            positions=[{"ticker": "AAPL", "weight": 0.6}, {"ticker": "MSFT", "weight": 0.4}],
            days=252,
            simulations=1000,
        )
        returns_dict = {"AAPL": np.random.randn(500) * 0.015, "MSFT": np.random.randn(500) * 0.012}
        result = service.run_portfolio_simulation(req, returns_dict)
        assert result["var_95"] <= 0
        assert result["var_99"] <= result["var_95"]
```

- [ ] **Step 5: Run the tests again to verify they still fail**

Run: `cd backend && python -m pytest tests/engines/monte_carlo/ -v`
Expected: FAIL (no service module)

- [ ] **Step 6: Create Monte Carlo service**

Create `backend/app/engines/monte_carlo/service.py`:
```python
import numpy as np
from app.engines.monte_carlo.schemas import (
    MonteCarloRequest,
    MonteCarloResult,
    PortfolioMonteCarloRequest,
)


class MonteCarloService:
    def historical_bootstrap(
        self, returns: np.ndarray, days: int, simulations: int
    ) -> np.ndarray:
        n = len(returns)
        indices = np.random.randint(0, n, size=(simulations, days))
        sampled = returns[indices]
        return sampled

    def parametric_simulation(
        self, mu: float, sigma: float, days: int, simulations: int
    ) -> np.ndarray:
        if sigma < 0:
            raise ValueError("sigma must be non-negative")
        daily_returns = np.random.normal(mu, sigma, size=(simulations, days))
        return daily_returns

    def compute_risk_metrics(self, price_paths: np.ndarray) -> dict:
        final_prices = price_paths[:, -1]
        returns = (price_paths[:, 1:] - price_paths[:, :-1]) / price_paths[:, :-1]

        var_95 = float(np.percentile(returns[:, -1], 5))
        var_99 = float(np.percentile(returns[:, -1], 1))

        tail_95 = returns[:, -1] <= var_95
        cvar_95 = float(returns[:, -1][tail_95].mean()) if tail_95.any() else var_95

        peak = np.maximum.accumulate(price_paths, axis=1)
        drawdowns = (price_paths - peak) / peak
        max_drawdowns = drawdowns.min(axis=1)

        return {
            "final_prices": final_prices,
            "returns": returns,
            "var_95": var_95,
            "var_99": var_99,
            "cvar_95": cvar_95,
            "max_drawdowns": max_drawdowns,
            "median_final": float(np.median(final_prices)),
            "mean_final": float(np.mean(final_prices)),
            "std_final": float(np.std(final_prices)),
        }

    def run_simulation(
        self, req: MonteCarloRequest, historical_returns: np.ndarray
    ) -> MonteCarloResult:
        if req.method == "historical":
            daily_returns = self.historical_bootstrap(
                historical_returns, req.days, req.simulations
            )
        else:
            mu = float(np.mean(historical_returns))
            sigma = float(np.std(historical_returns))
            daily_returns = self.parametric_simulation(
                mu, sigma, req.days, req.simulations
            )

        price_paths = 100.0 * np.exp(np.cumsum(daily_returns, axis=1))
        metrics = self.compute_risk_metrics(price_paths)

        return MonteCarloResult(
            ticker=req.ticker,
            simulations=req.simulations,
            days=req.days,
            method=req.method,
            final_prices=metrics["final_prices"],
            returns=metrics["returns"],
            var_95=metrics["var_95"],
            var_99=metrics["var_99"],
            cvar_95=metrics["cvar_95"],
            max_drawdowns=metrics["max_drawdowns"],
            median_final=metrics["median_final"],
            mean_final=metrics["mean_final"],
            std_final=metrics["std_final"],
        )

    def run_portfolio_simulation(
        self, req: PortfolioMonteCarloRequest, returns_dict: dict[str, np.ndarray]
    ) -> dict:
        portfolio_daily_returns = np.zeros((req.simulations, req.days))
        for pos in req.positions:
            ticker = pos["ticker"]
            weight = pos["weight"]
            ret = returns_dict[ticker]
            method = getattr(req, "method", "historical")
            if method == "historical":
                sim_returns = self.historical_bootstrap(ret, req.days, req.simulations)
            else:
                mu = float(np.mean(ret))
                sigma = float(np.std(ret))
                sim_returns = self.parametric_simulation(mu, sigma, req.days, req.simulations)
            portfolio_daily_returns += weight * sim_returns

        price_paths = 100.0 * np.exp(np.cumsum(portfolio_daily_returns, axis=1))
        metrics = self.compute_risk_metrics(price_paths)
        return metrics
```

- [ ] **Step 7: Create Monte Carlo router**

Create `backend/app/engines/monte_carlo/router.py`:
```python
from fastapi import APIRouter, HTTPException
import numpy as np
from app.engines.monte_carlo.schemas import MonteCarloRequest, PortfolioMonteCarloRequest
from app.engines.monte_carlo.service import MonteCarloService

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])
service = MonteCarloService()


@router.post("/monte-carlo/{ticker}")
async def run_monte_carlo(ticker: str, req: MonteCarloRequest | None = None):
    if req is None:
        req = MonteCarloRequest(ticker=ticker)
    req.ticker = ticker.upper()

    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)
        ohlcv = data_service.load_ohlcv(ticker, days=756)
        if ohlcv.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")
        returns = ohlcv["close"].pct_change().dropna().values.astype(np.float64)
        if len(returns) < 20:
            raise HTTPException(status_code=400, detail=f"Not enough data for {ticker}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = service.run_simulation(req, returns)
    return result.model_dump()


@router.post("/monte-carlo/portfolio")
async def run_portfolio_monte_carlo(req: PortfolioMonteCarloRequest):
    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)

        returns_dict = {}
        for pos in req.positions:
            ticker = pos["ticker"]
            ohlcv = data_service.load_ohlcv(ticker, days=756)
            if ohlcv.empty:
                raise HTTPException(status_code=404, detail=f"No data for {ticker}")
            ret = ohlcv["close"].pct_change().dropna().values.astype(np.float64)
            if len(ret) < 20:
                raise HTTPException(status_code=400, detail=f"Not enough data for {ticker}")
            returns_dict[ticker] = ret
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = service.run_portfolio_simulation(req, returns_dict)

    serializable = {}
    for k, v in result.items():
        if isinstance(v, np.ndarray):
            serializable[k] = v.tolist()
        else:
            serializable[k] = v
    return serializable
```

- [ ] **Step 8: Create Monte Carlo tasks**

Create `backend/app/engines/monte_carlo/tasks.py`:
```python
from celery import shared_task
from app.engines.monte_carlo.service import MonteCarloService
from app.engines.monte_carlo.schemas import MonteCarloRequest
import numpy as np

service = MonteCarloService()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_daily_monte_carlo(self, ticker: str):
    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)
        ohlcv = data_service.load_ohlcv(ticker, days=756)
        if ohlcv.empty:
            return {"ticker": ticker, "status": "no_data"}
        returns = ohlcv["close"].pct_change().dropna().values.astype(np.float64)
        req = MonteCarloRequest(ticker=ticker)
        result = service.run_simulation(req, returns)
        return {"ticker": ticker, "status": "success", "var_95": result.var_95}
    except Exception as exc:
        raise self.retry(exc=exc)
```

- [ ] **Step 9: Register router in main app**

Append to `backend/app/main.py`:
```python
from app.engines.monte_carlo.router import router as monte_carlo_router
app.include_router(monte_carlo_router)
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/monte_carlo/ -v`
Expected: PASS

- [ ] **Step 11: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 12: Commit**

```
git add backend/app/engines/monte_carlo/ backend/tests/engines/monte_carlo/
git commit -m "feat: add Monte Carlo simulation engine with historical bootstrap and parametric methods"
```

---

### Task B2: Stress Testing Engine

**Files:**
- Create: `backend/app/engines/stress_test/__init__.py`
- Create: `backend/app/engines/stress_test/schemas.py`
- Create: `backend/app/engines/stress_test/service.py`
- Create: `backend/app/engines/stress_test/router.py`
- Test: `backend/tests/engines/stress_test/__init__.py`
- Test: `backend/tests/engines/stress_test/test_service.py`
- Test: `backend/tests/engines/stress_test/test_schemas.py`

- [ ] **Step 1: Write failing tests for stress test schemas**

Create `backend/tests/engines/stress_test/__init__.py` (empty)

Create `backend/tests/engines/stress_test/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError


class TestScenarioDefinition:
    def test_predefined_scenario(self):
        from app.engines.stress_test.schemas import ScenarioDefinition
        s = ScenarioDefinition(name="2008 Crash", equity_shock=-0.50)
        assert s.name == "2008 Crash"
        assert s.equity_shock == -0.50

    def test_custom_scenario_with_bond_shift(self):
        from app.engines.stress_test.schemas import ScenarioDefinition
        s = ScenarioDefinition(
            name="Custom", equity_shock=-0.20,
            bond_yield_shift=0.50, vol_shock=0.30, dollar_shock=0.05,
        )
        assert s.bond_yield_shift == 0.50

    def test_invalid_equity_shock(self):
        from app.engines.stress_test.schemas import ScenarioDefinition
        with pytest.raises(ValidationError):
            ScenarioDefinition(name="Bad", equity_shock=0.10)


class TestStressTestRequest:
    def test_valid_request(self):
        from app.engines.stress_test.schemas import StressTestRequest
        req = StressTestRequest(
            positions=[{"ticker": "AAPL", "beta": 1.2, "market_value": 10000}],
        )
        assert len(req.positions) == 1

    def test_request_with_custom_scenarios(self):
        from app.engines.stress_test.schemas import StressTestRequest
        req = StressTestRequest(
            positions=[{"ticker": "AAPL", "beta": 1.2, "market_value": 10000}],
            custom_scenarios=[{"name": "My Scenario", "equity_shock": -0.15}],
        )
        assert len(req.custom_scenarios) == 1


class TestStressTestResult:
    def test_valid_result(self):
        from app.engines.stress_test.schemas import StressTestResult
        r = StressTestResult(
            scenario_name="2008 Crash",
            total_portfolio_impact=-5000.0,
            total_portfolio_impact_pct=-0.15,
            position_impacts=[{"ticker": "AAPL", "impact": -3000.0, "impact_pct": -0.18}],
            top_vulnerable=["AAPL"],
        )
        assert r.total_portfolio_impact == -5000.0
        assert r.top_vulnerable == ["AAPL"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/engines/stress_test/ -v`
Expected: FAIL

- [ ] **Step 3: Create stress test schemas**

Create `backend/app/engines/stress_test/__init__.py` (empty)

Create `backend/app/engines/stress_test/schemas.py`:
```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal


class ScenarioDefinition(BaseModel):
    name: str
    equity_shock: float = Field(..., lt=0, description="Expected equity return shock (e.g., -0.50 for -50%)")
    bond_yield_shift: float = 0.0
    vol_shock: float = 0.0
    dollar_shock: float = 0.0
    credit_spread_widen: float = 0.0

    @field_validator("equity_shock")
    @classmethod
    def equity_shock_negative(cls, v: float) -> float:
        if v >= 0:
            raise ValueError("equity_shock must be negative")
        return v


PREDEFINED_SCENARIOS: dict[str, ScenarioDefinition] = {
    "2008 Crash": ScenarioDefinition(
        name="2008 Crash", equity_shock=-0.50, vol_shock=0.80, credit_spread_widen=0.05,
    ),
    "COVID Crash": ScenarioDefinition(
        name="COVID Crash", equity_shock=-0.35, vol_shock=0.60, bond_yield_shift=-0.01,
    ),
    "Dot-com Bust": ScenarioDefinition(
        name="Dot-com Bust", equity_shock=-0.49, vol_shock=0.50,
    ),
    "2022 Bear Market": ScenarioDefinition(
        name="2022 Bear Market", equity_shock=-0.25, vol_shock=0.30, bond_yield_shift=0.02,
    ),
    "1987 Black Monday": ScenarioDefinition(
        name="1987 Black Monday", equity_shock=-0.23, vol_shock=1.0,
    ),
}


class PortfolioPosition(BaseModel):
    ticker: str
    beta: float = 1.0
    market_value: float
    sector: str = "Unknown"

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class StressTestRequest(BaseModel):
    positions: list[PortfolioPosition]
    scenarios: list[str] = list(PREDEFINED_SCENARIOS.keys())
    custom_scenarios: list[ScenarioDefinition] = []


class StressTestResult(BaseModel):
    scenario_name: str
    total_portfolio_impact: float
    total_portfolio_impact_pct: float
    position_impacts: list[dict]
    top_vulnerable: list[str]
```

- [ ] **Step 4: Write failing tests for stress test service**

Create `backend/tests/engines/stress_test/test_service.py`:
```python
import pytest


class TestStressService:
    def test_run_single_position_stress(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "AAPL", "beta": 1.2, "market_value": 10000, "sector": "Technology"},
        ]
        results = service.run_stress_test(positions, scenarios=["2008 Crash"])
        assert len(results) == 1
        assert results[0].scenario_name == "2008 Crash"
        assert results[0].total_portfolio_impact < 0
        assert results[0].total_portfolio_impact == -6000.0

    def test_run_multi_position_stress(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "AAPL", "beta": 1.2, "market_value": 10000, "sector": "Technology"},
            {"ticker": "TLT", "beta": -0.3, "market_value": 5000, "sector": "Treasuries"},
        ]
        results = service.run_stress_test(positions, scenarios=["2022 Bear Market"])
        assert len(results) == 1
        assert results[0].total_portfolio_impact == -2625.0

    def test_custom_scenario(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "AAPL", "beta": 1.0, "market_value": 10000, "sector": "Technology"},
        ]
        custom = [{"name": "Custom", "equity_shock": -0.10, "bond_yield_shift": 0.0,
                   "vol_shock": 0.0, "dollar_shock": 0.0, "credit_spread_widen": 0.0}]
        results = service.run_stress_test(positions, custom_scenarios=custom)
        assert len(results) == 1
        assert results[0].total_portfolio_impact == -1000.0

    def test_top_vulnerable_identified(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "AAPL", "beta": 2.0, "market_value": 10000, "sector": "Technology"},
            {"ticker": "KO", "beta": 0.5, "market_value": 10000, "sector": "Consumer Staples"},
        ]
        results = service.run_stress_test(positions, scenarios=["2008 Crash"])
        assert "AAPL" in results[0].top_vulnerable

    def test_empty_positions(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        results = service.run_stress_test([], scenarios=["2008 Crash"])
        assert len(results) == 1
        assert results[0].total_portfolio_impact == 0.0
        assert results[0].top_vulnerable == []

    def test_all_predefined_scenarios(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "SPY", "beta": 1.0, "market_value": 10000, "sector": "ETF"},
        ]
        results = service.run_stress_test(positions)
        assert len(results) == 5
```

- [ ] **Step 5: Create stress test service**

Create `backend/app/engines/stress_test/service.py`:
```python
from app.engines.stress_test.schemas import (
    PortfolioPosition,
    StressTestRequest,
    StressTestResult,
    ScenarioDefinition,
    PREDEFINED_SCENARIOS,
)


class StressTestService:
    def _compute_position_impact(self, position: dict, scenario: ScenarioDefinition) -> float:
        beta = position["beta"]
        market_value = position["market_value"]
        equity_impact = market_value * beta * scenario.equity_shock
        vol_impact = market_value * scenario.vol_shock * 0.01
        return equity_impact + vol_impact

    def run_stress_test(
        self,
        positions_data: list[dict],
        scenarios: list[str] | None = None,
        custom_scenarios: list[dict] | None = None,
    ) -> list[StressTestResult]:
        if scenarios is None:
            scenarios = list(PREDEFINED_SCENARIOS.keys())

        scenario_defs: list[ScenarioDefinition] = []
        for name in scenarios:
            if name in PREDEFINED_SCENARIOS:
                scenario_defs.append(PREDEFINED_SCENARIOS[name])

        if custom_scenarios:
            for cs in custom_scenarios:
                scenario_defs.append(ScenarioDefinition(**cs))

        results: list[StressTestResult] = []
        for scenario in scenario_defs:
            position_impacts: list[dict] = []
            total_impact = 0.0
            total_value = sum(p["market_value"] for p in positions_data)

            for pos in positions_data:
                impact = self._compute_position_impact(pos, scenario)
                impact_pct = impact / pos["market_value"] if pos["market_value"] > 0 else 0
                position_impacts.append({
                    "ticker": pos["ticker"],
                    "impact": round(impact, 2),
                    "impact_pct": round(impact_pct, 4),
                })
                total_impact += impact

            sorted_impacts = sorted(position_impacts, key=lambda x: x["impact"])
            top_vulnerable = [p["ticker"] for p in sorted_impacts[:3] if p["impact"] < 0]

            results.append(StressTestResult(
                scenario_name=scenario.name,
                total_portfolio_impact=round(total_impact, 2),
                total_portfolio_impact_pct=round(
                    total_impact / total_value if total_value > 0 else 0, 4
                ),
                position_impacts=position_impacts,
                top_vulnerable=top_vulnerable,
            ))

        return results
```

- [ ] **Step 6: Create stress test router**

Create `backend/app/engines/stress_test/router.py`:
```python
from fastapi import APIRouter
from app.engines.stress_test.schemas import StressTestRequest, PREDEFINED_SCENARIOS
from app.engines.stress_test.service import StressTestService

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])
service = StressTestService()


@router.get("/stress-test/scenarios")
async def list_scenarios():
    return {name: s.model_dump() for name, s in PREDEFINED_SCENARIOS.items()}


@router.post("/stress-test")
async def run_stress_test(req: StressTestRequest):
    positions_data = [p.model_dump() for p in req.positions]
    custom_data = [s.model_dump() for s in req.custom_scenarios] if req.custom_scenarios else None
    results = service.run_stress_test(positions_data, scenarios=req.scenarios, custom_scenarios=custom_data)
    return [r.model_dump() for r in results]
```

- [ ] **Step 7: Register router in main app**

Append to `backend/app/main.py`:
```python
from app.engines.stress_test.router import router as stress_test_router
app.include_router(stress_test_router)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/stress_test/ -v`
Expected: PASS

- [ ] **Step 9: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 10: Commit**

```
git add backend/app/engines/stress_test/ backend/tests/engines/stress_test/
git commit -m "feat: add stress testing engine with 5 predefined crash scenarios and custom scenario support"
```

---

### Task B3: Economic Calendar Integration

**Files:**
- Create: `backend/app/engines/economic_calendar/__init__.py`
- Create: `backend/app/engines/economic_calendar/schemas.py`
- Create: `backend/app/engines/economic_calendar/service.py`
- Create: `backend/app/engines/economic_calendar/router.py`
- Create: `backend/app/engines/economic_calendar/tasks.py`
- Test: `backend/tests/engines/economic_calendar/__init__.py`
- Test: `backend/tests/engines/economic_calendar/test_service.py`
- Test: `backend/tests/engines/economic_calendar/test_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/engines/economic_calendar/__init__.py` (empty)

Create `backend/tests/engines/economic_calendar/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone


class TestEconomicEvent:
    def test_valid_event(self):
        from app.engines.economic_calendar.schemas import EconomicEvent
        ev = EconomicEvent(
            title="CPI MoM",
            event_date=datetime.now(timezone.utc),
            impact="high",
            category="inflation",
            forecast=0.3,
            previous=0.2,
        )
        assert ev.title == "CPI MoM"
        assert ev.impact == "high"

    def test_invalid_impact(self):
        from app.engines.economic_calendar.schemas import EconomicEvent
        with pytest.raises(ValidationError):
            EconomicEvent(
                title="CPI", event_date=datetime.now(timezone.utc),
                impact="critical", category="inflation",
            )

    def test_invalid_category(self):
        from app.engines.economic_calendar.schemas import EconomicEvent
        with pytest.raises(ValidationError):
            EconomicEvent(
                title="CPI", event_date=datetime.now(timezone.utc),
                impact="high", category="weather",
            )


class TestEventImpactAnalysis:
    def test_analyze_impact_on_positions(self):
        from app.engines.economic_calendar.schemas import EventImpactAnalysis
        analysis = EventImpactAnalysis(
            event_title="FOMC Rate Decision",
            impact_level="high",
            affected_tickers=["SPY", "TLT", "AAPL"],
            reasoning="Rate decisions affect discount rates",
            event_date=datetime.now(timezone.utc),
        )
        assert "SPY" in analysis.affected_tickers
```

- [ ] **Step 2: Run tests to verify fail**

Run: `cd backend && python -m pytest tests/engines/economic_calendar/ -v`
Expected: FAIL

- [ ] **Step 3: Create economic calendar schemas**

Create `backend/app/engines/economic_calendar/__init__.py` (empty)

Create `backend/app/engines/economic_calendar/schemas.py`:
```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator

ImpactLevel = Literal["low", "medium", "high"]
EventCategory = Literal[
    "inflation", "employment", "gdp", "central_bank", "housing",
    "manufacturing", "consumer", "trade", "confidence",
]


class EconomicEvent(BaseModel):
    title: str
    event_date: datetime
    impact: ImpactLevel
    category: EventCategory
    forecast: float | None = None
    previous: float | None = None
    actual: float | None = None
    description: str = ""
    source: str = "fred"

    @field_validator("impact")
    @classmethod
    def validate_impact(cls, v: str) -> str:
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"impact must be one of {allowed}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {
            "inflation", "employment", "gdp", "central_bank", "housing",
            "manufacturing", "consumer", "trade", "confidence",
        }
        if v not in allowed:
            raise ValueError(f"category must be one of {allowed}")
        return v


class EventImpactAnalysis(BaseModel):
    event_title: str
    impact_level: str
    affected_tickers: list[str]
    reasoning: str
    event_date: datetime
```

- [ ] **Step 4: Write failing service tests**

Create `backend/tests/engines/economic_calendar/test_service.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


class TestFREDService:
    def test_fetch_events_returns_list(self):
        from app.engines.economic_calendar.service import EconomicCalendarService
        service = EconomicCalendarService(api_key="test_key")
        events = service._fetch_from_fred()
        assert isinstance(events, list)

    def test_fetch_events_handles_api_error_gracefully(self):
        from app.engines.economic_calendar.service import EconomicCalendarService
        service = EconomicCalendarService(api_key="invalid")
        events = service._fetch_from_fred()
        assert events == []

    def test_get_upcoming_events_returns_filtered(self):
        from app.engines.economic_calendar.service import EconomicCalendarService
        service = EconomicCalendarService(api_key="test")
        events = service.get_upcoming_events(days_ahead=7)
        assert isinstance(events, list)

    def test_analyze_position_impact(self):
        from app.engines.economic_calendar.service import EconomicCalendarService
        service = EconomicCalendarService(api_key="test")
        from app.engines.economic_calendar.schemas import EconomicEvent
        events = [
            EconomicEvent(
                title="FOMC Rate Decision", impact="high",
                event_date=datetime.now(timezone.utc) + timedelta(days=2),
                category="central_bank",
            ),
        ]
        analysis = service.analyze_position_impact(events, ["SPY", "AAPL"])
        assert isinstance(analysis, list)

    def test_no_positions_returns_empty(self):
        from app.engines.economic_calendar.service import EconomicCalendarService
        service = EconomicCalendarService(api_key="test")
        from app.engines.economic_calendar.schemas import EconomicEvent
        events = [EconomicEvent(
            title="CPI", impact="high",
            event_date=datetime.now(timezone.utc) + timedelta(days=1),
            category="inflation",
        )]
        analysis = service.analyze_position_impact(events, [])
        assert analysis == []


class TestEventCategorization:
    def test_inflation_event_flags_bond_sensitive(self):
        from app.engines.economic_calendar.service import EconomicCalendarService
        service = EconomicCalendarService(api_key="test")
        from app.engines.economic_calendar.schemas import EconomicEvent
        ev = EconomicEvent(
            title="CPI YoY", event_date=datetime.now(timezone.utc),
            impact="high", category="inflation",
        )
        tickers = service._get_affected_tickers(ev, ["SPY", "TLT", "AAPL", "GLD"])
        assert "TLT" in tickers
        assert "SPY" in tickers

    def test_central_bank_event_flags_all(self):
        from app.engines.economic_calendar.service import EconomicCalendarService
        service = EconomicCalendarService(api_key="test")
        from app.engines.economic_calendar.schemas import EconomicEvent
        ev = EconomicEvent(
            title="FOMC Decision", event_date=datetime.now(timezone.utc),
            impact="high", category="central_bank",
        )
        tickers = service._get_affected_tickers(ev, ["SPY", "TLT"])
        assert len(tickers) == 2
```

- [ ] **Step 5: Create economic calendar service**

Create `backend/app/engines/economic_calendar/service.py`:
```python
from datetime import datetime, timezone, timedelta
import httpx
from app.engines.economic_calendar.schemas import EconomicEvent, EventImpactAnalysis


FRED_EVENT_SERIES = {
    "CPI": ("CPIAUCSL", "inflation"),
    "Core CPI": ("CPILFESL", "inflation"),
    "PPI": ("PPIACO", "inflation"),
    "Unemployment Rate": ("UNRATE", "employment"),
    "Nonfarm Payrolls": ("PAYEMS", "employment"),
    "GDP": ("GDP", "gdp"),
    "Fed Funds Rate": ("FEDFUNDS", "central_bank"),
    "Housing Starts": ("HOUST", "housing"),
    "Industrial Production": ("INDPRO", "manufacturing"),
    "Consumer Confidence": ("UMCSENT", "confidence"),
    "Retail Sales": ("RSXFS", "consumer"),
    "Trade Balance": ("BOPGSTB", "trade"),
}

CATEGORY_TICKER_MAP = {
    "inflation": ["TLT", "IEF", "SHY", "GLD", "AAPL", "MSFT", "KO"],
    "employment": ["SPY", "DIA", "IWM", "XLY", "XLP"],
    "gdp": ["SPY", "DIA", "XLI", "XLB"],
    "central_bank": ["SPY", "TLT", "IEF", "XLF", "AAPL", "MSFT", "GOOGL", "AMZN"],
    "housing": ["XHB", "ITB", "LEN", "DHI", "HD", "LOW"],
    "manufacturing": ["XLI", "CAT", "DE", "MMM", "GE"],
    "consumer": ["XLY", "AMZN", "WMT", "TSLA", "HD"],
    "trade": ["XLI", "CAT", "BA", "DE"],
    "confidence": ["SPY", "DIA", "XLY"],
}


class EconomicCalendarService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ""

    def _fetch_from_fred(self) -> list[dict]:
        if not self.api_key:
            return []

        events: list[dict] = []
        for name, (series_id, category) in FRED_EVENT_SERIES.items():
            try:
                url = (
                    f"https://api.stlouisfed.org/fred/series/observations"
                    f"?series_id={series_id}&api_key={self.api_key}"
                    f"&file_type=json&sort_order=desc&limit=1"
                )
                resp = httpx.get(url, timeout=10.0)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                observations = data.get("observations", [])
                if not observations:
                    continue
                obs = observations[0]
                if obs.get("value") in (".", ""):
                    continue

                event_date = datetime.now(timezone.utc)
                try:
                    event_date = datetime.strptime(obs["date"], "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                except (ValueError, KeyError):
                    pass

                events.append({
                    "title": f"{name} Release",
                    "event_date": event_date.isoformat(),
                    "impact": "high" if category in ("inflation", "central_bank", "employment", "gdp") else "medium",
                    "category": category,
                    "forecast": None,
                    "previous": float(obs["value"]) if obs["value"].replace(".","").replace("-","").isdigit() else None,
                    "actual": None,
                    "description": f"FRED series {series_id} - {name}",
                    "source": "fred",
                })
            except Exception:
                continue

        return events

    def get_upcoming_events(self, days_ahead: int = 14) -> list[EconomicEvent]:
        raw = self._fetch_from_fred()
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)

        events: list[EconomicEvent] = []
        for item in raw:
            event_date = datetime.fromisoformat(item["event_date"])
            if event_date <= cutoff and event_date >= now - timedelta(days=1):
                try:
                    events.append(EconomicEvent(**item))
                except Exception:
                    continue

        events.sort(key=lambda e: e.event_date)
        return events

    def _get_affected_tickers(self, event: EconomicEvent, portfolio_tickers: list[str]) -> list[str]:
        default_tickers = CATEGORY_TICKER_MAP.get(event.category, ["SPY"])
        affected = [t for t in portfolio_tickers if t in default_tickers]
        if event.impact == "high":
            for broad in ["SPY", "QQQ", "IWM"]:
                if broad in portfolio_tickers and broad not in affected:
                    affected.append(broad)
        return affected

    def analyze_position_impact(self, events: list[EconomicEvent], portfolio_tickers: list[str]) -> list[EventImpactAnalysis]:
        if not portfolio_tickers:
            return []

        results: list[EventImpactAnalysis] = []
        for event in events:
            if event.impact == "low":
                continue
            affected = self._get_affected_tickers(event, portfolio_tickers)
            if not affected:
                continue

            results.append(EventImpactAnalysis(
                event_title=event.title,
                impact_level=event.impact,
                affected_tickers=affected,
                reasoning=self._generate_reasoning(event, affected),
                event_date=event.event_date,
            ))

        return results

    def _generate_reasoning(self, event: EconomicEvent, affected: list[str]) -> str:
        category_descriptions = {
            "inflation": "Inflation data affects bond yields, discount rates, and consumer spending power",
            "employment": "Employment data affects consumer spending, Fed policy expectations",
            "gdp": "GDP data affects overall economic growth expectations",
            "central_bank": "Central bank decisions affect interest rates, liquidity, and asset valuations across the board",
            "housing": "Housing data affects real estate, construction, and consumer durable goods",
            "manufacturing": "Manufacturing data affects industrial companies and raw materials",
            "consumer": "Consumer data affects retail, e-commerce, and discretionary spending stocks",
            "trade": "Trade data affects multinational companies and currency-sensitive sectors",
            "confidence": "Confidence data affects consumer spending and economic outlook",
        }
        base = category_descriptions.get(event.category, "Economic data release")
        return f"{base}. Potentially impacts: {', '.join(affected)}."
```

- [ ] **Step 6: Create economic calendar router**

Create `backend/app/engines/economic_calendar/router.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from app.config import settings
from app.engines.economic_calendar.service import EconomicCalendarService

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


def get_calendar_service() -> EconomicCalendarService:
    return EconomicCalendarService(api_key=settings.fred_api_key)


@router.get("/economic")
async def get_economic_calendar(
    days_ahead: int = 14,
    service: EconomicCalendarService = Depends(get_calendar_service),
):
    events = service.get_upcoming_events(days_ahead=days_ahead)
    return [e.model_dump() for e in events]


@router.get("/economic/impact")
async def analyze_economic_impact(
    tickers: str = "",
    days_ahead: int = 14,
    service: EconomicCalendarService = Depends(get_calendar_service),
):
    portfolio_tickers = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not portfolio_tickers:
        raise HTTPException(status_code=400, detail="At least one ticker required")
    events = service.get_upcoming_events(days_ahead=days_ahead)
    analysis = service.analyze_position_impact(events, portfolio_tickers)
    return [a.model_dump() for a in analysis]


@router.get("/economic/alerts")
async def get_high_impact_alerts(
    days_ahead: int = 7,
    service: EconomicCalendarService = Depends(get_calendar_service),
):
    events = service.get_upcoming_events(days_ahead=days_ahead)
    high_impact = [e for e in events if e.impact == "high"]
    if not high_impact:
        return {"message": "No high-impact events in the next 7 days", "alerts": []}

    alerts = []
    for ev in high_impact:
        days_until = (ev.event_date - datetime.now(timezone.utc)).days
        alerts.append({
            "title": ev.title,
            "date": ev.event_date.isoformat(),
            "days_until": days_until,
            "impact": ev.impact,
            "category": ev.category,
            "message": f"{ev.title} expected in {days_until} day(s) — high impact",
        })

    return {"alerts": alerts, "count": len(alerts)}
```

- [ ] **Step 7: Create economic calendar tasks**

Create `backend/app/engines/economic_calendar/tasks.py`:
```python
from celery import shared_task
from app.config import settings
from app.engines.economic_calendar.service import EconomicCalendarService


@shared_task
def fetch_economic_calendar():
    service = EconomicCalendarService(api_key=settings.fred_api_key)
    events = service.get_upcoming_events(days_ahead=14)
    return {"events_fetched": len(events)}


@shared_task
def check_high_impact_alerts():
    service = EconomicCalendarService(api_key=settings.fred_api_key)
    events = service.get_upcoming_events(days_ahead=7)
    high_impact = [e for e in events if e.impact == "high"]
    return {
        "high_impact_count": len(high_impact),
        "alerts": [{"title": e.title, "date": e.event_date.isoformat()} for e in high_impact],
    }
```

- [ ] **Step 8: Register router in main app**

Append to `backend/app/main.py`:
```python
from app.engines.economic_calendar.router import router as economic_calendar_router
app.include_router(economic_calendar_router)
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/economic_calendar/ -v`
Expected: PASS

- [ ] **Step 10: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 11: Commit**

```
git add backend/app/engines/economic_calendar/ backend/tests/engines/economic_calendar/
git commit -m "feat: add economic calendar integration with FRED API, impact analysis, and high-impact alerts"
```

---

### Task B4: Earnings Calendar Integration

**Files:**
- Create: `backend/app/engines/earnings_calendar/__init__.py`
- Create: `backend/app/engines/earnings_calendar/schemas.py`
- Create: `backend/app/engines/earnings_calendar/service.py`
- Create: `backend/app/engines/earnings_calendar/router.py`
- Create: `backend/app/engines/earnings_calendar/tasks.py`
- Test: `backend/tests/engines/earnings_calendar/__init__.py`
- Test: `backend/tests/engines/earnings_calendar/test_service.py`
- Test: `backend/tests/engines/earnings_calendar/test_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/engines/earnings_calendar/__init__.py` (empty)

Create `backend/tests/engines/earnings_calendar/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone, timedelta


class TestEarningsEvent:
    def test_valid_event(self):
        from app.engines.earnings_calendar.schemas import EarningsEvent
        ev = EarningsEvent(
            ticker="AAPL",
            fiscal_quarter="Q3 2024",
            earnings_date=datetime.now(timezone.utc) + timedelta(days=14),
            estimated_eps=1.50,
            estimated_revenue=90000,
        )
        assert ev.ticker == "AAPL"
        assert ev.estimated_eps == 1.50

    def test_no_estimates(self):
        from app.engines.earnings_calendar.schemas import EarningsEvent
        ev = EarningsEvent(
            ticker="AAPL", fiscal_quarter="Q3 2024",
            earnings_date=datetime.now(timezone.utc) + timedelta(days=14),
        )
        assert ev.estimated_eps is None

    def test_invalid_ticker_empty(self):
        from app.engines.earnings_calendar.schemas import EarningsEvent
        with pytest.raises(ValidationError):
            EarningsEvent(
                ticker="", fiscal_quarter="Q3 2024",
                earnings_date=datetime.now(timezone.utc),
            )


class TestEarningsAlert:
    def test_alert_created(self):
        from app.engines.earnings_calendar.schemas import EarningsAlert
        alert = EarningsAlert(
            ticker="AAPL",
            earnings_date=datetime.now(timezone.utc) + timedelta(days=7),
            days_until=7, risk_level="medium",
            message="AAPL earnings in 7 days",
        )
        assert alert.risk_level == "medium"
```

- [ ] **Step 2: Run tests to verify fail**

Run: `cd backend && python -m pytest tests/engines/earnings_calendar/ -v`
Expected: FAIL

- [ ] **Step 3: Create earnings calendar schemas**

Create `backend/app/engines/earnings_calendar/__init__.py` (empty)

Create `backend/app/engines/earnings_calendar/schemas.py`:
```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator


class EarningsEvent(BaseModel):
    ticker: str
    fiscal_quarter: str
    earnings_date: datetime
    estimated_eps: float | None = None
    estimated_revenue: float | None = None
    actual_eps: float | None = None
    actual_revenue: float | None = None
    source: str = "fmp"

    @field_validator("ticker")
    @classmethod
    def ticker_not_empty(cls, v: str) -> str:
        v = v.upper().strip()
        if not v:
            raise ValueError("ticker cannot be empty")
        return v


class EarningsAlert(BaseModel):
    ticker: str
    earnings_date: datetime
    days_until: int
    risk_level: Literal["low", "medium", "high"]
    message: str
```

- [ ] **Step 4: Write failing service tests**

Create `backend/tests/engines/earnings_calendar/test_service.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta


class TestEarningsService:
    def test_get_earnings_returns_list(self):
        from app.engines.earnings_calendar.service import EarningsCalendarService
        service = EarningsCalendarService(api_key="test")
        tickers = ["AAPL", "MSFT"]
        events = service.get_earnings_for_tickers(tickers)
        assert isinstance(events, list)

    def test_empty_tickers_returns_empty(self):
        from app.engines.earnings_calendar.service import EarningsCalendarService
        service = EarningsCalendarService(api_key="test")
        events = service.get_earnings_for_tickers([])
        assert events == []

    def test_fetch_handles_api_error_gracefully(self):
        from app.engines.earnings_calendar.service import EarningsCalendarService
        service = EarningsCalendarService(api_key="invalid_key_that_will_fail")
        events = service.get_earnings_for_tickers(["AAPL"])
        assert isinstance(events, list)

    def test_generate_alerts(self):
        from app.engines.earnings_calendar.service import EarningsCalendarService
        service = EarningsCalendarService(api_key="test")
        from app.engines.earnings_calendar.schemas import EarningsEvent
        events = [
            EarningsEvent(
                ticker="AAPL", fiscal_quarter="Q3 2024",
                earnings_date=datetime.now(timezone.utc) + timedelta(days=3),
            ),
            EarningsEvent(
                ticker="MSFT", fiscal_quarter="Q3 2024",
                earnings_date=datetime.now(timezone.utc) + timedelta(days=30),
            ),
        ]
        alerts = service.generate_alerts(events)
        assert len(alerts) == 1
        assert alerts[0].ticker == "AAPL"

    def test_alert_risk_levels(self):
        from app.engines.earnings_calendar.service import EarningsCalendarService
        service = EarningsCalendarService(api_key="test")
        from app.engines.earnings_calendar.schemas import EarningsEvent
        now = datetime.now(timezone.utc)
        events = [
            EarningsEvent(ticker="HIGH", fiscal_quarter="Q3",
                          earnings_date=now + timedelta(days=1)),
            EarningsEvent(ticker="MED", fiscal_quarter="Q3",
                          earnings_date=now + timedelta(days=5)),
            EarningsEvent(ticker="LOW", fiscal_quarter="Q3",
                          earnings_date=now + timedelta(days=10)),
        ]
        alerts = service.generate_alerts(events)
        alert_map = {a.ticker: a for a in alerts}
        assert alert_map["HIGH"].risk_level == "high"
        assert alert_map["MED"].risk_level == "medium"
        assert "LOW" not in alert_map
```

- [ ] **Step 5: Create earnings calendar service**

Create `backend/app/engines/earnings_calendar/service.py`:
```python
from datetime import datetime, timezone, timedelta
import httpx
from app.engines.earnings_calendar.schemas import EarningsEvent, EarningsAlert


class EarningsCalendarService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ""

    def _fetch_from_fmp(self, ticker: str) -> list[dict]:
        if not self.api_key:
            return []
        try:
            url = (
                f"https://financialmodelingprep.com/api/v3/earnings_calendar"
                f"?symbol={ticker}&apikey={self.api_key}"
            )
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code != 200:
                return []
            return resp.json()
        except Exception:
            return []

    def get_earnings_for_tickers(self, tickers: list[str]) -> list[EarningsEvent]:
        if not tickers or not self.api_key:
            return []

        events: list[EarningsEvent] = []
        for ticker in tickers:
            raw = self._fetch_from_fmp(ticker)
            for item in raw:
                try:
                    ev = EarningsEvent(
                        ticker=ticker.upper(),
                        fiscal_quarter=f"{item.get('fiscalYear', '?')} Q{item.get('fiscalQuarter', '?')}",
                        earnings_date=datetime.fromisoformat(
                            item.get("date", datetime.now(timezone.utc).isoformat())
                        ).replace(tzinfo=timezone.utc),
                        estimated_eps=item.get("estimatedEps"),
                        estimated_revenue=item.get("estimatedRevenue"),
                        actual_eps=item.get("eps"),
                        actual_revenue=item.get("revenue"),
                        source="fmp",
                    )
                    events.append(ev)
                except (ValueError, KeyError):
                    continue

        return events

    def generate_alerts(self, events: list[EarningsEvent]) -> list[EarningsAlert]:
        now = datetime.now(timezone.utc)
        window = timedelta(days=7)
        alerts: list[EarningsAlert] = []

        for ev in events:
            days_until = (ev.earnings_date - now).days
            if days_until < 0:
                continue

            if days_until <= 7:
                if days_until <= 2:
                    risk_level = "high"
                    message = f"{ev.ticker} earnings in {days_until} day(s) — high risk of price movement"
                elif days_until <= 5:
                    risk_level = "medium"
                    message = f"{ev.ticker} earnings in {days_until} day(s) — elevated risk"
                else:
                    risk_level = "low"
                    message = f"{ev.ticker} earnings in {days_until} day(s)"

                alerts.append(EarningsAlert(
                    ticker=ev.ticker,
                    earnings_date=ev.earnings_date,
                    days_until=days_until,
                    risk_level=risk_level,
                    message=message,
                ))

        alerts.sort(key=lambda a: a.days_until)
        return alerts
```

- [ ] **Step 6: Create earnings calendar router**

Create `backend/app/engines/earnings_calendar/router.py`:
```python
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.engines.earnings_calendar.service import EarningsCalendarService

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


@router.get("/earnings")
async def get_earnings(tickers: str = "AAPL,MSFT,GOOGL,AMZN"):
    service = EarningsCalendarService(api_key=settings.polygon_api_key)
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="At least one ticker required")
    events = service.get_earnings_for_tickers(ticker_list)
    return [e.model_dump() for e in events]


@router.get("/earnings/alerts")
async def get_earnings_alerts(tickers: str = ""):
    service = EarningsCalendarService(api_key=settings.polygon_api_key)
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    else:
        try:
            from app.database import get_connection
            conn = get_connection()
            rows = conn.execute("SELECT DISTINCT ticker FROM positions WHERE quantity > 0").fetchall()
            ticker_list = [r[0] for r in rows]
        except Exception:
            ticker_list = []

    events = service.get_earnings_for_tickers(ticker_list)
    alerts = service.generate_alerts(events)
    return [a.model_dump() for a in alerts]
```

- [ ] **Step 7: Create earnings calendar tasks**

Create `backend/app/engines/earnings_calendar/tasks.py`:
```python
from celery import shared_task
from app.config import settings
from app.engines.earnings_calendar.service import EarningsCalendarService


@shared_task
def check_earnings_alerts():
    service = EarningsCalendarService(api_key=settings.polygon_api_key)
    try:
        from app.database import get_connection
        conn = get_connection()
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM positions WHERE quantity > 0"
        ).fetchall()
        tickers = [r[0] for r in rows]
    except Exception:
        tickers = []

    events = service.get_earnings_for_tickers(tickers)
    alerts = service.generate_alerts(events)
    return {"alerts_count": len(alerts), "alerts": [a.model_dump() for a in alerts]}
```

- [ ] **Step 8: Register router in main app**

Append to `backend/app/main.py`:
```python
from app.engines.earnings_calendar.router import router as earnings_calendar_router
app.include_router(earnings_calendar_router)
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/earnings_calendar/ -v`
Expected: PASS

- [ ] **Step 10: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 11: Commit**

```
git add backend/app/engines/earnings_calendar/ backend/tests/engines/earnings_calendar/
git commit -m "feat: add earnings calendar integration with FMP API, alerts, and risk levels"
```

---

### Task B5: Sector Rotation Analysis Engine

**Files:**
- Create: `backend/app/engines/sector_rotation/__init__.py`
- Create: `backend/app/engines/sector_rotation/schemas.py`
- Create: `backend/app/engines/sector_rotation/service.py`
- Create: `backend/app/engines/sector_rotation/router.py`
- Create: `backend/app/engines/sector_rotation/tasks.py`
- Test: `backend/tests/engines/sector_rotation/__init__.py`
- Test: `backend/tests/engines/sector_rotation/test_service.py`
- Test: `backend/tests/engines/sector_rotation/test_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/engines/sector_rotation/__init__.py` (empty)

Create `backend/tests/engines/sector_rotation/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError


class TestSectorData:
    def test_valid_sector(self):
        from app.engines.sector_rotation.schemas import SectorData
        s = SectorData(ticker="XLK", sector_name="Technology", price=200.0)
        assert s.ticker == "XLK"
        assert s.sector_name == "Technology"

    def test_sector_name_validated(self):
        from app.engines.sector_rotation.schemas import SectorData
        with pytest.raises(ValidationError):
            SectorData(ticker="XYZ", sector_name="Unknown Sector", price=100.0)


class TestRotationSignal:
    def test_bullish_signal(self):
        from app.engines.sector_rotation.schemas import RotationSignal
        s = RotationSignal(
            sector="Technology", momentum_rank=1, momentum_score=85.0,
            signal="overweight", reason="Leading sector with strong momentum",
        )
        assert s.signal == "overweight"

    def test_bearish_signal(self):
        from app.engines.sector_rotation.schemas import RotationSignal
        s = RotationSignal(
            sector="Utilities", momentum_rank=11, momentum_score=15.0,
            signal="underweight", reason="Lagging sector with weak momentum",
        )
        assert s.signal == "underweight"
```

- [ ] **Step 2: Run tests to verify fail**

Run: `cd backend && python -m pytest tests/engines/sector_rotation/ -v`
Expected: FAIL

- [ ] **Step 3: Create sector rotation schemas**

Create `backend/app/engines/sector_rotation/__init__.py` (empty)

Create `backend/app/engines/sector_rotation/schemas.py`:
```python
from typing import Literal
from pydantic import BaseModel, field_validator

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLBS": "Communication Services",
}

SECTOR_TICKER_MAP = {v: k for k, v in SECTOR_ETFS.items()}
SECTOR_LIST = list(SECTOR_ETFS.values())

SIGNAL_TYPE = Literal["overweight", "neutral", "underweight"]


class SectorData(BaseModel):
    ticker: str
    sector_name: str
    price: float
    ma_20: float | None = None
    ma_50: float | None = None
    ma_200: float | None = None
    momentum_1m: float | None = None
    momentum_3m: float | None = None
    momentum_6m: float | None = None
    rsi: float | None = None

    @field_validator("sector_name")
    @classmethod
    def sector_must_be_valid(cls, v: str) -> str:
        if v not in SECTOR_LIST:
            raise ValueError(f"sector_name must be one of {SECTOR_LIST}")
        return v


class RotationSignal(BaseModel):
    sector: str
    momentum_rank: int
    momentum_score: float
    signal: SIGNAL_TYPE
    reason: str


class SectorRotationReport(BaseModel):
    date: str
    total_sectors: int
    leading_sectors: list[str]
    lagging_sectors: list[str]
    rotation_signals: list[RotationSignal]
    recommended_tilts: str
```

- [ ] **Step 4: Write failing service tests**

Create `backend/tests/engines/sector_rotation/test_service.py`:
```python
import pytest
import numpy as np


class TestSectorRotationService:
    def test_compute_momentum_scores(self):
        from app.engines.sector_rotation.service import SectorRotationService
        service = SectorRotationService()
        prices = {
            "XLK": np.array([100, 102, 104, 106, 108, 110]),
            "XLU": np.array([100, 99, 98, 97, 96, 95]),
            "XLP": np.array([100, 100, 100, 100, 100, 100]),
        }
        scores = service.compute_momentum_scores(prices)
        assert scores["XLK"] > scores["XLP"]
        assert scores["XLP"] > scores["XLU"]

    def test_generate_rotation_signals(self):
        from app.engines.sector_rotation.service import SectorRotationService
        service = SectorRotationService()
        scores = {"XLK": 90.0, "XLF": 75.0, "XLV": 60.0, "XLY": 50.0,
                  "XLP": 40.0, "XLE": 35.0, "XLI": 30.0, "XLB": 25.0,
                  "XLU": 20.0, "XLRE": 15.0, "XLBS": 10.0}
        signals = service.generate_rotation_signals(scores)
        assert len(signals) == 11

        overweight = [s for s in signals if s.signal == "overweight"]
        assert len(overweight) == 3
        assert overweight[0].sector == "Technology"

        underweight = [s for s in signals if s.signal == "underweight"]
        assert len(underweight) == 3

        neutral = [s for s in signals if s.signal == "neutral"]
        assert len(neutral) == 5

    def test_detect_rotation_trend(self):
        from app.engines.sector_rotation.service import SectorRotationService
        service = SectorRotationService()
        historical_scores = {
            "Technology": [50, 55, 60, 65, 70, 75],
            "Utilities": [70, 65, 60, 55, 50, 45],
            "Healthcare": [60, 58, 62, 61, 59, 63],
        }
        trend = service.detect_rotation_trend(historical_scores)
        assert "Technology" in trend["rotating_in"]
        assert "Utilities" in trend["rotating_out"]

    def test_empty_prices_returns_empty(self):
        from app.engines.sector_rotation.service import SectorRotationService
        service = SectorRotationService()
        scores = service.compute_momentum_scores({})
        assert scores == {}

    def test_single_sector_returns_default(self):
        from app.engines.sector_rotation.service import SectorRotationService
        service = SectorRotationService()
        scores = service.compute_momentum_scores({"XLK": np.array([100, 101, 102])})
        assert scores["XLK"] == 50.0
```

- [ ] **Step 5: Create sector rotation service**

Create `backend/app/engines/sector_rotation/service.py`:
```python
import numpy as np
from datetime import datetime, timezone
from app.engines.sector_rotation.schemas import (
    SectorData,
    RotationSignal,
    SectorRotationReport,
    SECTOR_ETFS,
    SECTOR_LIST,
)


class SectorRotationService:
    def compute_momentum_scores(self, sector_prices: dict[str, np.ndarray]) -> dict[str, float]:
        if not sector_prices:
            return {}

        scores: dict[str, float] = {}
        for ticker, prices in sector_prices.items():
            if len(prices) < 2:
                scores[ticker] = 50.0
                continue
            returns = np.diff(prices) / prices[:-1]
            mom_1m = np.mean(returns[-20:]) if len(returns) >= 20 else np.mean(returns)
            mom_3m = np.mean(returns[-60:]) if len(returns) >= 60 else np.mean(returns)
            mom_6m = np.mean(returns[-120:]) if len(returns) >= 120 else np.mean(returns)

            score = 0.5 * mom_1m + 0.3 * mom_3m + 0.2 * mom_6m
            scores[ticker] = float(np.clip((score + 0.1) * 500, 0, 100))

        if len(scores) <= 1:
            for k in scores:
                scores[k] = 50.0
            return scores

        return scores

    def generate_rotation_signals(self, momentum_scores: dict[str, float]) -> list[RotationSignal]:
        if not momentum_scores:
            return []

        sorted_sectors = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        n = len(sorted_sectors)

        signals: list[RotationSignal] = []
        for rank, (ticker, score) in enumerate(sorted_sectors, start=1):
            sector_name = SECTOR_ETFS.get(ticker, ticker)

            if rank <= max(1, n // 4):
                signal = "overweight"
                reason = f"Ranked #{rank}/{n} — leading sector with strong momentum ({score:.1f})"
            elif rank >= n - max(1, n // 4) + 1:
                signal = "underweight"
                reason = f"Ranked #{rank}/{n} — lagging sector with weak momentum ({score:.1f})"
            else:
                signal = "neutral"
                reason = f"Ranked #{rank}/{n} — neutral momentum ({score:.1f})"

            signals.append(RotationSignal(
                sector=sector_name, momentum_rank=rank,
                momentum_score=round(score, 2), signal=signal, reason=reason,
            ))

        return signals

    def detect_rotation_trend(self, historical_scores: dict[str, list[float]]) -> dict:
        rotating_in: list[str] = []
        rotating_out: list[str] = []

        for sector, scores in historical_scores.items():
            if len(scores) < 6:
                continue
            weights = np.linspace(0.5, 1.0, len(scores))
            weighted_avg = np.average(scores, weights=weights)
            simple_avg = np.mean(scores)

            if weighted_avg > simple_avg * 1.05 and scores[-1] > np.mean(scores[-3:]):
                rotating_in.append(sector)
            elif weighted_avg < simple_avg * 0.95 and scores[-1] < np.mean(scores[-3:]):
                rotating_out.append(sector)

        return {"rotating_in": rotating_in, "rotating_out": rotating_out}

    def generate_report(self, sector_prices: dict[str, np.ndarray]) -> SectorRotationReport:
        scores = self.compute_momentum_scores(sector_prices)
        signals = self.generate_rotation_signals(scores)

        historical_scores: dict[str, list[float]] = {}
        for ticker, prices in sector_prices.items():
            if len(prices) >= 6:
                window = len(prices) // 6
                hist = [float(np.mean(prices[i:i+window])) for i in range(0, len(prices), window)]
                historical_scores[SECTOR_ETFS.get(ticker, ticker)] = hist

        trend = self.detect_rotation_trend(historical_scores)

        leading = [s.sector for s in signals if s.signal == "overweight"]
        lagging = [s.sector for s in signals if s.signal == "underweight"]

        if leading:
            tilt = f"Tilt toward: {', '.join(leading)}. "
        else:
            tilt = "No clear leadership. "
        if lagging:
            tilt += f"Reduce exposure to: {', '.join(lagging)}. "
        if trend["rotating_in"]:
            tilt += f"Rotating in: {', '.join(trend['rotating_in'])}. "
        if trend["rotating_out"]:
            tilt += f"Rotating out: {', '.join(trend['rotating_out'])}."

        return SectorRotationReport(
            date=str(datetime.now(timezone.utc).date()),
            total_sectors=len(signals),
            leading_sectors=leading,
            lagging_sectors=lagging,
            rotation_signals=signals,
            recommended_tilts=tilt,
        )
```

- [ ] **Step 6: Create sector rotation router**

Create `backend/app/engines/sector_rotation/router.py`:
```python
import numpy as np
from fastapi import APIRouter, HTTPException
from app.engines.sector_rotation.service import SectorRotationService
from app.engines.sector_rotation.schemas import SECTOR_ETFS

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
service = SectorRotationService()


@router.get("/sector-rotation")
async def get_sector_rotation():
    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)
    except Exception:
        raise HTTPException(status_code=503, detail="Data service unavailable")

    sector_prices: dict[str, np.ndarray] = {}
    for ticker in SECTOR_ETFS:
        try:
            ohlcv = data_service.load_ohlcv(ticker, days=365)
            if not ohlcv.empty:
                sector_prices[ticker] = ohlcv["close"].values.astype(np.float64)
        except Exception:
            continue

    if not sector_prices:
        raise HTTPException(status_code=404, detail="No sector data available")

    report = service.generate_report(sector_prices)
    return report.model_dump()


@router.get("/sector-rotation/rankings")
async def get_sector_rankings():
    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)
    except Exception:
        raise HTTPException(status_code=503, detail="Data service unavailable")

    sector_prices: dict[str, np.ndarray] = {}
    for ticker in SECTOR_ETFS:
        try:
            ohlcv = data_service.load_ohlcv(ticker, days=365)
            if not ohlcv.empty:
                sector_prices[ticker] = ohlcv["close"].values.astype(np.float64)
        except Exception:
            continue

    scores = service.compute_momentum_scores(sector_prices)
    signals = service.generate_rotation_signals(scores)
    return [s.model_dump() for s in signals]
```

- [ ] **Step 7: Create sector rotation tasks**

Create `backend/app/engines/sector_rotation/tasks.py`:
```python
from celery import shared_task
import numpy as np
from app.engines.sector_rotation.service import SectorRotationService
from app.engines.sector_rotation.schemas import SECTOR_ETFS


@shared_task
def compute_sector_rotation():
    service = SectorRotationService()
    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)
    except Exception:
        return {"status": "error", "message": "Data service unavailable"}

    sector_prices: dict[str, np.ndarray] = {}
    for ticker in SECTOR_ETFS:
        try:
            ohlcv = data_service.load_ohlcv(ticker, days=365)
            if not ohlcv.empty:
                sector_prices[ticker] = ohlcv["close"].values.astype(np.float64)
        except Exception:
            continue

    report = service.generate_report(sector_prices)
    return report.model_dump()
```

- [ ] **Step 8: Register router in main app**

Append to `backend/app/main.py`:
```python
from app.engines.sector_rotation.router import router as sector_rotation_router
app.include_router(sector_rotation_router)
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/sector_rotation/ -v`
Expected: PASS

- [ ] **Step 10: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 11: Commit**

```
git add backend/app/engines/sector_rotation/ backend/tests/engines/sector_rotation/
git commit -m "feat: add sector rotation analysis with momentum scoring, rotation signal generation, and trend detection"
```

---

### Task B6: Trade Journal Enhancements

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/tests/test_database.py`
- Create: `backend/app/engines/trade_journal/__init__.py`
- Create: `backend/app/engines/trade_journal/schemas.py`
- Create: `backend/app/engines/trade_journal/service.py`
- Create: `backend/app/engines/trade_journal/router.py`
- Test: `backend/tests/engines/trade_journal/__init__.py`
- Test: `backend/tests/engines/trade_journal/test_service.py`
- Test: `backend/tests/engines/trade_journal/test_schemas.py`

- [ ] **Step 1: Add trade_journal table to database schema**

Append to `backend/app/database.py` in `_init_schema`:
```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR NOT NULL,
            direction VARCHAR NOT NULL,
            entry_price DECIMAL(18,4) NOT NULL,
            exit_price DECIMAL(18,4),
            quantity INTEGER NOT NULL,
            entry_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            exit_date TIMESTAMP WITH TIME ZONE,
            tags VARCHAR DEFAULT '',
            notes VARCHAR DEFAULT '',
            strategy_type VARCHAR NOT NULL,
            pnl DECIMAL(18,4),
            pnl_pct DECIMAL(10,4),
            hold_days INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
```

- [ ] **Step 2: Add database test for trade_journal table**

Add test class to `backend/tests/test_database.py`:
```python
class TestTradeJournalSchema:
    def test_trade_journal_table_created(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_journal'"
            ).fetchall()
            assert len(tables) == 1
        finally:
            close_connection(test_db_path)

    def test_trade_journal_columns(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            cols = conn.execute("PRAGMA table_info(trade_journal)").fetchall()
            names = {c[1] for c in cols}
            for expected in ("id", "ticker", "direction", "entry_price", "exit_price",
                             "quantity", "entry_date", "exit_date", "tags", "notes",
                             "strategy_type", "pnl", "pnl_pct", "hold_days"):
                assert expected in names
        finally:
            close_connection(test_db_path)
```

- [ ] **Step 3: Run database tests to verify**

Run: `cd backend && python -m pytest tests/test_database.py -v`
Expected: PASS (including new tests)

- [ ] **Step 4: Write failing tests for trade journal schemas**

Create `backend/tests/engines/trade_journal/__init__.py` (empty)

Create `backend/tests/engines/trade_journal/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone


class TestJournalEntry:
    def test_valid_entry(self):
        from app.engines.trade_journal.schemas import JournalEntry
        entry = JournalEntry(
            ticker="AAPL", direction="long",
            entry_price=150.0, exit_price=165.0, quantity=100,
            entry_date=datetime.now(timezone.utc),
            exit_date=datetime.now(timezone.utc),
            tags=["earnings_play", "momentum"],
            notes="Good entry on pullback to 50MA",
            strategy_type="swing",
        )
        assert entry.pnl_pct == 10.0
        assert len(entry.tags) == 2

    def test_entry_without_exit(self):
        from app.engines.trade_journal.schemas import JournalEntry
        entry = JournalEntry(
            ticker="AAPL", direction="long",
            entry_price=150.0, quantity=100,
            entry_date=datetime.now(timezone.utc),
            strategy_type="swing",
        )
        assert entry.exit_price is None
        assert entry.pnl is None

    def test_invalid_direction(self):
        from app.engines.trade_journal.schemas import JournalEntry
        with pytest.raises(ValidationError):
            JournalEntry(
                ticker="AAPL", direction="sideways",
                entry_price=150.0, quantity=100,
                entry_date=datetime.now(timezone.utc),
                strategy_type="swing",
            )


class TestJournalExport:
    def test_csv_export_format(self):
        from app.engines.trade_journal.schemas import JournalEntry, JournalExport
        entries = [
            JournalEntry(
                ticker="AAPL", direction="long", entry_price=150.0,
                exit_price=165.0, quantity=100,
                entry_date=datetime.now(timezone.utc),
                exit_date=datetime.now(timezone.utc),
                strategy_type="swing",
            )
        ]
        export = JournalExport(entries=entries, format="csv")
        csv = export.to_csv()
        assert "ticker" in csv
        assert "AAPL" in csv
        assert csv.count("\n") == 2


class TestTagSystem:
    def test_tag_normalization(self):
        from app.engines.trade_journal.schemas import Tag
        t = Tag(name="  Earnings Play  ")
        assert t.name == "earnings_play"

    def test_tag_analytics(self):
        from app.engines.trade_journal.schemas import TagAnalytics
        a = TagAnalytics(tag="earnings_play", count=5, total_pnl=1500.0, win_rate=0.6, avg_hold_days=14)
        assert a.win_rate == 0.6
```

- [ ] **Step 5: Run tests to verify fail**

Run: `cd backend && python -m pytest tests/engines/trade_journal/ -v`
Expected: FAIL

- [ ] **Step 6: Create trade journal schemas**

Create `backend/app/engines/trade_journal/__init__.py` (empty)

Create `backend/app/engines/trade_journal/schemas.py`:
```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator
import csv
import io


class Tag(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def normalize_tag(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")


class JournalEntry(BaseModel):
    ticker: str
    direction: Literal["long", "short"]
    entry_price: float
    exit_price: float | None = None
    quantity: int
    entry_date: datetime
    exit_date: datetime | None = None
    tags: list[str] = []
    notes: str = ""
    strategy_type: str = "swing"
    pnl: float | None = None
    pnl_pct: float | None = None
    hold_days: int | None = None

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()

    def compute_pnl(self):
        if self.exit_price is not None:
            if self.direction == "long":
                self.pnl = round((self.exit_price - self.entry_price) * self.quantity, 2)
                self.pnl_pct = round((self.exit_price - self.entry_price) / self.entry_price * 100, 2)
            else:
                self.pnl = round((self.entry_price - self.exit_price) * self.quantity, 2)
                self.pnl_pct = round((self.entry_price - self.exit_price) / self.entry_price * 100, 2)
        if self.exit_date and self.entry_date:
            delta = self.exit_date - self.entry_date
            self.hold_days = max(0, delta.days)


class TagAnalytics(BaseModel):
    tag: str
    count: int
    total_pnl: float
    win_rate: float
    avg_hold_days: float


class JournalExport(BaseModel):
    entries: list[JournalEntry]
    format: Literal["csv"] = "csv"

    def to_csv(self) -> str:
        output = io.StringIO()
        fieldnames = [
            "ticker", "direction", "entry_price", "exit_price", "quantity",
            "entry_date", "exit_date", "tags", "notes", "strategy_type",
            "pnl", "pnl_pct", "hold_days",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for entry in self.entries:
            entry.compute_pnl()
            row = entry.model_dump()
            row["entry_date"] = entry.entry_date.isoformat() if entry.entry_date else ""
            row["exit_date"] = entry.exit_date.isoformat() if entry.exit_date else ""
            row["tags"] = ";".join(entry.tags)
            writer.writerow(row)
        return output.getvalue()
```

- [ ] **Step 7: Write failing service tests**

Create `backend/tests/engines/trade_journal/test_service.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta


class TestJournalService:
    def test_add_entry(self, test_db_path):
        from app.engines.trade_journal.service import TradeJournalService
        from app.engines.trade_journal.schemas import JournalEntry
        service = TradeJournalService(db_path=test_db_path)
        entry = JournalEntry(
            ticker="AAPL", direction="long", entry_price=150.0,
            exit_price=165.0, quantity=100,
            entry_date=datetime.now(timezone.utc) - timedelta(days=30),
            exit_date=datetime.now(timezone.utc),
            tags=["earnings_play"], notes="Good trade",
            strategy_type="swing",
        )
        result = service.add_entry(entry)
        assert result["id"] is not None
        assert result["ticker"] == "AAPL"

    def test_get_entries(self, test_db_path):
        from app.engines.trade_journal.service import TradeJournalService
        from app.engines.trade_journal.schemas import JournalEntry
        service = TradeJournalService(db_path=test_db_path)
        entry = JournalEntry(
            ticker="AAPL", direction="long", entry_price=150.0,
            exit_price=165.0, quantity=100,
            entry_date=datetime.now(timezone.utc) - timedelta(days=30),
            exit_date=datetime.now(timezone.utc),
            strategy_type="swing",
        )
        service.add_entry(entry)
        entries = service.get_entries()
        assert len(entries) >= 1
        assert entries[0]["ticker"] == "AAPL"

    def test_get_entries_filtered_by_tag(self, test_db_path):
        from app.engines.trade_journal.service import TradeJournalService
        from app.engines.trade_journal.schemas import JournalEntry
        service = TradeJournalService(db_path=test_db_path)
        e1 = JournalEntry(
            ticker="AAPL", direction="long", entry_price=150.0,
            exit_price=165.0, quantity=100,
            entry_date=datetime.now(timezone.utc) - timedelta(days=30),
            exit_date=datetime.now(timezone.utc),
            tags=["earnings"], strategy_type="swing",
        )
        e2 = JournalEntry(
            ticker="MSFT", direction="long", entry_price=300.0,
            exit_price=310.0, quantity=50,
            entry_date=datetime.now(timezone.utc) - timedelta(days=20),
            exit_date=datetime.now(timezone.utc),
            tags=["momentum"], strategy_type="swing",
        )
        service.add_entry(e1)
        service.add_entry(e2)
        entries = service.get_entries(tag="earnings")
        assert len(entries) == 1
        assert entries[0]["ticker"] == "AAPL"

    def test_tag_analytics(self, test_db_path):
        from app.engines.trade_journal.service import TradeJournalService
        from app.engines.trade_journal.schemas import JournalEntry
        service = TradeJournalService(db_path=test_db_path)
        for pnl_pct in [10, -5, 15, 8, -2]:
            exit_p = 100 * (1 + pnl_pct / 100)
            entry = JournalEntry(
                ticker="AAPL", direction="long", entry_price=100.0,
                exit_price=exit_p, quantity=10,
                entry_date=datetime.now(timezone.utc) - timedelta(days=14),
                exit_date=datetime.now(timezone.utc),
                tags=["earnings"], strategy_type="swing",
            )
            service.add_entry(entry)
        analytics = service.get_tag_analytics()
        assert len(analytics) >= 1
        earnings_tag = [a for a in analytics if a.tag == "earnings"][0]
        assert earnings_tag.count == 5
        assert earnings_tag.win_rate == 0.6

    def test_export_csv(self, test_db_path):
        from app.engines.trade_journal.service import TradeJournalService
        from app.engines.trade_journal.schemas import JournalEntry
        service = TradeJournalService(db_path=test_db_path)
        entry = JournalEntry(
            ticker="AAPL", direction="long", entry_price=150.0,
            exit_price=165.0, quantity=100,
            entry_date=datetime.now(timezone.utc) - timedelta(days=30),
            exit_date=datetime.now(timezone.utc),
            strategy_type="swing",
        )
        service.add_entry(entry)
        csv_content = service.export_csv()
        assert "ticker" in csv_content
        assert "AAPL" in csv_content

    def test_update_tags(self, test_db_path):
        from app.engines.trade_journal.service import TradeJournalService
        from app.engines.trade_journal.schemas import JournalEntry
        service = TradeJournalService(db_path=test_db_path)
        entry = JournalEntry(
            ticker="AAPL", direction="long", entry_price=150.0,
            exit_price=165.0, quantity=100,
            entry_date=datetime.now(timezone.utc) - timedelta(days=30),
            exit_date=datetime.now(timezone.utc),
            strategy_type="swing",
        )
        result = service.add_entry(entry)
        entry_id = result["id"]
        updated = service.update_entry(entry_id, tags=["earnings", "swing"])
        assert "earnings" in updated["tags"]
        assert "swing" in updated["tags"]
```

- [ ] **Step 8: Create trade journal service**

Create `backend/app/engines/trade_journal/service.py`:
```python
from datetime import datetime, timezone
from app.database import get_connection, close_connection
from app.engines.trade_journal.schemas import JournalEntry, TagAnalytics


class TradeJournalService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def add_entry(self, entry: JournalEntry) -> dict:
        entry.compute_pnl()
        conn = self._conn()
        conn.execute("""
            INSERT INTO trade_journal
                (ticker, direction, entry_price, exit_price, quantity,
                 entry_date, exit_date, tags, notes, strategy_type,
                 pnl, pnl_pct, hold_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            entry.ticker, entry.direction, entry.entry_price, entry.exit_price,
            entry.quantity, entry.entry_date, entry.exit_date,
            ";".join(entry.tags), entry.notes, entry.strategy_type,
            entry.pnl, entry.pnl_pct, entry.hold_days,
        ])
        row = conn.execute(
            "SELECT * FROM trade_journal WHERE id = last_insert_rowid()"
        ).fetchone()
        return dict(row) if row else {}

    def get_entries(self, tag: str | None = None) -> list[dict]:
        conn = self._conn()
        if tag:
            rows = conn.execute(
                "SELECT * FROM trade_journal WHERE tags LIKE ? ORDER BY entry_date DESC",
                [f"%{tag}%"],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trade_journal ORDER BY entry_date DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_entry(self, entry_id: int) -> dict | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM trade_journal WHERE id = ?", [entry_id]
        ).fetchone()
        return dict(row) if row else None

    def update_entry(self, entry_id: int, **kwargs) -> dict | None:
        conn = self._conn()
        allowed = {"tags", "notes", "exit_price", "exit_date", "direction"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return None

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = ";".join(updates["tags"])

        conn.execute(
            f"UPDATE trade_journal SET {set_clause}, updated_at = NOW() WHERE id = ?",
            [*updates.values(), entry_id],
        )
        return self.get_entry(entry_id)

    def get_tag_analytics(self) -> list[TagAnalytics]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT tags, COUNT(*) as cnt, SUM(pnl) as total_pnl
            FROM trade_journal
            WHERE tags != '' AND tags IS NOT NULL
            GROUP BY tags
        """).fetchall()

        analytics: list[TagAnalytics] = []
        for row in rows:
            tag_str = dict(row)["tags"]
            tag = tag_str.split(";")[0] if ";" in tag_str else tag_str

            win_count = conn.execute(
                "SELECT COUNT(*) FROM trade_journal WHERE tags LIKE ? AND pnl > 0",
                [f"%{tag}%"],
            ).fetchone()
            total_count = conn.execute(
                "SELECT COUNT(*) FROM trade_journal WHERE tags LIKE ?",
                [f"%{tag}%"],
            ).fetchone()
            avg_days = conn.execute(
                "SELECT AVG(hold_days) FROM trade_journal WHERE tags LIKE ? AND hold_days IS NOT NULL",
                [f"%{tag}%"],
            ).fetchone()

            win_rate = dict(win_count)[0] / dict(total_count)[0] if dict(total_count)[0] > 0 else 0
            avg_hold = dict(avg_days)[0] or 0

            analytics.append(TagAnalytics(
                tag=tag,
                count=dict(total_count)[0],
                total_pnl=float(dict(row)["total_pnl"] or 0),
                win_rate=round(win_rate, 2),
                avg_hold_days=round(float(avg_hold), 1),
            ))

        return analytics

    def export_csv(self) -> str:
        from app.engines.trade_journal.schemas import JournalExport
        entries_data = self.get_entries()
        entries = [JournalEntry(**e) for e in entries_data]
        export = JournalExport(entries=entries)
        return export.to_csv()
```

- [ ] **Step 9: Create trade journal router**

Create `backend/app/engines/trade_journal/router.py`:
```python
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from app.engines.trade_journal.service import TradeJournalService
from app.engines.trade_journal.schemas import JournalEntry

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])


@router.get("/entries")
async def get_journal_entries(tag: str | None = None):
    service = TradeJournalService()
    entries = service.get_entries(tag=tag)
    return entries


@router.get("/entries/{entry_id}")
async def get_journal_entry(entry_id: int):
    service = TradeJournalService()
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.post("/entries")
async def create_journal_entry(entry: JournalEntry):
    service = TradeJournalService()
    result = service.add_entry(entry)
    return result


@router.patch("/entries/{entry_id}")
async def update_journal_entry(entry_id: int, tags: list[str] | None = None, notes: str | None = None):
    service = TradeJournalService()
    kwargs = {}
    if tags is not None:
        kwargs["tags"] = tags
    if notes is not None:
        kwargs["notes"] = notes
    updated = service.update_entry(entry_id, **kwargs)
    if updated is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return updated


@router.get("/export/csv")
async def export_journal_csv():
    service = TradeJournalService()
    csv_content = service.export_csv()
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trade_journal.csv"},
    )


@router.get("/analytics/tags")
async def get_tag_analytics():
    service = TradeJournalService()
    analytics = service.get_tag_analytics()
    return [a.model_dump() for a in analytics]
```

- [ ] **Step 10: Register router in main app**

Append to `backend/app/main.py`:
```python
from app.engines.trade_journal.router import router as trade_journal_router
app.include_router(trade_journal_router)
```

- [ ] **Step 11: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/trade_journal/ -v`
Expected: PASS

- [ ] **Step 12: Run ALL tests to verify no regressions**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL pass

- [ ] **Step 13: Commit**

```
git add backend/app/database.py backend/app/engines/trade_journal/ backend/tests/engines/trade_journal/ backend/tests/test_database.py
git commit -m "feat: add trade journal enhancements with tags, notes, CSV export, tag analytics, and post-trade analysis"
```

---

## Summary

Phase 7 delivers two work streams:

**Part A — OCI Deployment & CI/CD:**
- Docker Compose with 4 containers (nginx, backend, frontend, redis) with resource limits & health checks
- Nginx reverse proxy with Let's Encrypt SSL
- GitHub Actions CI/CD: test → build → push to OCI Container Registry → SSH deploy → health check
- OCI Object Storage daily backups with 90-day retention
- Uptime monitoring with log rotation
- 14 infra files (configs, scripts, workflows)

**Part B — Advanced Features:**
| Engine | Files | Tests | Endpoints |
|--------|-------|-------|-----------|
| Monte Carlo | 6 | 16 | `POST /risk/monte-carlo/{ticker}`, `POST /risk/monte-carlo/portfolio` |
| Stress Testing | 5 | 6 | `GET /risk/stress-test/scenarios`, `POST /risk/stress-test` |
| Economic Calendar | 6 | 8 | `GET /calendar/economic`, `GET /calendar/economic/impact`, `GET /calendar/economic/alerts` |
| Earnings Calendar | 6 | 5 | `GET /calendar/earnings`, `GET /calendar/earnings/alerts` |
| Sector Rotation | 6 | 5 | `GET /analysis/sector-rotation`, `GET /analysis/sector-rotation/rankings` |
| Trade Journal | 5 | 9 | `GET/POST/PATCH /journal/entries`, `GET /journal/export/csv`, `GET /journal/analytics/tags` |

**Total: ~110 tests across all new code, 38 infra files, 6 new engine packages.**
