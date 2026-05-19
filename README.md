# PropEdge AI — Sports Prop Intelligence Platform

Real-time AI-powered EV analysis for PrizePicks and major sportsbooks. Identifies mispriced player props before the lines move.

```
┌─────────────────────────────────────────────────────────────┐
│  PrizePicks  ──┐                                            │
│  DraftKings  ──┼── Scrapers ── EV Engine ── WebSocket ──── │
│  FanDuel     ──┘                   │           │            │
│  WSPN        ──┐          AI/ML Predictor   Dashboard       │
│  NBA Stats   ──┼── Analytics ─────┘           │            │
│  ESPN        ──┘                          Discord/Telegram  │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **Live prop feed** — WebSocket updates every 30 seconds
- **EV calculator** — Vig-removed fair odds vs PrizePicks lines
- **AI predictions** — XGBoost + LightGBM + RandomForest ensemble
- **Line movement tracker** — Detect steam moves and sharp action
- **Parlay builder** — Correlation-adjusted joint probability engine
- **Kelly sizing** — Fractional Kelly bankroll management
- **Multi-channel alerts** — Discord, Telegram, SMS, Email
- **Player analytics** — Weighted trend projections with matchup grades

---

## Quick Start (Docker — recommended)

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | 4.x+ | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Git | any | [git-scm.com](https://git-scm.com/) |

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/sports-prop-analyzer.git
cd sports-prop-analyzer

# 2. Configure
cp .env.example .env
# Edit .env and add at minimum: THE_ODDS_API_KEY

# 3. Launch
docker compose up -d

# 4. Open
# Frontend:  http://localhost
# API Docs:  http://localhost/docs
```

That's it. Docker handles PostgreSQL, Redis, the backend, and the Next.js frontend.

---

## Windows Setup (step-by-step for beginners)

### Method A — Automated (recommended)

Open **PowerShell as Administrator** and run:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
cd C:\path\to\sports-prop-analyzer
.\scripts\setup-windows.ps1
```

The script installs Git, Node.js, Python 3.11, Docker Desktop, and all project dependencies automatically.

### Method B — Manual

**Step 1 — Install Docker Desktop**

1. Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Run the installer and follow the prompts
3. Restart your computer when prompted
4. Open Docker Desktop and wait for "Engine running" (green icon in the system tray)

**Step 2 — Install Git**

```powershell
winget install Git.Git
```

Restart your terminal after installation.

**Step 3 — Clone the project**

```powershell
git clone https://github.com/YOUR_USERNAME/sports-prop-analyzer.git
cd sports-prop-analyzer
```

**Step 4 — Configure environment**

```powershell
Copy-Item .env.example .env
notepad .env
```

At minimum, set `THE_ODDS_API_KEY` (free at [the-odds-api.com](https://the-odds-api.com)).

**Step 5 — Start the platform**

```powershell
docker compose up -d
```

Wait ~2 minutes for all services to start, then open `http://localhost`.

---

## Local Development (without Docker)

For active development you'll want hot-reload on both backend and frontend.

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

# You still need PostgreSQL and Redis — easiest via Docker:
docker compose up postgres redis -d

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

---

## API Keys Reference

| Key | Required | Where to get | Free tier |
|-----|----------|-------------|-----------|
| `THE_ODDS_API_KEY` | **Yes** | [the-odds-api.com](https://the-odds-api.com) | 500 req/month |
| `DISCORD_WEBHOOK_URL` | No | Discord Server → Integrations → Webhooks | Free |
| `TELEGRAM_BOT_TOKEN` | No | [@BotFather](https://t.me/BotFather) on Telegram | Free |
| `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` + `TWILIO_FROM_NUMBER` | No | [twilio.com](https://twilio.com) | Trial credit |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | No | Gmail SMTP or SendGrid | Free |

To get a free TheOddsAPI key:
1. Go to [the-odds-api.com](https://the-odds-api.com) and click "Get API Key"
2. Sign up with your email
3. Copy the key into `.env` as `THE_ODDS_API_KEY=your_key_here`

---

## Project Structure

```
sports-prop-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   │   ├── props.py          # /api/v1/props
│   │   │   ├── analytics.py      # /api/v1/analytics
│   │   │   ├── line_movement.py  # /api/v1/line-movement
│   │   │   ├── players.py        # /api/v1/players
│   │   │   ├── settings_api.py   # /api/v1/settings
│   │   │   └── websocket.py      # /ws
│   │   ├── scrapers/       # Data ingestion
│   │   │   ├── prizepicks.py
│   │   │   ├── odds_api.py
│   │   │   ├── draftkings.py
│   │   │   ├── fanduel.py
│   │   │   ├── wspn.py
│   │   │   ├── nba_api.py
│   │   │   ├── espn.py
│   │   │   ├── injury.py
│   │   │   └── sleeper.py
│   │   ├── services/       # Business logic
│   │   │   ├── ev_calculator.py
│   │   │   ├── prop_analyzer.py
│   │   │   ├── player_analytics.py
│   │   │   ├── correlation.py
│   │   │   ├── kelly_criterion.py
│   │   │   └── alerts.py
│   │   ├── ml/             # Machine learning
│   │   │   ├── feature_engineering.py
│   │   │   ├── model_trainer.py
│   │   │   └── predictor.py
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── middleware/     # Rate limiting, logging
│   │   ├── tasks/          # APScheduler background jobs
│   │   ├── utils/          # Redis cache, helpers
│   │   ├── config.py       # Pydantic settings
│   │   ├── database.py     # Async SQLAlchemy
│   │   └── main.py         # FastAPI app entry point
│   ├── alembic/            # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   └── src/
│       ├── app/            # Next.js App Router pages
│       │   ├── page.tsx          # Dashboard
│       │   ├── props/page.tsx    # All Props
│       │   ├── analytics/page.tsx
│       │   ├── bankroll/page.tsx
│       │   ├── live-props/page.tsx  # WebSocket live feed
│       │   ├── line-movement/page.tsx
│       │   └── settings/page.tsx
│       ├── components/
│       │   ├── layout/       # Sidebar, Navbar
│       │   ├── props/        # PropCard, PropFilters
│       │   ├── charts/       # EV, HitRate, OddsMovement
│       │   ├── dashboard/    # StatsOverview, TopPicks, LiveFeed
│       │   ├── bankroll/     # KellyCalculator
│       │   └── ui/           # AnimatedCard, Toast, shared UI
│       ├── hooks/            # useProps, useWebSocket
│       ├── lib/              # types, api client, websocket
│       └── store/            # Zustand stores
│
├── docker/
│   └── nginx.conf          # NGINX reverse proxy
├── .github/
│   └── workflows/ci.yml    # GitHub Actions CI/CD
├── scripts/
│   ├── setup-windows.ps1   # Windows dev setup
│   └── setup-ubuntu.sh     # Ubuntu VPS production setup
├── ecosystem.config.js     # PM2 process config
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## EV Analysis Explained

### How Expected Value is calculated

```
1. Fetch PrizePicks line:          over/under 24.5 points
2. Fetch sportsbook odds:          DraftKings, FanDuel, Caesars...
3. Remove vig (juice):             American odds → implied prob → normalized
4. Get fair probability:           P(over) = 0.54
5. Calculate EV:                   EV% = ((fair_prob × 2) - 1) × 100
                                        = (0.54 × 2 - 1) × 100 = +8%
```

### Edge Classification

| EV%       | Label    | Action                    |
|-----------|----------|---------------------------|
| 10%+      | ELITE    | Max Kelly bet             |
| 7–10%     | STRONG   | Full unit                 |
| 5–7%      | GOOD     | 0.75 unit                 |
| 3–5%      | SLIGHT   | 0.5 unit                  |
| 1–3%      | MARGINAL | Skip or 0.25 unit         |
| < 1%      | NEGATIVE | Avoid                     |

### Steam Move Detection

A **steam move** is flagged when:
- The consensus line moves ≥ 1 unit within a short window
- Multiple sportsbooks move simultaneously
- This signals sharp/syndicate money and should be treated as confirmation

---

## Data Flow

```
Every 30 seconds (APScheduler):
┌──────────────────────────────────────────────────────┐
│  1. PrizePicks API → 200-400 active projections      │
│  2. TheOddsAPI → Player prop odds for each sport     │
│  3. DraftKings / FanDuel → Additional book lines     │
│  4. WSPN → Statistical projections                   │
│  5. Name fuzzy match (SequenceMatcher ≥ 0.80)        │
│  6. Vig removal → Fair probabilities                 │
│  7. EV calculation → Edge classification             │
│  8. ML prediction overlay (if models trained)        │
│  9. Upsert to PostgreSQL                             │
│  10. Broadcast updated props via WebSocket           │
│  11. Check alert thresholds → Discord/Telegram/SMS   │
└──────────────────────────────────────────────────────┘
```

---

## Deployment

### Railway (easiest)

1. Fork this repository on GitHub
2. Create a new project at [railway.app](https://railway.app)
3. Click "Deploy from GitHub repo"
4. Add a PostgreSQL service (Railway provides one)
5. Add a Redis service (Railway provides one)
6. Set environment variables from `.env.example`
7. Railway auto-detects Docker and deploys

### Render

1. Create account at [render.com](https://render.com)
2. New → "Blueprint" → connect your GitHub repo
3. Create a `render.yaml` in the repo root:

```yaml
services:
  - type: web
    name: propedge-backend
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    envVars:
      - fromGroup: propedge-secrets

  - type: web
    name: propedge-frontend
    runtime: docker
    dockerfilePath: ./frontend/Dockerfile
    envVars:
      - key: NEXT_PUBLIC_API_URL
        value: https://propedge-backend.onrender.com

databases:
  - name: propedge-postgres
    plan: free

  - name: propedge-redis
    plan: free
```

### DigitalOcean App Platform

1. Go to [cloud.digitalocean.com](https://cloud.digitalocean.com) → Apps
2. Connect GitHub repository
3. DigitalOcean auto-detects the `docker-compose.yml`
4. Set environment variables in the dashboard
5. Choose "Basic" plan ($12/month) for hobby use

### Ubuntu VPS (full control)

```bash
# On your VPS (Ubuntu 22.04+)
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/sports-prop-analyzer/main/scripts/setup-ubuntu.sh | sudo bash

# Copy the project
cd /opt/propedge
git clone https://github.com/YOUR_USERNAME/sports-prop-analyzer.git .

# Configure
cp .env.example .env && nano .env

# Get SSL cert (replace with your domain)
certbot certonly --standalone -d yourdomain.com
mkdir -p docker/ssl
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   docker/ssl/
# Uncomment the SSL block in docker/nginx.conf

# Start
docker compose up -d
```

### PM2 (non-Docker)

For servers where you want to run without Docker:

```bash
npm install -g pm2

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend (build first)
cd ../frontend
npm ci && npm run build

# Start both with PM2
cd ..
pm2 start ecosystem.config.js
pm2 save
pm2 startup   # follow the printed command to enable auto-start
```

---

## Makefile Commands

```bash
make up          # docker compose up -d
make down        # docker compose down
make logs        # stream all service logs
make backend     # stream backend logs only
make frontend    # stream frontend logs only
make install     # install all dependencies (no Docker)
make migrate     # run alembic migrations
make migration name=add_something   # create new migration
make format      # run ruff + prettier
```

---

## API Documentation

The interactive API docs are at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/props/top` | Top EV props (cached 30s) |
| GET | `/api/v1/props/best-bets` | EV ≥ 5% props |
| GET | `/api/v1/props/mispriced` | Largest PP vs book discrepancy |
| GET | `/api/v1/props/sharp-action` | Stale lines + boosted props |
| GET | `/api/v1/props/parlay-builder` | Correlated parlay legs |
| POST | `/api/v1/props/refresh` | Trigger manual data refresh |
| GET | `/api/v1/analytics/dashboard` | Aggregate stats |
| GET | `/api/v1/line-movement/recent` | Recent line movements |
| GET | `/api/v1/line-movement/steam-moves` | Steam move alerts |
| GET | `/api/v1/players/{id}/analytics` | Player trend data |
| GET | `/api/v1/players/{id}/projection` | AI-weighted projection |
| WS  | `/ws/props` | Live prop updates (30s interval) |

---

## Troubleshooting

### "Docker daemon not running"
Start Docker Desktop and wait for the whale icon in the system tray to stop animating.

### "Port 80 already in use"
Something else is using port 80. Either stop it, or change the NGINX port in `docker-compose.yml`:
```yaml
nginx:
  ports:
    - "8080:80"   # access at http://localhost:8080
```

### "No props showing on dashboard"
The TheOddsAPI key is missing or invalid. Check your `.env` file:
```
THE_ODDS_API_KEY=your_actual_key_here
```
Then restart: `docker compose restart backend`

### "WebSocket not connecting"
The frontend connects to the WebSocket using `NEXT_PUBLIC_WS_URL`. In Docker, this is routed through NGINX. Make sure `NEXT_PUBLIC_WS_URL` matches your server address.

### "ML models not trained"
The ML models train automatically at 3 AM UTC once enough historical data is collected. Until then, the EV calculator falls back to the statistical normal CDF approximation — all core features still work.

### Backend crashes on startup
Check logs: `docker compose logs backend`

Common causes:
- Database not ready — postgres container still initializing. Wait 30s and retry.
- Missing required env var — check `config.py` for required fields
- Migration needed — run `docker compose exec backend alembic upgrade head`

### Frontend build fails
```bash
cd frontend
rm -rf .next node_modules
npm install --legacy-peer-deps
npm run build
```

### Out of memory on a 1GB VPS
1. Disable ML retraining: comment out `job_retrain_models` in `apscheduler_tasks.py`
2. Reduce PostgreSQL memory: add `command: postgres -c shared_buffers=64MB` to the postgres service in `docker-compose.yml`

---

## Architecture Decisions

**Why APScheduler instead of Celery?**
Celery requires a separate worker process and message broker. APScheduler runs in-process with async jobs — simpler for a single-server deployment with our refresh frequency.

**Why fuzzy name matching?**
PrizePicks uses full names ("LeBron James") while some books use abbreviated formats. `difflib.SequenceMatcher` with a 0.80 threshold handles 95%+ of cases without requiring a name normalization database.

**Why not scrape PrizePicks with Playwright?**
The PrizePicks public API (`/projections`) returns clean JSON with all the data we need. Playwright is reserved for WSPN and other sources that require JavaScript execution.

**Why Redis for rate limiting?**
In-process rate limiting doesn't work with multiple uvicorn workers. The Redis sliding window (ZADD-based) is accurate across all processes and falls back to an in-memory dict when Redis is unavailable.

---

## License

MIT — use freely, bet responsibly.

> **Disclaimer**: This tool is for informational and educational purposes. Sports betting involves financial risk. Past EV does not guarantee future results. Only bet what you can afford to lose.
