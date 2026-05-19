#!/usr/bin/env bash
# PropEdge AI — Ubuntu/Debian VPS production setup
# Tested on Ubuntu 22.04 LTS and 24.04 LTS
# Run as root or with sudo privileges:
#   curl -fsSL https://your-domain.com/setup-ubuntu.sh | bash
#   — OR —
#   bash scripts/setup-ubuntu.sh

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
step()  { echo -e "\n${CYAN}[STEP] $*${NC}"; }
ok()    { echo -e "${GREEN}  [OK] $*${NC}"; }
warn()  { echo -e "${YELLOW} [WARN] $*${NC}"; }
fail()  { echo -e "${RED} [FAIL] $*${NC}"; exit 1; }

# ── Detect OS ─────────────────────────────────────────────────────────────────
[[ "$(uname -s)" == "Linux" ]] || fail "This script is for Linux only."
source /etc/os-release 2>/dev/null || true
step "Detected OS: ${PRETTY_NAME:-Linux}"

# ── 1. System update ──────────────────────────────────────────────────────────
step "Updating system packages"
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget git unzip build-essential \
    ca-certificates gnupg lsb-release \
    software-properties-common apt-transport-https
ok "System packages updated"

# ── 2. Docker ─────────────────────────────────────────────────────────────────
step "Installing Docker Engine"
if ! command -v docker &>/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    ok "Docker installed and started"
else
    ok "Docker already installed: $(docker --version)"
fi

# Add current user to docker group (avoids needing sudo for docker commands)
DEPLOY_USER="${SUDO_USER:-$(whoami)}"
if [[ "$DEPLOY_USER" != "root" ]]; then
    usermod -aG docker "$DEPLOY_USER"
    warn "Added $DEPLOY_USER to docker group. Log out and back in for this to take effect."
fi

# ── 3. Clone the repository ───────────────────────────────────────────────────
step "Setting up application directory"
APP_DIR="/opt/propedge"
if [[ ! -d "$APP_DIR" ]]; then
    mkdir -p "$APP_DIR"
    warn "Created $APP_DIR. Copy your project files here or clone from git:"
    warn "  git clone https://github.com/YOUR_USERNAME/sports-prop-analyzer $APP_DIR"
else
    ok "App directory exists: $APP_DIR"
fi
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

# ── 4. Environment file ───────────────────────────────────────────────────────
step "Environment configuration"
if [[ -f "$APP_DIR/.env.example" && ! -f "$APP_DIR/.env" ]]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    warn "Created $APP_DIR/.env — ADD YOUR API KEYS before starting!"
elif [[ -f "$APP_DIR/.env" ]]; then
    ok ".env already exists"
fi

# ── 5. Firewall (UFW) ─────────────────────────────────────────────────────────
step "Configuring firewall (UFW)"
apt-get install -y -qq ufw
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
ok "UFW configured: SSH, HTTP, HTTPS allowed"

# ── 6. SSL via Certbot (optional) ─────────────────────────────────────────────
step "Certbot (Let's Encrypt SSL)"
if ! command -v certbot &>/dev/null; then
    apt-get install -y -qq certbot
    ok "Certbot installed"
    warn "To get SSL cert, run:"
    warn "  certbot certonly --standalone -d yourdomain.com"
    warn "Then copy certs to $APP_DIR/docker/ssl/ and uncomment SSL config in docker/nginx.conf"
else
    ok "Certbot already installed"
fi

# ── 7. Systemd service for Docker Compose ─────────────────────────────────────
step "Creating systemd service for auto-start"
cat > /etc/systemd/system/propedge.service << EOF
[Unit]
Description=PropEdge AI Sports Prop Platform
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=120
Restart=on-failure
RestartSec=10
User=$DEPLOY_USER
Group=docker

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable propedge.service
ok "systemd service 'propedge' created and enabled"

# ── 8. Deployment script ──────────────────────────────────────────────────────
step "Creating deploy helper script"
cat > "$APP_DIR/deploy.sh" << 'DEPLOY'
#!/usr/bin/env bash
# Zero-downtime deploy: pull latest, rebuild changed images, restart
set -euo pipefail
cd /opt/propedge
echo "[deploy] Pulling latest code..."
git pull origin main
echo "[deploy] Rebuilding changed images..."
docker compose build --parallel
echo "[deploy] Rolling restart..."
docker compose up -d --remove-orphans
docker image prune -f
echo "[deploy] Done at $(date). Containers:"
docker compose ps
DEPLOY
chmod +x "$APP_DIR/deploy.sh"
ok "Deploy script at $APP_DIR/deploy.sh"

# ── 9. Log rotation ───────────────────────────────────────────────────────────
step "Configuring log rotation"
cat > /etc/logrotate.d/propedge << EOF
/opt/propedge/docker/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $DEPLOY_USER $DEPLOY_USER
}
EOF
ok "Log rotation configured (14-day retention)"

# ── 10. Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  PropEdge AI — VPS setup complete!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Next steps:"
echo "  1. Copy your project to $APP_DIR (or git clone)"
echo "  2. Edit $APP_DIR/.env — add THE_ODDS_API_KEY and other secrets"
echo "  3. (Optional) Get SSL cert: certbot certonly --standalone -d yourdomain.com"
echo "     Then copy /etc/letsencrypt/live/yourdomain.com/*.pem to $APP_DIR/docker/ssl/"
echo "  4. Start the platform:"
echo -e "     ${YELLOW}cd $APP_DIR && docker compose up -d${NC}"
echo ""
echo "  Management commands:"
echo -e "     ${YELLOW}docker compose logs -f backend${NC}     # stream backend logs"
echo -e "     ${YELLOW}docker compose restart backend${NC}     # restart backend only"
echo -e "     ${YELLOW}bash $APP_DIR/deploy.sh${NC}            # zero-downtime redeploy"
echo -e "     ${YELLOW}systemctl status propedge${NC}          # check service status"
echo ""
echo "  App URLs (replace with your domain/IP):"
echo "    Frontend:  http://YOUR_SERVER_IP"
echo "    API Docs:  http://YOUR_SERVER_IP/docs"
echo ""
