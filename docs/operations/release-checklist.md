# Release Checklist

**Purpose**: Pre-deployment checklist to ensure safe releases to production.

**Audience**: Engineers deploying to production, release managers.

**Where this is used**: Before every production deployment.

**Last updated**: 2025-01-XX

---

## Pre-Deployment

### Code Review

- [ ] All changes reviewed and approved
- [ ] Tests passing (unit + integration)
- [ ] No breaking changes to APIs
- [ ] Database migrations tested
- [ ] Configuration changes documented

### Risk Assessment

- [ ] Risk limits unchanged or explicitly approved
- [ ] No changes to kill switch logic
- [ ] Execution engine changes reviewed
- [ ] Wallet service changes reviewed
- [ ] Circuit breaker thresholds verified

### Testing

- [ ] Unit tests: `pytest tests/unit/ -v`
- [ ] Integration tests: `pytest tests/integration/ -v`
- [ ] Manual testing in staging
- [ ] Performance testing completed
- [ ] Load testing (if applicable)

### Documentation

- [ ] README updated (if needed)
- [ ] API changes documented
- [ ] Configuration changes documented
- [ ] Migration guide (if breaking changes)

---

## Deployment

### Database

- [ ] Backup database before migration
- [ ] Run migrations: `alembic upgrade head`
- [ ] Verify migration success
- [ ] Check for data integrity issues

### Configuration

- [ ] Environment variables verified
- [ ] Secrets updated (if needed)
- [ ] API keys valid
- [ ] Database connection tested

### Deployment Steps

1. [ ] Deploy backend
2. [ ] Verify backend health: `GET /api/health`
3. [ ] Deploy frontend (if changed)
4. [ ] Verify frontend accessible
5. [ ] Check system status: `GET /api/status`

---

## Post-Deployment

### Verification

- [ ] System status: GREEN
- [ ] All services running
- [ ] Metrics collection working
- [ ] Logging working
- [ ] No errors in logs

### Monitoring

- [ ] Watch metrics for 15 minutes
- [ ] Check latency metrics
- [ ] Verify order execution (if applicable)
- [ ] Monitor error rates
- [ ] Check exposure levels

### Rollback Plan

- [ ] Rollback procedure documented
- [ ] Previous version tagged
- [ ] Database rollback script ready
- [ ] Rollback tested in staging

---

## Emergency Rollback

If issues detected:

1. [ ] Pause trading immediately
2. [ ] Execute rollback procedure
3. [ ] Verify system stability
4. [ ] Document issues
5. [ ] Notify team

---

## Open Questions

- What is the exact rollback procedure?
- How long should we monitor after deployment?
- What metrics indicate a successful deployment?
- Who approves production deployments?




