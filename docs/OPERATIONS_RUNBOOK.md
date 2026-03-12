# DOD Platform - Operations Runbook

## On-Call Procedures

### First Response
1. Check Slack/email alerts
2. Log into Grafana: https://yourdomain.com/grafana
3. Assess severity: Critical/High/Medium/Low
4. Document incident time and details
5. Notify team if Critical

### Alert Levels

**CRITICAL** (P1 - Immediate action required)
- Database down
- Application errors > 5% of requests
- Complete service unavailable
- Security breach indicator

**HIGH** (P2 - Within 30 minutes)
- Response time > 5 seconds
- Memory usage > 90%
- Disk usage > 85%
- Celery queue delay > 5 minutes

**MEDIUM** (P3 - Within 2 hours)
- Non-critical errors appearing
- Slow queries detected
- Cache hit rate < 80%

**LOW** (P4 - Within 24 hours)
- Warnings in logs
- Monitoring configuration issues
- Documentation updates needed

## Common Issues & Solutions

### 1. Application Not Responding

```bash
# Check status
docker compose -f docker-compose.prod.yml ps

# View recent errors
docker compose -f docker-compose.prod.yml logs --tail=100 web

# Check CPU/Memory
docker stats --no-stream

# Restart if healthy
docker compose -f docker-compose.prod.yml restart web

# Or restart all
docker compose -f docker-compose.prod.yml up -d
```

### 2. High Error Rate

```bash
# Check logs for patterns
docker compose -f docker-compose.prod.yml logs web | grep -i error | tail -50

# Check database
docker compose -f docker-compose.prod.yml exec db \
    psql -U $DB_USER -d $DB_NAME -c "SELECT 1"

# Check Redis
docker compose -f docker-compose.prod.yml exec redis \
    redis-cli -a $REDIS_PASSWORD PING

# Check Celery
docker compose -f docker-compose.prod.yml exec celery_worker \
    celery -A config inspect active
```

### 3. Database Issues

```bash
# Check if running
docker compose -f docker-compose.prod.yml ps db

# Test connection
docker compose -f docker-compose.prod.yml exec db \
    psql -U $DB_USER -d $DB_NAME -c "SELECT now()"

# Check active connections
docker compose -f docker-compose.prod.yml exec db \
    psql -U $DB_USER -d $DB_NAME -c \
    "SELECT count(*) FROM pg_stat_activity where state != 'idle'"

# Check disk space
docker compose -f docker-compose.prod.yml exec db \
    psql -U $DB_USER -d $DB_NAME -c \
    "SELECT pg_pretty_size(pg_database_size('$DB_NAME'))"

# If hung queries, terminate
docker compose -f docker-compose.prod.yml exec db \
    psql -U $DB_USER -d $DB_NAME -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query != 'SELECT 1' AND state='active'"
```

### 4. Out of Disk Space

```bash
# Check usage
df -h

# Remove old Docker images
docker system prune -a

# Remove unused volumes
docker volume prune

# Rotate logs manually
find /var/log/dod -name "*.log" -mtime +30 -delete

# Check Docker sizes
du -sh /var/lib/docker/*
```

### 5. Celery Queue Backlog

```bash
# Check queue depth
docker compose -f docker-compose.prod.yml exec celery_worker \
    celery -A config inspect reserved

# View pending tasks
docker compose -f docker-compose.prod.yml exec celery_worker \
    celery -A config inspect active

# Clear queue if necessary (WARNING: loses tasks)
docker compose -f docker-compose.prod.yml exec redis \
    redis-cli -a $REDIS_PASSWORD FLUSHDB

# Restart workers
docker compose -f docker-compose.prod.yml restart celery_worker
```

### 6. SSL Certificate Issues

```bash
# Check certificate
docker exec dod_nginx openssl x509 -in /etc/nginx/ssl/live/$DOMAIN/fullchain.pem -text

# Check days remaining
docker exec dod_nginx openssl x509 -in /etc/nginx/ssl/live/$DOMAIN/fullchain.pem -noout -dates

# Renew if needed
docker compose -f docker-compose.prod.yml exec certbot \
    certbot renew --force-renewal
```

### 7. Memory Leak Suspected

```bash
# Monitor memory over time
docker stats --no-stream dod_web

# Check for potential issues
docker compose -f docker-compose.prod.yml logs web | grep -i "memory\|leak"

# Restart to reset
docker compose -f docker-compose.prod.yml restart web

# If persists, check code for:
# - Unclosed database connections
# - Unbounded caches
# - Circular references
```

### 8. Network Connectivity Issues

```bash
# Test external connectivity
docker compose -f docker-compose.prod.yml exec web \
    curl -I https://api.example.com

# Check DNS
docker compose -f docker-compose.prod.yml exec web \
    nslookup yourdomain.com

# Check firewall rules
ufw status

# Check nginx
docker compose -f docker-compose.prod.yml logs nginx | grep -i error
```

## Escalation Path

1. **On-Call Engineer** (First responder)
   - Assess severity
   - Document incident
   - Take initial action

2. **Team Lead** (If Critical or unresolved in 15 min)
   - Notify: @devops-lead
   - Coordinate response
   - Communicate to stakeholders

3. **CTO/Manager** (If:)
   - Service down > 1 hour
   - Customer impact > 1000 users
   - Data loss or security breach
   - Notify: @cto, @vp-engineering

## Incident Report Template

```
INCIDENT REPORT
===============
Date: YYYY-MM-DD HH:MM UTC
Duration: X minutes
Severity: Critical/High/Medium/Low

Issue:
- What happened?
- How many users affected?
- What was the impact?

Timeline:
- HH:MM - Alert triggered
- HH:MM - On-call engaged
- HH:MM - Root cause identified
- HH:MM - Fix implemented
- HH:MM - Service restored

Root Cause:
- What caused the issue?
- Was it preventable?

Resolution:
- What was done to fix it?
- Was it temporary or permanent fix?

Post-Incident
- What will we do to prevent this?
- What monitoring needs to be improved?
- Any code changes needed?

Owner: [Name]
Reviewed: [Date/Initials]
```

## Key Commands Quick Reference

```bash
# Status
docker compose -f docker-compose.prod.yml ps
docker stats

# Logs
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs --tail=100 web

# Database
docker compose -f docker-compose.prod.yml exec db psql
docker compose -f docker-compose.prod.yml exec db pg_dump -U $DB_USER $DB_NAME > backup.sql

# Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD

# Celery
docker compose -f docker-compose.prod.yml exec celery_worker celery -A config inspect active

# Restart Services
docker compose -f docker-compose.prod.yml restart web
docker compose -f docker-compose.prod.yml restart celery_worker
docker compose -f docker-compose.prod.yml restart db

# Full restart
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# Backup
bash deploy/backups/backup.sh

# Health check
bash deploy/scripts/health-check.sh yourdomain.com
```

## Useful Dashboards & URLs

- Grafana: https://yourdomain.com/grafana/
- Prometheus: http://localhost:9090
- Application: https://yourdomain.com/
- Admin Panel: https://yourdomain.com/admin-panel/
- Health Check: https://yourdomain.com/health/

## Contact Information

- DevOps Lead: devops-lead@example.com, +1-XXX-XXX-XXXX
- Database Admin: dba@example.com
- Security Team: security@example.com
- Escalation: ops-manager@example.com

## References

- Deployment Guide: docs/DEPLOYMENT_GUIDE.md
- Security Audit: SECURITY_AUDIT.md
- Architecture: docs/architecture.md
- API Documentation: /api/docs/
