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

echo "[6/6] Setting up Setting up backup cron..."
cd /home/opc/portfolio-mgr
bash infra/scripts/schedule-backup.sh

echo "=== Init complete! ==="
echo "Next steps:"
echo "  1. cd /home/opc/portfolio-mgr"
echo "  2. cp backend/.env.example backend/.env && vi backend/.env"
echo "  3. Copy GitHub Actions secrets from the repo settings"
echo "  4. Run: docker compose up -d"
echo "  5. Run: bash infra/scripts/setup-ssl.sh yourdomain.com you@email.com"