# FI Auth

Centralized authentication and RBAC package for AURITY services following Clean Architecture. The package exposes FastAPI dependencies and a lightweight Auth0 provider to validate JWTs, build user context, and enforce role/permission checks.

## Usage

```python
from backend.packages.fi_auth import auth_router, get_current_user, require_roles, UserRole
from fastapi import FastAPI, Depends

app = FastAPI()
app.include_router(auth_router, prefix="/api")

@app.get("/api/protected")
async def protected(user = Depends(get_current_user)):
    return {"user_id": user.user_id}

@app.get("/api/admin")
async def admin_only(user = Depends(require_roles([UserRole.SUPERADMIN]))):
    return {"user_id": user.user_id}
```

## Tests

```
pytest backend/packages/fi_auth/tests -v
```
