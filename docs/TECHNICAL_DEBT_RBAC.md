# Technical Debt Report: RBAC & User Management

**Generated**: 2025-11-20
**Scope**: User management, RBAC, Auth0 integration, Config page
**Status**: 🟡 System functional but needs security hardening

---

## 🔴 CRITICAL (Security Vulnerabilities)

### 1. Backend JWT Verification is Mocked
**File**: `backend/api/internal/admin/users.py:76-95`
**Issue**: `require_superadmin()` dependency always returns mock admin user

```python
# Current (INSECURE):
async def require_superadmin() -> dict:
    # TODO: Implement real JWT verification
    return {
        "user_id": "auth0|mock",
        "email": "admin@aurity.app",
        "roles": ["superadmin"],
    }
```

**Impact**: 🚨 **Anyone can call admin endpoints without authentication**

**Solution**:
```python
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
import os

DOMAIN = os.getenv("AUTH0_DOMAIN")
API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.fi-aurity.duckdns.org")

async def require_superadmin(
    authorization: str = Header(None)
) -> dict:
    """Verify user has SUPERADMIN role via JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]

    try:
        # Verify JWT signature with Auth0 JWKS
        jwks_url = f"https://{DOMAIN}/.well-known/jwks.json"
        # ... (use python-jose to verify)

        # Decode and verify
        payload = jwt.decode(
            token,
            key=...,  # Fetch from JWKS
            audience=API_IDENTIFIER,
            issuer=f"https://{DOMAIN}/"
        )

        # Check roles claim
        roles = payload.get("https://aurity.app/roles", [])
        if "FI-superadmin" not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "roles": roles
        }
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

**Dependencies needed**:
```bash
pip install python-jose[cryptography] cryptography
```

**Priority**: 🔴 **P0 - MUST FIX BEFORE PRODUCTION**

---

### 2. Frontend Token Storage in localStorage (XSS Risk)
**File**: `apps/aurity/components/admin/UserManagement.tsx:53,155,188,429`
**Issue**: Access tokens stored in localStorage are vulnerable to XSS attacks

```typescript
// Current (INSECURE):
'Authorization': `Bearer ${localStorage.getItem('auth0_access_token') || ''}`
```

**Impact**: 🚨 XSS attack can steal admin tokens and impersonate superadmin

**Solution**: Use Auth0 SDK's secure token management
```typescript
import { useAuth0 } from '@auth0/auth0-react';

export function UserManagement({ onClose }: UserManagementProps) {
  const { getAccessTokenSilently } = useAuth0();

  const loadUsers = async () => {
    try {
      // Secure: Token retrieved from memory/httpOnly cookie
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE,
          scope: 'read:users update:users create:users delete:users'
        }
      });

      const response = await fetch(`${backendUrl}/api/internal/admin/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      // ...
    }
  };
}
```

**Benefits**:
- Tokens stored in memory (not accessible to XSS)
- Automatic token refresh
- Auth0 SDK handles token expiration

**Priority**: 🔴 **P0 - MUST FIX BEFORE PRODUCTION**

---

## 🟠 HIGH PRIORITY

### 3. Missing NEXT_PUBLIC_SUPERADMIN_EMAILS Environment Variable
**File**: `apps/aurity/hooks/useRBAC.ts:122`
**Issue**: Environment variable not defined in `.env.local` or `.env.production`

```typescript
const envEmails = process.env.NEXT_PUBLIC_SUPERADMIN_EMAILS;
// Returns undefined → superadmin check fails
```

**Impact**: Frontend superadmin detection won't work

**Solution**: Add to `.env.local` and `.env.production`
```bash
NEXT_PUBLIC_SUPERADMIN_EMAILS=bernarduriza@gmail.com,admin@aurity.app
```

**Priority**: 🟠 **P1 - Required for superadmin detection**

---

### 4. No Token Refresh Logic
**File**: `apps/aurity/components/admin/UserManagement.tsx`
**Issue**: Access tokens expire after 1 hour, no refresh mechanism

**Impact**: After 1 hour, all API calls fail with 401

**Solution**: Auth0 SDK handles this automatically with `getAccessTokenSilently()`
- If using localStorage (current): Need manual refresh logic
- If using Auth0 SDK (recommended): Handled automatically

**Priority**: 🟠 **P1 - Affects UX after 1 hour**

---

### 5. Hardcoded Superadmin Fallback List
**File**: `apps/aurity/hooks/useRBAC.ts:123-130`

```typescript
// Fallback to hardcoded list (TODO: Move to database)
const hardcodedSuperAdmins = [
  'bernarduriza@gmail.com',
  'admin@aurity.app',
];
```

**Issue**: Hardcoded emails in source code

**Solution Options**:
1. **Environment Variable** (quick):
   - Use `NEXT_PUBLIC_SUPERADMIN_EMAILS` exclusively
   - Remove hardcoded fallback

2. **Database** (scalable):
   - Store in PostgreSQL `users` table with `is_superadmin` flag
   - Query via API endpoint

**Priority**: 🟠 **P1 - Security best practice**

---

## 🟡 MEDIUM PRIORITY

### 6. No Audit Logging for Admin Operations
**File**: `backend/api/internal/admin/users.py`
**Issue**: Admin operations logged but not persisted to audit table

**Current**:
```python
logger.info("USER_CREATED_VIA_API", user_id=user_id, admin_email=admin.get("email"))
```

**Impact**: Can't audit trail who created/modified/deleted users

**Solution**: Add audit table integration
```python
from backend.audit.logger import log_audit_event

@router.post("")
async def create_user(request: CreateUserRequest, admin: dict = Depends(require_superadmin)):
    user = service.create_user(...)

    # Persist to audit table
    await log_audit_event(
        action="USER_CREATED",
        user_id=admin["user_id"],
        resource_type="user",
        resource_id=user["user_id"],
        details={"email": user["email"], "roles": request.roles}
    )
```

**Priority**: 🟡 **P2 - Compliance requirement (HIPAA)**

---

### 7. Generic Error Messages
**File**: `apps/aurity/components/admin/UserManagement.tsx:58-75`

```typescript
if (!response.ok) {
  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
}
```

**Issue**: User sees technical error messages instead of friendly explanations

**Solution**: Map HTTP codes to user-friendly messages
```typescript
const ERROR_MESSAGES: Record<number, string> = {
  401: "Tu sesión expiró. Por favor inicia sesión nuevamente.",
  403: "No tienes permisos para realizar esta acción.",
  404: "Usuario no encontrado.",
  500: "Error del servidor. Intenta nuevamente en unos momentos.",
};

if (!response.ok) {
  const message = ERROR_MESSAGES[response.status] || "Error desconocido";
  toast.error(message);
  return;
}
```

**Priority**: 🟡 **P2 - UX improvement**

---

### 8. Mock User Data Still Present
**File**: `apps/aurity/components/admin/UserManagement.tsx:78-119`
**Issue**: 12 mock users defined as fallback

**Impact**: If API fails, UI shows fake data (confusing in production)

**Solution**: Remove mock data, show error state instead
```typescript
} catch (error) {
  console.error('Failed to load users:', error);
  setUsers([]);  // Don't fallback to mock data
  setError("No se pudieron cargar los usuarios. Verifica tu conexión.");
}
```

**Priority**: 🟡 **P2 - Production cleanliness**

---

## 🟢 LOW PRIORITY (Nice to Have)

### 9. No Rate Limiting on Admin Endpoints
**File**: `backend/api/internal/admin/users.py`
**Issue**: No rate limiting for admin operations

**Solution**: Add rate limiting middleware
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("")
@limiter.limit("10/minute")  # Max 10 requests per minute
async def list_users(...):
    ...
```

**Priority**: 🟢 **P3 - Defense in depth**

---

### 10. No Pagination for Large User Lists
**File**: `apps/aurity/components/admin/UserManagement.tsx:51`
**Issue**: Loads all users with `per_page=100` (hard limit)

**Solution**: Implement pagination UI
```typescript
const [page, setPage] = useState(0);
const [totalPages, setTotalPages] = useState(0);

const response = await fetch(
  `${backendUrl}/api/internal/admin/users?page=${page}&per_page=20`
);
```

**Priority**: 🟢 **P3 - Scalability (only needed if >100 users)**

---

## 📊 Summary

| Priority | Count | Must Fix Before Production |
|----------|-------|----------------------------|
| 🔴 P0    | 2     | ✅ YES                     |
| 🟠 P1    | 3     | ⚠️ RECOMMENDED            |
| 🟡 P2    | 4     | ❌ NO                      |
| 🟢 P3    | 2     | ❌ NO                      |

---

## 🎯 Recommended Action Plan

### Phase 1: Security Hardening (P0) - 4 hours
1. Implement JWT verification in `require_superadmin()` (2h)
2. Replace localStorage with Auth0 SDK `getAccessTokenSilently()` (2h)

### Phase 2: Essential Fixes (P1) - 2 hours
1. Add `NEXT_PUBLIC_SUPERADMIN_EMAILS` to env files (15min)
2. Verify token refresh works with Auth0 SDK (30min)
3. Remove hardcoded superadmin list (15min)

### Phase 3: Quality Improvements (P2) - 3 hours
1. Add audit logging integration (1.5h)
2. Improve error messages (1h)
3. Remove mock data fallback (30min)

### Phase 4: Polish (P3) - Optional
- Rate limiting
- Pagination

---

## 🔧 Quick Wins (Can be done now)

1. **Add NEXT_PUBLIC_SUPERADMIN_EMAILS** (2 minutes)
   ```bash
   echo "NEXT_PUBLIC_SUPERADMIN_EMAILS=bernarduriza@gmail.com" >> apps/aurity/.env.local
   ```

2. **Remove hardcoded superadmin list** (2 minutes)
   - Delete lines 123-130 in `useRBAC.ts`
   - Keep only env variable check

3. **Remove mock data** (2 minutes)
   - Delete lines 78-119 in `UserManagement.tsx`
   - Replace with error state

---

**Next Steps**: Which priority level should we tackle first? I recommend starting with P0 (security) immediately.
