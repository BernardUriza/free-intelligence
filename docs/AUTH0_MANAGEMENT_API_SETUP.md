# Auth0 Management API Setup Guide

Complete guide to configure Auth0 Management API for AURITY user administration.

**Last Updated**: 2025-11-20
**Owner**: Bernard Uriza

---

## Prerequisites

- Auth0 account with admin access
- Auth0 tenant (e.g., `dev-xyz.us.auth0.com`)
- Node.js 18+ (for Auth0 CLI - optional)

---

## Step 1: Create Machine-to-Machine Application

The Management API requires a dedicated M2M application for authentication.

### Via Auth0 Dashboard

1. **Navigate to Applications**
   ```
   Auth0 Dashboard → Applications → Applications
   ```

2. **Create Application**
   - Click "Create Application"
   - Name: `AURITY Management API`
   - Type: **Machine to Machine Applications**
   - Click "Create"

3. **Select API**
   - Authorize for: **Auth0 Management API**
   - Click "Authorize"

4. **Configure Scopes** (Grant Permissions)

   **User Management Scopes:**
   - ✅ `read:users` - Read user data
   - ✅ `create:users` - Create new users
   - ✅ `update:users` - Update user attributes
   - ✅ `delete:users` - Delete users
   - ✅ `read:users_app_metadata` - Read user metadata
   - ✅ `update:users_app_metadata` - Update user metadata

   **Role Management Scopes:**
   - ✅ `read:roles` - List available roles
   - ✅ `create:roles` - Create roles (optional)
   - ✅ `update:roles` - Update roles (optional)
   - ✅ `delete:roles` - Delete roles (optional)
   - ✅ `read:role_members` - Get users in role
   - ✅ `create:role_members` - Assign roles to users
   - ✅ `delete:role_members` - Remove roles from users

   **Email Scopes:**
   - ✅ `create:user_tickets` - Send verification emails

5. **Save Credentials**
   - Go to "Settings" tab
   - Copy **Client ID**
   - Copy **Client Secret**
   - **⚠️ IMPORTANT**: Store securely, never commit to git

---

## Step 2: Configure Environment Variables

Add the following to your `.env` file:

```bash
# Auth0 Management API (M2M Application)
AUTH0_DOMAIN=dev-xyz.us.auth0.com
AUTH0_MANAGEMENT_CLIENT_ID=your_m2m_client_id_here
AUTH0_MANAGEMENT_CLIENT_SECRET=your_m2m_client_secret_here

# Auth0 Application (Frontend - already configured)
AUTH0_CLIENT_ID=your_spa_client_id
AUTH0_CLIENT_SECRET=your_spa_client_secret
```

**Security Checklist:**
- ✅ Added `.env` to `.gitignore`
- ✅ Used different credentials for M2M vs SPA
- ✅ Stored secrets in secure vault (production)

---

## Step 3: Install Required Dependencies

### Backend (Python)

```bash
pip install auth0-python structlog
```

Or add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "auth0-python>=4.4.0",
    "structlog>=24.1.0",
]
```

---

## Step 4: Verify Configuration

### Test Auth0 Management Service

```bash
# From project root
python3 -c "
from backend.services.auth0_management import get_auth0_service

service = get_auth0_service()
print('✅ Auth0 Management Service initialized')

# List users (test connection)
response = service.list_users(per_page=5)
print(f'✅ Found {response.get(\"total\", 0)} users')
print('✅ Configuration successful!')
"
```

Expected output:
```
✅ Auth0 Management Service initialized
✅ Found 3 users
✅ Configuration successful!
```

### Test API Endpoints

```bash
# Start backend
make run

# Test list users endpoint (requires superadmin token)
curl -X GET "http://localhost:7001/api/internal/admin/users?per_page=10" \
  -H "Authorization: Bearer <your_jwt_token>"
```

---

## Step 5: Create Roles in Auth0

### Via Auth0 Dashboard

1. **Navigate to Roles**
   ```
   Auth0 Dashboard → User Management → Roles
   ```

2. **Create Roles** (one by one)

   | Role Name | Description |
   |-----------|-------------|
   | `superadmin` | Full system access (AURITY superusers) |
   | `admin` | Administrative operations |
   | `doctor` | Clinical operations |
   | `nurse` | Clinical assistance |
   | `staff` | Administrative staff |
   | `viewer` | Read-only access |

3. **Assign Permissions** (optional)
   - Roles can have permissions for APIs
   - For now, roles are checked client-side via JWT

### Via Auth0 CLI (Optional)

```bash
# Install Auth0 CLI
npm install -g auth0-cli

# Login
auth0 login

# Create roles programmatically
for role in superadmin admin doctor nurse staff viewer; do
  auth0 api post /roles --data "{\"name\":\"$role\",\"description\":\"AURITY $role role\"}"
done
```

---

## Step 6: Configure JWT Custom Claims

To include roles in JWT tokens, configure an Auth0 Action:

1. **Create Action**
   ```
   Auth0 Dashboard → Actions → Flows → Login → Custom
   ```

2. **Add Custom Action**
   - Click "+ Add Action" → "Build Custom"
   - Name: `Add Roles to Token`
   - Trigger: **Login / Post Login**

3. **Action Code**

   ```javascript
   exports.onExecutePostLogin = async (event, api) => {
     const namespace = 'https://aurity.app';

     if (event.authorization) {
       // Add roles to ID token (frontend)
       api.idToken.setCustomClaim(
         `${namespace}/roles`,
         event.authorization.roles
       );

       // Add roles to access token (backend)
       api.accessToken.setCustomClaim(
         `${namespace}/roles`,
         event.authorization.roles
       );
     }
   };
   ```

4. **Deploy Action**
   - Click "Deploy"
   - Drag action to "Login" flow
   - Click "Apply"

5. **Verify**
   - Login as a user with roles
   - Decode JWT at [jwt.io](https://jwt.io)
   - Confirm `https://aurity.app/roles` claim exists

---

## Step 7: Assign Roles to Users

### Via Auth0 Dashboard

1. **Navigate to Users**
   ```
   Auth0 Dashboard → User Management → Users
   ```

2. **Select User**
   - Click on user email

3. **Assign Roles**
   - Go to "Roles" tab
   - Click "Assign Roles"
   - Select role(s)
   - Click "Assign"

### Via AURITY Admin UI

1. **Login as Superadmin**
   - Navigate to `/config`
   - Click "Gestionar Usuarios"

2. **Toggle Roles**
   - Click on user
   - Click role badges to toggle on/off
   - Changes save automatically

---

## Step 8: Register Routes in Backend

Add admin router to `backend/app/main.py`:

```python
from backend.api.internal.admin import users_router

# Register admin routes
app.include_router(
    users_router,
    prefix="/api/internal",
    tags=["admin"]
)
```

---

## Troubleshooting

### Error: "Insufficient scope"

**Cause**: M2M application missing required scopes

**Fix**:
1. Go to Auth0 Dashboard → Applications
2. Select "AURITY Management API"
3. Go to "APIs" tab
4. Click "Auth0 Management API"
5. Grant all required scopes
6. Clear cached tokens:
   ```python
   from backend.services.auth0_management import get_auth0_service
   service = get_auth0_service()
   service._token = None  # Force token refresh
   ```

### Error: "Invalid credentials"

**Cause**: Incorrect Client ID or Secret

**Fix**:
1. Verify `.env` file has correct credentials
2. Check no extra whitespace in values
3. Restart backend to reload environment

### Error: "Rate limit exceeded"

**Cause**: Too many Management API calls

**Fix**:
- Token caching is implemented (55-min cache)
- Reduce polling frequency
- Check Auth0 tenant rate limits:
  ```
  Dashboard → Monitoring → Rate Limits
  ```

---

## Security Best Practices

1. **Principle of Least Privilege**
   - Only grant scopes actually needed
   - Regularly audit M2M application scopes

2. **Rotate Credentials**
   - Rotate Client Secret every 90 days
   - Use different credentials per environment (dev/staging/prod)

3. **Token Security**
   - Never log access tokens
   - Never expose tokens to frontend
   - Tokens auto-expire after 1 hour

4. **Audit Trail**
   - All admin operations logged in backend
   - Review logs regularly: `backend/api/internal/admin/users.py`

5. **RBAC Enforcement**
   - Always verify superadmin role in endpoints
   - Implement JWT verification (TODO in `require_superadmin`)

---

## References

- [Auth0 Management API Documentation](https://auth0.com/docs/api/management/v2)
- [Auth0 Python SDK](https://auth0-python.readthedocs.io/)
- [Auth0 RBAC Guide](https://auth0.com/docs/manage-users/access-control/rbac)
- [Auth0 Actions](https://auth0.com/docs/customize/actions)

---

## Next Steps

1. ✅ Configure M2M application
2. ✅ Set environment variables
3. ✅ Test Management API connection
4. ✅ Create roles in Auth0
5. ✅ Configure JWT custom claims
6. ⏳ Implement JWT verification in `require_superadmin`
7. ⏳ Deploy to production
8. ⏳ Setup monitoring and alerts

---

**Questions?** Contact: bernarduriza@gmail.com
