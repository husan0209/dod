# DOD Platform - Deployment Guide

## Quick Start

### Prerequisites
- Ubuntu 22.04+ VPS with 4GB RAM, 100GB SSD
- Domain name with DNS records
- GitHub repository access
- Payment gateway API keys

### Step 1: Server Initialization

```bash
# SSH into server as root
ssh root@yourdomain.com

# Clone script execution
curl -fsSL https://raw.githubusercontent.com/yourusername/dod/main/deploy/scripts/init-server.sh | bash -s yourdomain.com deploy

# The script will:
# - Update system packages
# - Install Docker & Docker Compose
# - Create deploy user
# - Setup directories
# - Configure firewall
# - Generate SSL certificates
```

### Step 2: Clone Repository

```bash
su - deploy
cd /opt/dod
git clone https://github.com/yourusername/dod.git .
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.production.example .env.production

# Edit with your values
nano .env.production

# Required variables:
DB_NAME=dod_prod
DB_USER=dod_user
DB_PASSWORD=<generate-strong-password>
REDIS_PASSWORD=<generate-strong-password>
SECRET_KEY=<generate-with-django>
DOMAIN=yourdomain.com
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Step 4: Deploy Application

```bash
# Run deployment script
bash deploy/scripts/deploy.sh production

# The script will:
# - Create pre-deployment backup
# - Build Docker images
# - Start services
# - Run migrations
# - Collect static files
# - Run health checks
```

### Step 5: Verify Deployment

```bash
# Check service status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f web

# Run health check
bash deploy/scripts/health-check.sh yourdomain.com
```

## Production Checklist

### Pre-Deployment
- [ ] Domain DNS configured
- [ ] SSL certificates generated
- [ ] Database backups configured
- [ ] Monitoring setup configured
- [ ] Slack/email notifications ready
- [ ] Security audit completed
- [ ] Load testing passed
- [ ] Documentation reviewed

### Post-Deployment
- [ ] Application loads without errors
- [ ] All endpoints responding
- [ ] Database migrations completed
- [ ] Static files accessible
- [ ] Admin dashboard accessible
- [ ] Health checks passing
- [ ] Monitoring receiving data
- [ ] Backups running
- [ ] Logs being collected

## Maintenance

### Daily Tasks
```bash
# Check service health
docker compose -f docker-compose.prod.yml ps

# View error logs
docker compose -f docker-compose.prod.yml logs --tail=100 web
docker compose -f docker-compose.prod.yml logs --tail=100 celery_worker
```

### Weekly Tasks
```bash
# Review security updates
apt update && apt list --upgradable

# Verify backups
ls -lah deploy/backups/dod_backup_*

# Check disk usage
df -h
du -sh /opt/dod
```

### Monthly Tasks
```bash
# Update base images
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull nginx:latest
docker compose -f docker-compose.prod.yml up -d

# Rotate logs
systemctl restart rsyslog

# Database maintenance
docker compose -f docker-compose.prod.yml exec db \
    pg_maintenance_tool --analyze --vacuum
```

## Updating Application

```bash
# 1. Pull latest code
git pull origin main

# 2. Review changes
git log --oneline -5

# 3. Create backup
bash deploy/backups/backup.sh

# 4. Deploy
bash deploy/scripts/deploy.sh production

# 5. Monitor
docker compose -f docker-compose.prod.yml logs -f web

# 6. If issues, rollback
bash deploy/scripts/rollback.sh
```

## Troubleshooting

### Services not starting
```bash
# Check Docker logs
docker logs dod_web
docker logs dod_celery_worker
docker logs dod_db

# Restart services
docker compose -f docker-compose.prod.yml restart web
docker compose -f docker-compose.prod.yml restart celery_worker
```

### Database connection errors
```bash
# Check PostgreSQL
docker compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME -c "SELECT 1"

# Check Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping
```

### High CPU/Memory usage
```bash
# Check metrics
docker stats

# Review logs for errors
docker compose -f docker-compose.prod.yml logs --tail=200 web

# Check Grafana dashboard
# Visit: https://yourdomain.com/grafana/
```

### Performance issues
```bash
# Check slow queries
docker compose -f docker-compose.prod.yml exec db \
    pg_log_analyze --slow-queries

# Review Celery queue
docker compose -f docker-compose.prod.yml exec celery_worker \
    celery -A config inspect active

# Monitor WebSocket connections
docker compose -f docker-compose.prod.yml logs channels
```

## Backup & Restore

### Manual Backup
```bash
bash deploy/backups/backup.sh

# List backups
ls -lah deploy/backups/dod_backup_*
```

### Restore from Backup
```bash
# List available backups
ls deploy/backups/dod_backup_*_db.sql.gz

# Restore database
gunzip -c deploy/backups/dod_backup_YYYYMMDD_HHMMSS_db.sql.gz | \
    docker compose -f docker-compose.prod.yml \
    exec -T db psql -U $DB_USER $DB_NAME
```

## Monitoring & Alerts

### Prometheus
- URL: http://localhost:9090
- Config: deploy/monitoring/prometheus/prometheus.yml

### Grafana
- URL: https://yourdomain.com/grafana
- Default: admin/admin (change immediately!)

### AlertManager
- Reports to: Slack, PagerDuty
- Config: deploy/monitoring/alertmanager/alertmanager.yml

## Support & Documentation

- API Documentation: /api/docs/
- Admin Panel: /admin-panel/
- Health Check: /health/
- Logs: docker compose logs
- Metrics: http://localhost:9090

## Security

### SSL/TLS Certificate Renewal
```bash
# Automatic renewal via Certbot
# (Already configured in docker-compose.prod.yml)

# Manual renewal if needed
/usr/bin/certbot renew --non-interactive
```

### Firewall Rules
```bash
# SSH
ufw allow 22/tcp

# HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Monitoring (restrict to office IP)
ufw allow from 203.0.113.0/24 to any port 9090
```

## Support Contacts

- DevOps: devops@example.com
- Database Admin: dba@example.com
- Security: security@example.com
- On-call: ops-oncall@example.com

## References

- Docker Documentation: https://docs.docker.com/
- Django Documentation: https://docs.djangoproject.com/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Redis Documentation: https://redis.io/documentation
- Nginx Documentation: https://nginx.org/en/docs/
