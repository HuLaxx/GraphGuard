# Sentinance Deployment Guide

## 🚀 Deployment Options

### Option 1: Docker Compose (Recommended)

**Production deployment with all services:**

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your actual values (API keys, passwords, etc.)

# 2. Build and start all services
docker compose up -d --build

# 3. Check status
docker compose ps

# 4. View logs
docker compose logs -f api
```

**Services will be available at:**
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8001 |
| API Docs | http://localhost:8001/docs |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

---

### Option 2: Development Mode

For local development with hot-reloading:

```bash
# 1. Start infrastructure only
docker compose -f docker-compose.dev.yml up -d

# 2. Start backend (terminal 1)
cd apps/api
pip install -r requirements.txt
export REDIS_URL=redis://localhost:6380
export DATABASE_URL=postgresql+asyncpg://sentinance:password@localhost:5434/sentinance
uvicorn main:app --reload --port 8001

# 3. Start frontend (terminal 2)
cd apps/web
npm install
npm run dev
```

---

### Option 3: Kubernetes

For cloud-native deployment:

```bash
# 1. Create namespace
kubectl create namespace sentinance

# 2. Create secrets
kubectl create secret generic sentinance-secrets \
  --from-env-file=.env \
  -n sentinance

# 3. Deploy
kubectl apply -k infra/k8s/

# 4. Check pods
kubectl get pods -n sentinance
```

---

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL password |
| `JWT_SECRET` | ✅ | Secret for JWT signing (32+ chars) |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `GROQ_API_KEY` | ⚪ | Groq API key (fallback) |
| `GF_SECURITY_ADMIN_PASSWORD` | ⚪ | Grafana admin password |

---

## 📊 Database Migrations

Run migrations on first deployment:

```bash
cd apps/api
alembic upgrade head
```

---

## 🔍 Health Checks

Verify deployment health:

```bash
# API health
curl http://localhost:8001/health

# Liveness probe
curl http://localhost:8001/health/live

# Readiness probe
curl http://localhost:8001/health/ready
```

---

## 📈 Monitoring

### Prometheus Metrics
Access at: http://localhost:9090

### Grafana Dashboards
1. Open http://localhost:3001
2. Login: admin / (your GF_SECURITY_ADMIN_PASSWORD)
3. Import dashboard from `infra/monitoring/grafana-dashboard.json`

---

## 🔒 Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate strong JWT_SECRET: `openssl rand -hex 32`
- [ ] Enable HTTPS in production (configure in ingress)
- [ ] Review CORS settings in `main.py`
- [ ] Set up firewall rules for exposed ports

---

## 🐛 Troubleshooting

### Docker containers not starting
```bash
# Check logs
docker compose logs

# Reset and rebuild
docker compose down -v
docker compose up -d --build
```

### API connection errors
- Verify `.env` variables are set
- Check if PostgreSQL and Redis are healthy
- Ensure network connectivity between containers

### Frontend build errors
```bash
cd apps/web
rm -rf node_modules .next
npm install
npm run build
```
