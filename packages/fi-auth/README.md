# @aurity/fi-auth

Minimal RBAC helpers for AURITY MVP.

## Roles
- `FI-superadmin`
- `FI-clinician`
- `FI-staff`
- `FI-patient`

## Usage
```ts
import { getRoles, hasRole, type TokenClaims } from '@aurity/fi-auth';

function canUseAssistant(claims: TokenClaims) {
  const roles = getRoles(claims);
  return roles.includes('FI-clinician') || roles.includes('FI-superadmin');
}

// Example in API layer
if (!canUseAssistant(claims)) {
  throw new Error('Acceso denegado: rol insuficiente');
}
```

Claims shape expects `roles?: Role[]` parsed from Auth0 claim `https://aurity.app/roles`.