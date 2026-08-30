# AeroGuard Stage PR3 Staging Deployment & Operational Runbook

## 1. Overview
This runbook provides step-by-step instructions for deploying, operating, verifying, and recovering the AeroGuard platform on a Linux staging environment using Docker Compose (`docker-compose.prod.yml`).

---

## 2. Prerequisites & Environment Setup

### Staging Host Requirements
- Linux server (Ubuntu 24.04 LTS or Debian 12)
- 4 vCPU, 8 GB RAM, 50 GB SSD
- Docker Engine 26.0+ & Docker Compose v2.27+
- Open ports: `80/tcp` (HTTP) and `443/tcp` (HTTPS)

### Environment Configuration
1. Clone the repository to the staging host:
   ```bash
   git clone https://github.com/Tanishk756/AeroGuard.git /opt/aeroguard
   cd /opt/aeroguard
   ```
2. Create production `.env` configuration file from template:
   ```bash
   cp .env.example .env
   ```
3. Update `.env` with production values:
   ```env
   AEROGUARD_ENVIRONMENT=production
   AEROGUARD_SECRET_KEY=CHANGE_ME_TO_A_64_CHAR_RANDOM_STRING
   AEROGUARD_ALLOWED_ORIGINS=["https://aeroguard.staging.domain"]
   POSTGRES_USER=aeroguard_user
   POSTGRES_PASSWORD=CHANGE_ME_SECURE_DB_PASSWORD
   POSTGRES_DB=aeroguard_prod
   AEROGUARD_DATABASE_URL=postgresql+psycopg2://aeroguard_user:CHANGE_ME_SECURE_DB_PASSWORD@postgres:5432/aeroguard_prod
   AEROGUARD_RATE_LIMIT_STORAGE_URL=redis://redis:6379/0
   AEROGUARD_S3_ACCESS_KEY=CHANGE_ME_MINIO_ACCESS_KEY
   AEROGUARD_S3_SECRET_KEY=CHANGE_ME_MINIO_SECRET_KEY
   ```

---

## 3. Staging Deployment Procedure

### Step 1: Validate Compose Configuration
```bash
docker compose -f docker-compose.prod.yml config
```

### Step 2: Build Production Containers
```bash
docker compose -f docker-compose.prod.yml build
```

### Step 3: Launch Multi-Container Stack
```bash
docker compose -f docker-compose.prod.yml up -d
```

### Step 4: Verify Container Status & Health
```bash
docker compose -f docker-compose.prod.yml ps
```
Expected running services:
- `nginx` (Up, Healthy, listening on port 80/443)
- `migration` (Exited 0 after running `alembic upgrade head`)
- `backend` (Up, Healthy, port 8000 internal)
- `postgres` (Up, Healthy, port 5432 internal)
- `redis` (Up, Healthy, port 6379 internal)
- `minio` (Up, Healthy, port 9000 internal)

---

## 4. Operational Health & Verification Commands

### Check Live Application Health
```bash
curl -i http://localhost/health/live
curl -i http://localhost/health/ready
```

### Scrape Prometheus Metrics
```bash
curl -i http://localhost/metrics
```

### Tail Container Logs
```bash
docker compose -f docker-compose.prod.yml logs -f --tail=100 backend
```

---

## 5. Staging PostgreSQL Backup & Restore Procedure

### Database Backup (`pg_dump`)
```bash
mkdir -p /opt/aeroguard/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec -t aeroguard-prod-postgres-1 pg_dump -U aeroguard_user -d aeroguard_prod > /opt/aeroguard/backups/aeroguard_backup_${TIMESTAMP}.sql
```

### Database Restore Procedure
1. Create temporary restore database:
   ```bash
   docker exec -it aeroguard-prod-postgres-1 psql -U aeroguard_user -d postgres -c "CREATE DATABASE aeroguard_restore_test;"
   ```
2. Restore backup into test database:
   ```bash
   docker exec -i aeroguard-prod-postgres-1 psql -U aeroguard_user -d aeroguard_restore_test < /opt/aeroguard/backups/aeroguard_backup_${TIMESTAMP}.sql
   ```
3. Verify restored tables and Alembic schema head:
   ```bash
   docker exec -it aeroguard-prod-postgres-1 psql -U aeroguard_user -d aeroguard_restore_test -c "\dt"
   docker exec -it aeroguard-prod-postgres-1 psql -U aeroguard_user -d aeroguard_restore_test -c "SELECT * FROM alembic_version;"
   ```
4. Drop temporary restore database after verification:
   ```bash
   docker exec -it aeroguard-prod-postgres-1 psql -U aeroguard_user -d postgres -c "DROP DATABASE aeroguard_restore_test;"
   ```

---

## 6. Failure Recovery Procedures

### Scenario A: PostgreSQL Database Crash
1. Restart PostgreSQL container:
   ```bash
   docker compose -f docker-compose.prod.yml restart postgres
   ```
2. Verify application auto-recovery when readiness probe returns `HTTP 200 OK`.

### Scenario B: Redis Cache Disconnection
1. Restart Redis container:
   ```bash
   docker compose -f docker-compose.prod.yml restart redis
   ```
2. Verify rate-limiter fallback behavior and automatic reconnection.

### Scenario C: Application Rollback Procedure
If a deployment fails, execute database downgrade and code rollback:
```bash
docker compose -f docker-compose.prod.yml run --rm migration alembic downgrade -1
git checkout PREVIOUS_STABLE_COMMIT
docker compose -f docker-compose.prod.yml up -d --build
```
