# Alphha DMS - Disaster Recovery Runbook

## 1. Overview

This document outlines disaster recovery procedures for Alphha DMS, including backup strategies, recovery procedures, and RTO/RPO targets.

### Recovery Objectives

| Metric | Target | Description |
|--------|--------|-------------|
| RTO (Recovery Time Objective) | 4 hours | Maximum acceptable downtime |
| RPO (Recovery Point Objective) | 1 hour | Maximum acceptable data loss |

---

## 2. Backup Strategy

### 2.1 Database Backups

**PostgreSQL (Production) / SQLite (Development)**

```bash
# Automated daily backup (add to crontab)
0 2 * * * /opt/alphha-dms/scripts/backup-db.sh

# Manual backup
pg_dump -h localhost -U alphha alphha_dms > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite backup
sqlite3 /app/data/alphha.db ".backup '/backups/alphha_$(date +%Y%m%d).db'"
```

**Backup Retention:**
- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months

### 2.2 Document Storage Backups

```bash
# S3 cross-region replication (recommended)
aws s3 sync s3://alphha-dms-primary s3://alphha-dms-dr --region us-west-2

# Local backup
rsync -avz /app/uploads/ /backups/uploads/
```

### 2.3 Configuration Backups

```bash
# Backup environment and configs
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  .env \
  docker-compose.yml \
  backend/alembic/ \
  nginx/
```

---

## 3. Disaster Scenarios & Recovery Procedures

### 3.1 Database Corruption

**Symptoms:**
- Application errors mentioning database integrity
- Queries returning unexpected results
- SQLAlchemy errors in logs

**Recovery Steps:**

1. **Stop the application**
   ```bash
   docker-compose down
   ```

2. **Identify last good backup**
   ```bash
   ls -la /backups/db/
   ```

3. **Restore database**
   ```bash
   # PostgreSQL
   psql -h localhost -U alphha alphha_dms < backup_YYYYMMDD.sql
   
   # SQLite
   cp /backups/alphha_YYYYMMDD.db /app/data/alphha.db
   ```

4. **Verify integrity**
   ```bash
   # PostgreSQL
   psql -c "SELECT count(*) FROM documents;"
   
   # SQLite
   sqlite3 /app/data/alphha.db "PRAGMA integrity_check;"
   ```

5. **Restart application**
   ```bash
   docker-compose up -d
   ```

6. **Verify functionality**
   ```bash
   curl http://localhost:7001/api/v1/monitoring/health
   ```

### 3.2 Storage Failure

**Symptoms:**
- Document downloads failing
- Upload errors
- "File not found" errors

**Recovery Steps:**

1. **Check storage health**
   ```bash
   df -h /app/uploads
   aws s3 ls s3://alphha-dms-primary/
   ```

2. **Restore from backup**
   ```bash
   # From S3 DR bucket
   aws s3 sync s3://alphha-dms-dr s3://alphha-dms-primary
   
   # From local backup
   rsync -avz /backups/uploads/ /app/uploads/
   ```

3. **Verify document checksums**
   ```bash
   python -c "
   from app.core.database import SessionLocal
   from app.models import Document
   import hashlib
   
   db = SessionLocal()
   docs = db.query(Document).limit(100).all()
   for doc in docs:
       with open(doc.file_path, 'rb') as f:
           actual = hashlib.sha256(f.read()).hexdigest()
       if actual != doc.checksum_sha256:
           print(f'MISMATCH: {doc.id}')
   "
   ```

### 3.3 Complete System Failure

**Recovery Steps:**

1. **Provision new infrastructure**
   ```bash
   # Using Terraform (if available)
   cd infrastructure/
   terraform apply -var="environment=dr"
   ```

2. **Deploy application**
   ```bash
   git clone https://github.com/org/alphha-dms.git
   cd alphha-dms
   cp /backups/config/.env .
   docker-compose up -d --build
   ```

3. **Restore database**
   ```bash
   docker-compose exec backend python -c "
   from app.core.database import engine, Base
   Base.metadata.create_all(bind=engine)
   "
   
   # Restore data
   cat /backups/db/latest.sql | docker-compose exec -T db psql -U alphha
   ```

4. **Restore documents**
   ```bash
   aws s3 sync s3://alphha-dms-dr ./uploads/
   ```

5. **Update DNS**
   ```bash
   # Update Route53 or DNS provider to point to new infrastructure
   ```

6. **Verify all services**
   ```bash
   ./scripts/health-check.sh
   ```

### 3.4 Security Breach

**Immediate Actions:**

1. **Isolate affected systems**
   ```bash
   # Block all external access
   docker-compose down
   
   # Or use firewall
   ufw deny from any to any port 7000
   ufw deny from any to any port 7001
   ```

2. **Preserve evidence**
   ```bash
   # Snapshot current state
   docker-compose logs > incident_logs_$(date +%Y%m%d_%H%M%S).txt
   cp -r /app/data /evidence/
   ```

3. **Rotate all credentials**
   ```bash
   # Generate new secrets
   openssl rand -base64 32 > new_secret_key
   openssl rand -base64 32 > new_encryption_key
   
   # Update .env
   # Restart with new credentials
   ```

4. **Review audit logs**
   ```bash
   # Export audit trail
   sqlite3 /app/data/alphha.db "SELECT * FROM audit_ledger WHERE created_at > datetime('now', '-24 hours');" > audit_review.csv
   ```

5. **Notify stakeholders**
   - Security team
   - Legal/Compliance
   - Affected tenants (if applicable)

---

## 4. Backup Verification

### 4.1 Weekly Backup Test

```bash
#!/bin/bash
# backup-test.sh - Run weekly

# Create test environment
docker-compose -f docker-compose.test.yml up -d

# Restore latest backup
cat /backups/db/latest.sql | docker-compose -f docker-compose.test.yml exec -T db psql -U alphha

# Run verification
docker-compose -f docker-compose.test.yml exec backend python -c "
from app.core.database import SessionLocal
from app.models import Document, User, Tenant

db = SessionLocal()
print(f'Documents: {db.query(Document).count()}')
print(f'Users: {db.query(User).count()}')
print(f'Tenants: {db.query(Tenant).count()}')
"

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

### 4.2 Monthly DR Drill

1. Simulate complete failure
2. Execute full recovery procedure
3. Measure actual RTO
4. Document findings and improvements

---

## 5. Monitoring & Alerts

### 5.1 Health Check Endpoints

```bash
# Application health
curl http://localhost:7001/api/v1/monitoring/health

# Database connectivity
curl http://localhost:7001/api/v1/monitoring/health | jq '.components.database'

# Metrics
curl http://localhost:7001/api/v1/monitoring/prometheus
```

### 5.2 Alert Configuration

**Critical Alerts (PagerDuty/OpsGenie):**
- Database connection failures
- Storage > 90% capacity
- API error rate > 5%
- Backup job failures

**Warning Alerts (Slack/Email):**
- High latency (P95 > 2s)
- Failed login spikes
- Retention policy violations

---

## 6. Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | oncall@company.com | PagerDuty |
| Database Admin | dba@company.com | +1-xxx-xxx-xxxx |
| Security Team | security@company.com | Immediate |
| Management | cto@company.com | 30 min escalation |

---

## 7. Recovery Checklist

### Pre-Recovery
- [ ] Identify incident scope
- [ ] Notify stakeholders
- [ ] Preserve evidence (if security incident)
- [ ] Identify recovery point (which backup)

### During Recovery
- [ ] Stop affected services
- [ ] Restore database
- [ ] Restore document storage
- [ ] Restore configuration
- [ ] Run database migrations
- [ ] Verify data integrity

### Post-Recovery
- [ ] Verify all services operational
- [ ] Run smoke tests
- [ ] Check audit log integrity
- [ ] Monitor for issues (1 hour)
- [ ] Document incident
- [ ] Conduct post-mortem

---

## 8. Appendix

### A. Useful Commands

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend

# Database shell
docker-compose exec backend python -c "from app.core.database import SessionLocal; db = SessionLocal(); print('Connected')"

# Force restart
docker-compose down && docker-compose up -d --build

# Check disk usage
du -sh /app/uploads/*
```

### B. File Locations

| Item | Location |
|------|----------|
| Application | /opt/alphha-dms |
| Database | /app/data/alphha.db |
| Documents | /app/uploads |
| Backups | /backups |
| Logs | /var/log/alphha-dms |
| Config | /opt/alphha-dms/.env |

---

*Last Updated: January 2026*
*Version: 1.0*
