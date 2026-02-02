# Secrets Handling

**Purpose**: Procedures for managing secrets, API keys, and sensitive credentials.

**Audience**: Engineers, system administrators, security team.

**Where this is used**: System setup, key rotation, security audits.

**Last updated**: 2025-01-XX

---

## Secrets Overview

### Types of Secrets

1. **Private Keys**: Wallet private keys
2. **API Keys**: Polymarket API credentials
3. **Database Credentials**: Database connection strings
4. **OAuth Secrets**: Stack Auth secrets
5. **Encryption Keys**: Wallet encryption keys

---

## Storage

### Development

- `.env` files (never committed)
- Local environment variables
- Secure local storage

### Production

- **Recommended**: Secret management service
  - AWS Secrets Manager
  - HashiCorp Vault
  - Azure Key Vault
  - Google Secret Manager
- **Alternative**: Encrypted environment variables
- **Never**: Hardcoded in code or committed to git

---

## Wallet Private Keys

### Storage

- Encrypted in database (if using DB storage)
- Environment variable `PRIVATE_KEY` (recommended for production)
- Never in plain text
- Never in logs

### Encryption

- Fernet symmetric encryption
- Key stored separately from data
- Key rotation supported

### Access

- Only accessible to Execution Engine
- Never exposed to frontend
- Never in API responses
- Logged only as masked values

---

## API Keys

### Polymarket API

- Generated automatically from `PRIVATE_KEY` and `FUNDER_ADDRESS`
- Can be pre-generated and stored
- Rotated as needed

### External APIs

- Stored in `secrets` table
- Encrypted at rest
- Access controlled by role

---

## Key Rotation

### Procedure

1. Generate new key
2. Update configuration
3. Test with new key
4. Deploy update
5. Verify functionality
6. Revoke old key (if applicable)

### Wallet Rotation

```python
# Rotate wallet in runtime
wallet_service.rotate_wallet(new_wallet_id)
```

---

## Best Practices

1. **Never commit secrets** to version control
2. **Use secret management** in production
3. **Rotate keys regularly**
4. **Monitor access** to secrets
5. **Log secret access** (without values)
6. **Use least privilege** principle

---

## Emergency Procedures

### Compromised Key

1. Immediately rotate key
2. Revoke old key
3. Review access logs
4. Assess impact
5. Notify team

### Key Loss

1. Verify key is truly lost
2. Generate new key
3. Update all systems
4. Test thoroughly
5. Document incident

---

## Open Questions

- What is the key rotation schedule?
- How are keys backed up securely?
- What is the procedure for key recovery?
- How do we handle key compromise?




