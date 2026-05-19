// PM2 process manager configuration — for non-Docker production deployments
// Usage:
//   npm install -g pm2
//   cd backend && pip install -r requirements.txt
//   cd frontend && npm ci && npm run build
//   pm2 start ecosystem.config.js
//   pm2 save
//   pm2 startup   # generates systemd/launchd command to auto-start on reboot

const path = require("path");
const ROOT = __dirname;

module.exports = {
  apps: [
    // ── FastAPI Backend ──────────────────────────────────────────────────────
    {
      name: "propedge-backend",
      script: path.join(ROOT, "backend", ".venv", "bin", "uvicorn"),
      args: "app.main:app --host 0.0.0.0 --port 8000 --workers 4",
      cwd: path.join(ROOT, "backend"),

      // Process management
      instances: 1,           // uvicorn handles its own workers
      autorestart: true,
      watch: false,           // never watch in prod (use deploy script instead)
      max_restarts: 10,
      restart_delay: 3000,
      min_uptime: "5s",

      // Environment
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
      },
      env_production: {
        NODE_ENV: "production",
      },

      // Logging
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: path.join(ROOT, "logs", "backend-error.log"),
      out_file:   path.join(ROOT, "logs", "backend-out.log"),
      merge_logs: true,
      log_type: "json",

      // Graceful shutdown
      kill_timeout: 5000,
      listen_timeout: 8000,
    },

    // ── Next.js Frontend ─────────────────────────────────────────────────────
    {
      name: "propedge-frontend",
      script: "npm",
      args: "start",
      cwd: path.join(ROOT, "frontend"),

      instances: 1,
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 3000,
      min_uptime: "5s",

      env: {
        NODE_ENV: "production",
        PORT: "3000",
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
        NEXT_PUBLIC_WS_URL:  process.env.NEXT_PUBLIC_WS_URL  || "ws://localhost:8000",
      },

      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: path.join(ROOT, "logs", "frontend-error.log"),
      out_file:   path.join(ROOT, "logs", "frontend-out.log"),
      merge_logs: true,

      kill_timeout: 3000,
      listen_timeout: 10000,
    },
  ],

  // ── Deploy configuration (pm2 deploy) ──────────────────────────────────────
  deploy: {
    production: {
      user: process.env.VPS_USER || "ubuntu",
      host: process.env.VPS_HOST || "your-server-ip",
      ref: "origin/main",
      repo: "git@github.com:YOUR_USERNAME/sports-prop-analyzer.git",
      path: "/opt/propedge",
      "pre-deploy-local": "",
      "post-deploy": [
        "cd backend && pip install -r requirements.txt",
        "cd frontend && npm ci --production && npm run build",
        "pm2 reload ecosystem.config.js --env production",
      ].join(" && "),
      "pre-setup": "apt-get install -y git",
      env: {
        NODE_ENV: "production",
      },
    },
  },
};
