---
applyTo: "backend/**/*.py,apps/**/*.ts,apps/**/*.tsx"
excludeAgent: []
---

# Security & HIPAA Compliance - AURITY

## CRITICAL: NO PHI/PII in Logs

Protected Health Information (PHI) and Personally Identifiable Information (PII) MUST NEVER appear in logs.

### FORBIDDEN in Logs

```python
# ❌ VIOLATION - PHI/PII exposure
logger.info("patient_created", nombre=patient.nombre)  # PHI
logger.info("user_login", email=user.email)  # PII
logger.error("auth_failed", curp=patient.curp)  # PHI
logger.debug("call_data", phone=patient.telefono)  # PII
```

### CORRECT: Log Only IDs

```python
import structlog

logger = structlog.get_logger(__name__)

# ✅ CORRECT - Only identifiers
logger.info("patient_created", patient_id=patient.patient_id)
logger.info("user_authenticated", user_id=user.id)
logger.info("session_started", session_id=session.id, provider_id=provider.id)
logger.error("operation_failed", resource_id=resource.id, error_code="E001")
```

### PHI/PII Data Types to NEVER Log

- ❌ `nombre` (name)
- ❌ `apellido` (surname)
- ❌ `email`
- ❌ `curp` (Mexican national ID)
- ❌ `telefono` / `phone`
- ❌ `direccion` (address)
- ❌ `fecha_nacimiento` (date of birth)
- ❌ Medical data (diagnoses, prescriptions, notes)
- ❌ Audio transcripts containing patient speech

## Authentication - Self-Hosted JWT

### Dependency Injection Pattern

```python
from fastapi import Depends, HTTPException, status
from backend.auth.jwt import get_current_user, require_superadmin

# Public endpoint - requires authentication
@router.get("/api/workflows/aurity/sessions")
async def list_sessions(
    user: User = Depends(get_current_user)
):
    logger.info("sessions_listed", user_id=user.id)
    return await session_service.list_for_user(user.id)

# Admin endpoint - requires SUPERADMIN role
@router.delete("/internal/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: dict = Depends(require_superadmin)
):
    logger.info("user_deleted", target_user_id=user_id, admin_id=admin["sub"])
    return await user_service.delete(user_id)
```

### Role-Based Access Control (RBAC)

```python
from backend.auth.jwt import get_user_roles

@router.post("/api/workflows/aurity/sessions/{session_id}/finalize")
async def finalize_session(
    session_id: str,
    user: User = Depends(get_current_user)
):
    # Check if user owns the session
    session = await session_service.get(session_id)

    if session.user_id != user.id:
        # Check if user has admin role
        roles = user.roles

        if "FI-superadmin" not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to finalize this session"
            )

    logger.info("session_finalized", session_id=session_id, user_id=user.id)
    return await session_service.finalize(session_id)
```

## Environment Variables - Zero Hardcoding

### Python Backend

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

# ✅ CORRECT - Environment variables
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate at startup
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable not set")

# ❌ FORBIDDEN - Hardcoded secrets
DEEPGRAM_API_KEY = "a1b2c3d4..."  # SECURITY VIOLATION
API_TOKEN = "eyJhbGc..."  # SECURITY VIOLATION
```

### TypeScript Frontend

```typescript
// ✅ CORRECT - Public env vars only (prefixed with NEXT_PUBLIC_)
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
const API_URL = process.env.NEXT_PUBLIC_API_URL || BACKEND_URL;

// ❌ FORBIDDEN - Secrets in frontend
const API_KEY = "sk-abc123...";  // NEVER in client-side code
```

## CORS Configuration

```python
# backend/app/main.py

environment = os.getenv("ENVIRONMENT", "development")

if environment == "production":
    # Production - strict whitelist
    allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
    if not allowed_origins_str:
        raise ValueError("ALLOWED_ORIGINS must be set in production")

    allowed_origins = [
        origin.strip()
        for origin in allowed_origins_str.split(",")
        if origin.strip()
    ]
else:
    # Development - localhost only
    allowed_origins = [
        "http://localhost:9000",
        "http://localhost:9050",
        "http://127.0.0.1:9000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

## SQL Injection Prevention

```python
from sqlalchemy.orm import Session
from sqlalchemy import select

# ✅ CORRECT - Parameterized queries
def get_patient_by_curp(db: Session, curp: str):
    stmt = select(Patient).where(Patient.curp == curp)
    return db.execute(stmt).scalar_one_or_none()

# ❌ FORBIDDEN - String concatenation
def get_patient_by_curp(db: Session, curp: str):
    query = f"SELECT * FROM patients WHERE curp = '{curp}'"  # SQL INJECTION RISK
    return db.execute(query)
```

## Input Validation

```python
from pydantic import BaseModel, Field, validator

class CreatePatientRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    curp: str = Field(..., regex=r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$")

    @validator("curp")
    def validate_curp(cls, v):
        # Additional CURP validation logic
        if not is_valid_curp(v):
            raise ValueError("Invalid CURP format")
        return v.upper()
```

## Audit Logging

```python
from backend.services.audit_service import AuditService

# Log all sensitive operations
audit_service = AuditService(audit_repository)

# Create audit trail
audit_id = audit_service.log_action(
    action="patient_record_accessed",
    user_id=user.id,
    resource=f"patient:{patient_id}",
    result="success",
    details={
        "operation": "read",
        "timestamp": datetime.now(UTC).isoformat()
    }
)
```

## HTTPS Only in Production

```python
# Redirect HTTP to HTTPS in production
if environment == "production":
    @app.middleware("http")
    async def redirect_to_https(request, call_next):
        if request.url.scheme != "https":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url, status_code=301)
        return await call_next(request)
```

## Session Security

```python
from datetime import timedelta

# JWT token settings
JWT_EXPIRATION = timedelta(hours=8)  # Force re-authentication
JWT_ALGORITHM = "RS256"  # Asymmetric encryption

# Session timeout
SESSION_TIMEOUT = timedelta(minutes=30)
```

## CORS Configuration

### Production Whitelist
```python
# backend/app/main.py

import os
from fastapi.middleware.cors import CORSMiddleware

environment = os.getenv("ENVIRONMENT", "development")

if environment == "production":
    # CRITICAL: Strict whitelist for production
    allowed_origins = [
        "https://app.aurity.io",
        "https://fi-aurity.duckdns.org",  # Legacy (deprecated)
    ]
else:
    # Development: localhost only
    allowed_origins = [
        "http://localhost:9000",
        "http://localhost:9050",
        "http://127.0.0.1:9000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

## Production SSH Policy (MACHINE-ENFORCED)

### CRITICAL: Read-Only Production Access

This policy is **MACHINE-ENFORCED** via:
- `.git/hooks/pre-receive-prod` (blocks direct git push)
- `.git/hooks/prod-integrity-check.sh` (cron every 5min)
- `.github/workflows/deploy-production.yml` (pre-deploy integrity check)

### ✅ ALLOWED on Production Server
```bash
# Read-only audit operations
tail -f /tmp/backend.log
journalctl -u aurity-backend -f
ps aux | grep uvicorn
top
htop
lsof -i :7001
curl http://localhost:7001/api/health

# File inspection (read-only)
cat /opt/free-intelligence/backend/app/main.py
less /var/log/nginx/access.log
head -n 100 /tmp/backend.log
```

### ❌ FORBIDDEN on Production Server
```bash
# File modification (ANY method)
vim backend/app/main.py           # Text editors
nano .env                         # Any editor
echo "fix" > file.py              # Redirects
sed -i 's/old/new/' file.py       # In-place edits

# Git operations
git commit -m "hotfix"            # Blocked by pre-receive hook
git push origin prod              # Blocked

# Package/service management
pip install new-package           # Use CI/CD
systemctl restart aurity-backend  # Use CI/CD rollback

# Debug modifications
Adding print() statements         # NEVER
Temporary logging changes         # NEVER
"Quick fixes" of any kind         # NEVER
```

### Violation Response
1. Integrity monitor detects change within **5 minutes**
2. Alert sent to Slack + logged to `/var/log/aurity-security.log`
3. Next CI/CD deploy auto-resets production to clean state
4. Repeat violations = **revoked SSH access**

### CORRECT: Deploy via CI/CD Only
```bash
# Local development
git checkout -b hotfix/fix-critical-bug
# Make changes locally
git commit -m "fix: critical bug"
git push origin hotfix/fix-critical-bug

# Merge to prod via GitHub PR
# OR immediate deploy:
make ci-deploy  # Triggers CI/CD pipeline
```

## Secret Management Policy (ZERO TOLERANCE)

### Pattern Detection - NEVER Commit These

```python
# ❌ FORBIDDEN - Will be detected and blocked
API_KEY = "sk-abc123..."                    # Hardcoded API key
DEEPGRAM_API_KEY = "a1b2c3d4e5f6..."        # Service credentials
Bearer_token = "eyJhbGciOiJSUzI1NiIs..."    # JWT tokens
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/..."   # Cloud credentials

# ❌ FORBIDDEN - In documentation/comments
# Example: curl -H "Authorization: Bearer sk-real-key-here"
README.md: "Use API key: a1b2c3d4e5f6..."
```

### Credential Patterns to Detect
- `sk-[a-zA-Z0-9]{20,}` (OpenAI-style keys)
- `api_[a-zA-Z0-9]{20,}` (Generic API keys)
- `Bearer [a-zA-Z0-9]{40,}` (JWT tokens)
- `AZURE_API_KEY`, `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`
- Any 32+ character hex/base64 string in quotes
- Connection strings with passwords: `postgres://user:password@...`

### ✅ CORRECT: Environment Variables Only
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

# ✅ CORRECT
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate at startup
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable not set")
```

### Example Files - Use Placeholders
```bash
# .env.example (committed to git)
DEEPGRAM_API_KEY=<YOUR_DEEPGRAM_API_KEY_HERE>
CLAUDE_API_KEY=<YOUR_CLAUDE_API_KEY_HERE>
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# .env (gitignored, real values)
DEEPGRAM_API_KEY=a1b2c3d4e5f6g7h8i9j0
CLAUDE_API_KEY=sk-ant-api03-real-key-here
DATABASE_URL=postgresql://aurity:secret@localhost:5432/aurity_prod
```

### Recovery Procedure (If Secret Leaked)

```bash
# 1. IMMEDIATELY rotate the exposed credential
# - Go to service provider (Azure, AWS, Deepgram, etc.)
# - Revoke/regenerate the exposed key

# 2. Remove from git history
git filter-repo --invert-paths --path path/to/file-with-secret.py --force

# 3. Force push to all branches
git push --force --all
git push --force --tags

# 4. Notify team and affected services
# - Post incident report
# - Review access logs for unauthorized usage
# - Update monitoring alerts

# 5. Install git-secrets to prevent future leaks
brew install git-secrets
git secrets --install
git secrets --register-aws
```

### Documentation Examples - NEVER Real Keys
```markdown
# ❌ WRONG
## API Usage
```bash
curl -H "Authorization: Bearer sk-ant-api03-real-key" \
  https://api.anthropic.com/v1/messages
```

# ✅ CORRECT
## API Usage
```bash
curl -H "Authorization: Bearer $CLAUDE_API_KEY" \
  https://api.anthropic.com/v1/messages
```

Make sure to set your API key:
```bash
export CLAUDE_API_KEY=<YOUR_API_KEY_HERE>
```
```

## Anti-Patterns

1. ❌ Logging PHI/PII (email, nombre, curp, phone)
2. ❌ Hardcoded API keys or secrets
3. ❌ Missing authentication checks
4. ❌ String concatenation in SQL queries
5. ❌ Exposing stack traces to users
6. ❌ Missing input validation
7. ❌ HTTP in production
8. ❌ Weak CORS configuration
9. ❌ SSH editing files on production
10. ❌ Committing .env files with real credentials
11. ❌ Using real API keys in documentation
12. ❌ "Quick fixes" on production server

## Success Checklist

- [ ] No PHI/PII in logs (only IDs)
- [ ] All secrets from environment variables
- [ ] Authentication on all protected routes
- [ ] RBAC for admin operations
- [ ] Parameterized SQL queries
- [ ] Input validation with Pydantic
- [ ] Audit logs for sensitive operations
- [ ] HTTPS enforced in production
- [ ] CORS whitelist configured
- [ ] Error messages don't expose internals
- [ ] .env.example with placeholders (not real keys)
- [ ] No SSH file editing on production
- [ ] Deploy only via CI/CD (make ci-deploy)
