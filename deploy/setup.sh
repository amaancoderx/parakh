#!/usr/bin/env bash
# Runs on the server (Ubuntu 24.04), from deploy/aws.sh. Safe to run again.
set -euo pipefail
cd ~/parakh

sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg caddy > /dev/null
command -v uv > /dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync --no-dev --quiet

# The service, restarted if it ever stops.
sudo tee /etc/systemd/system/parakh.service > /dev/null <<UNIT
[Unit]
Description=Parakh
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/parakh
Environment=PARAKH_ACCESS_CODE=${PARAKH_ACCESS_CODE}
ExecStart=/home/ubuntu/.local/bin/uv run --no-dev uvicorn harness.service:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

# HTTPS in front of it: Caddy gets the certificate by itself.
sudo tee /etc/caddy/Caddyfile > /dev/null <<CADDY
${HOST} {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
CADDY

sudo systemctl daemon-reload
sudo systemctl enable --now parakh > /dev/null 2>&1
sudo systemctl restart parakh caddy
for i in $(seq 1 30); do curl -sf localhost:8000/api/health > /dev/null && break; sleep 1; done
curl -s localhost:8000/api/health
