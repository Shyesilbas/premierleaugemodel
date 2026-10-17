#!/usr/bin/env bash
# Ubuntu 22.04/24.04, root olarak. Kod /opt/plm içinde olmalı (git clone veya rsync).
set -euo pipefail
cd /opt/plm
timedatectl set-timezone UTC
apt-get update && apt-get install -y python3-venv python3-pip nodejs npm caddy ufw util-linux
python3 -m venv venv && venv/bin/pip install -r requirements.txt
(cd frontend && npm ci && npm run build)
cp deploy/plm-api.service /etc/systemd/system/ && cp deploy/Caddyfile /etc/caddy/Caddyfile
chmod +x deploy/job.sh
systemctl daemon-reload && systemctl enable --now plm-api && systemctl restart caddy
crontab deploy/crontab
# Güvenlik duvarı: gelen her şeyi kapat, yalnızca SSH + Tailscale
ufw default deny incoming && ufw allow OpenSSH && ufw allow in on tailscale0 && ufw --force enable
curl -fsSL https://tailscale.com/install.sh | sh
echo "Şimdi çalıştır:  tailscale up   (linke tıkla, giriş yap)  sonra:  tailscale serve --bg 8080"
