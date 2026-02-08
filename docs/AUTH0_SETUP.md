# Auth0 Setup Guide - AURITY Medical AI
**HIPAA Card:** G-003 - Auth0 OAuth2/OIDC Integration
**Created:** 2025-11-17
**Author:** Bernard Uriza Orozco

## 🎯 Overview

This guide walks you through setting up Auth0 authentication for AURITY Medical AI, replacing the custom JWT implementation with production-grade OAuth2/OIDC.

**Benefits:**
- ✅ **HIPAA Compliance** - BAA available on Enterprise plan
- ✅ **MFA Out-of-the-box** - SMS, Authenticator, biometrics
- ✅ **Professional Audit Logs** - 90 days retention
- ✅ **Less Code to Maintain** - Auth0 handles tokens, refresh, sessions
- ✅ **SSO Ready** - One login for multiple apps

---

## 📋 Prerequisites

- [ ] Auth0 account (free Developer plan works for MVP)
- [ ] Domain: `dev-1r4daup7ofj7q6gn.auth0.com`
- [ ] Client ID: `rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp`
- [ ] Production URL: `https://app.aurity.io`

---

## 🚀 Step 1: Create API in Auth0

Auth0 APIs represent your backend and define the "audience" for JWT tokens.

### 1.1 Navigate to APIs
```
Auth0 Dashboard → Applications → APIs → Create API
```

### 1.2 Configure API
```
Name: AURITY Medical AI API
Identifier: https://api.aurity.io
Signing Algorithm: RS256
```

**Important:** The identifier can be any URL (doesn't need to resolve), but it must match `AUTH0_API_IDENTIFIER` in your `.env`.

### 1.3 Enable RBAC
```
Settings → RBAC Settings:
  ☑ Enable RBAC
  ☑ Add Permissions in the Access Token
```

---

## 🔧 Step 2: Configure Application

Your frontend app needs Auth0 credentials to initiate login.

### 2.1 Navigate to Application
```
Auth0 Dashboard → Applications → Applications → (Select your app)
```

### 2.2 Update Settings

**Application Type:** Single Page Application

**Allowed Callback URLs:**
```
https://app.aurity.io/callback
http://localhost:9000/callback
```

**Allowed Logout URLs:**
```
https://app.aurity.io
http://localhost:9000
```

**Allowed Web Origins:**
```
https://app.aurity.io
http://localhost:9000
```

**Allowed Origins (CORS):**
```
https://app.aurity.io
http://localhost:9000
```

**JWT Signature Algorithm:** RS256

### 2.3 Save Changes
Click **Save Changes** at the bottom.

---

## 👥 Step 3: Create Roles (RBAC)

AURITY uses 3 roles for medical access control.

### 3.1 Navigate to Roles
```
Auth0 Dashboard → User Management → Roles → Create Role
```

### 3.2 Create Roles

**Role 1: MEDICO** (Doctor - Read/Write SOAP)
```
Name: MEDICO
Description: Doctor with read/write access to SOAP notes
```

**Role 2: ENFERMERA** (Nurse - Read-Only)
```
Name: ENFERMERA
Description: Nurse with read-only access to medical records
```

**Role 3: ADMIN** (Admin - Full Access)
```
Name: ADMIN
Description: System administrator with full access
```

---

## ⚙️ Step 4: Add Roles to JWT Token (Custom Claims)

Auth0 doesn't include roles in tokens by default. We need an Action to add them.

### 4.1 Navigate to Actions
```
Auth0 Dashboard → Actions → Flows → Login
```

### 4.2 Create Custom Action
Click **+ Add Action** → **Build Custom**

**Name:** Add Roles to Token
**Trigger:** Login / Post Login
**Runtime:** Node 18 (Recommended)

### 4.3 Action Code
```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://aurity.app/';

  if (event.authorization) {
    const roles = event.authorization.roles || [];

    // Add roles to ID token (for frontend)
    api.idToken.setCustomClaim(`${namespace}roles`, roles);

    // Add roles to access token (for backend API)
    api.accessToken.setCustomClaim(`${namespace}roles`, roles);
  }
};
```

### 4.4 Deploy Action
1. Click **Deploy**
2. Go back to **Actions → Flows → Login**
3. Drag your "Add Roles to Token" action to the flow
4. Click **Apply**

---

## 👤 Step 5: Create Test Users

### 5.1 Navigate to Users
```
Auth0 Dashboard → User Management → Users → Create User
```

### 5.2 Create Users

**User 1: Doctor**
```
Email: doctor@hospital.com
Password: Test@1234
Connection: Username-Password-Authentication
```

**User 2: Nurse**
```
Email: nurse@hospital.com
Password: Test@1234
Connection: Username-Password-Authentication
```

**User 3: Admin**
```
Email: admin@hospital.com
Password: Test@1234
Connection: Username-Password-Authentication
```

### 5.3 Assign Roles
For each user:
1. Click on the user
2. Go to **Roles** tab
3. Click **Assign Roles**
4. Select `MEDICO`, `ENFERMERA`, or `ADMIN`
5. Click **Assign**

---

## 🔐 Step 6: Configure Backend

### 6.1 Set Environment Variables
```bash
export AUTH0_DOMAIN=dev-1r4daup7ofj7q6gn.auth0.com
export AUTH0_CLIENT_ID=rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp
export AUTH0_API_IDENTIFIER=https://api.aurity.io
export FRONTEND_URL_PROD=https://app.aurity.io
export FRONTEND_URL_DEV=http://localhost:9000
```

Or create `.env` file:
```bash
cp .env.auth0.example .env
# Edit .env with your credentials
```

### 6.2 Start Backend
```bash
make run
```

### 6.3 Test Auth0 Integration
```bash
# Check health
curl http://localhost:7001/api/auth/health

# Get Auth0 config (for frontend)
curl http://localhost:7001/api/auth/config
```

Expected response:
```json
{
  "status": "healthy",
  "auth0_domain": "dev-1r4daup7ofj7q6gn.auth0.com",
  "jwks_url": "https://dev-1r4daup7ofj7q6gn.auth0.com/.well-known/jwks.json",
  "jwks_keys_count": 2
}
```

---

## 🧪 Step 7: Test Authentication Flow

### 7.1 Get Test Token
Use Auth0's API to get a token for testing:

```bash
curl --request POST \
  --url https://dev-1r4daup7ofj7q6gn.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id":"rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp",
    "client_secret":"YOUR_CLIENT_SECRET",
    "audience":"https://api.aurity.io",
    "grant_type":"client_credentials"
  }'
```

### 7.2 Test Protected Endpoint
```bash
export ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     http://localhost:7001/api/auth/me
```

Expected response:
```json
{
  "user_id": "auth0|507f1f77bcf86cd799439011",
  "username": "doctor@hospital.com",
  "email": "doctor@hospital.com",
  "full_name": "Dr. Carlos Mendoza",
  "role": "MEDICO"
}
```

---

## 🎨 Step 8: Frontend Integration (Next.js)

### 8.1 Install Auth0 React SDK
```bash
cd apps/aurity
pnpm install @auth0/auth0-react
```

### 8.2 Wrap App with Auth0Provider
`apps/aurity/pages/_app.tsx`:
```tsx
import { Auth0Provider } from '@auth0/auth0-react';

function MyApp({ Component, pageProps }) {
  return (
    <Auth0Provider
      domain="dev-1r4daup7ofj7q6gn.auth0.com"
      clientId="rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp"
      authorizationParams={{
        redirect_uri: typeof window !== 'undefined'
          ? window.location.origin + '/callback'
          : '',
        audience: 'https://api.aurity.io',
        scope: 'openid profile email'
      }}
    >
      <Component {...pageProps} />
    </Auth0Provider>
  );
}
```

### 8.3 Create Login Component
```tsx
import { useAuth0 } from '@auth0/auth0-react';

export function LoginButton() {
  const { loginWithRedirect, logout, isAuthenticated, user } = useAuth0();

  if (isAuthenticated) {
    return (
      <div>
        <span>Welcome, {user?.email}</span>
        <button onClick={() => logout()}>Logout</button>
      </div>
    );
  }

  return <button onClick={() => loginWithRedirect()}>Login</button>;
}
```

### 8.4 Make Authenticated API Calls
```tsx
import { useAuth0 } from '@auth0/auth0-react';

export function ProtectedComponent() {
  const { getAccessTokenSilently } = useAuth0();

  const fetchData = async () => {
    const token = await getAccessTokenSilently();

    const response = await fetch('http://localhost:7001/api/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    return response.json();
  };

  // ... use fetchData
}
```

---

## 🔒 HIPAA Compliance Checklist

For production HIPAA compliance:

- [ ] **Upgrade to Enterprise Plan** - Includes BAA ($$$)
- [ ] **Enable MFA** - User Management → Multi-factor Auth → Required
- [ ] **Configure Session Timeout** - Security → Session Management → 15 minutes
- [ ] **Enable Anomaly Detection** - Security → Attack Protection → Enable all
- [ ] **Set up Audit Logs Export** - Monitoring → Logs → Configure Log Stream
- [ ] **Sign BAA** - Contact Auth0 sales for HIPAA BAA
- [ ] **Review Permissions** - Ensure least privilege access
- [ ] **Test Breach Notification** - Auth0 will notify within 72 hours per HIPAA

---

## 📊 Monitoring & Logs

### View Auth0 Logs
```
Auth0 Dashboard → Monitoring → Logs
```

Filter by:
- **Success Logins** (s)
- **Failed Logins** (f, fp)
- **Token Exchange** (seacft)

### Export Logs for HIPAA Audit
```
Auth0 Dashboard → Monitoring → Logs → Export
```

---

## 🐛 Troubleshooting

### Error: "Invalid token signature"
**Cause:** Backend is using wrong JWKS URL
**Fix:** Verify `AUTH0_DOMAIN` in `.env`

### Error: "Invalid audience"
**Cause:** Token audience doesn't match API identifier
**Fix:** Verify `AUTH0_API_IDENTIFIER` matches API settings in Auth0 Dashboard

### Error: "Roles not in token"
**Cause:** Custom Action not deployed or not in flow
**Fix:** Check Actions → Flows → Login, ensure "Add Roles to Token" is active

### Error: "JWKS fetch failed"
**Cause:** Network issue or wrong domain
**Fix:** Test: `curl https://dev-1r4daup7ofj7q6gn.auth0.com/.well-known/jwks.json`

---

## 📚 Next Steps

1. ✅ Backend Auth0 integration (complete)
2. ⏳ Frontend React Auth0 integration (next)
3. ⏳ Protect SOAP endpoints with `Depends(get_current_user_auth0)`
4. ⏳ Test MFA flow
5. ⏳ Configure session timeout (15 min for HIPAA)
6. ⏳ Enable anomaly detection
7. ⏳ Set up log export for auditing

---

## 🔗 References

- [Auth0 Docs - React SDK](https://auth0.com/docs/quickstart/spa/react)
- [Auth0 Docs - FastAPI](https://auth0.com/docs/quickstart/backend/python)
- [Auth0 HIPAA Compliance](https://auth0.com/security/hipaa)
- [Auth0 RBAC](https://auth0.com/docs/manage-users/access-control/rbac)
