# @aurity-standalone/auth

Type-safe authentication and role-based access control (RBAC) utilities for Aurity healthcare platform.

## Installation

```bash
npm install @aurity-standalone/auth
# or
pnpm add @aurity-standalone/auth
# or
yarn add @aurity-standalone/auth
```

## Usage

```typescript
import { hasRole, getRoles, type TokenClaims } from '@aurity-standalone/auth';

// Check if user has a role
const claims: TokenClaims = {
  sub: 'auth0|123456',
  roles: ['FI-clinician', 'FI-staff']
};

if (hasRole(claims, 'FI-clinician')) {
  console.log('User is a clinician');
}

// Get all user roles
const roles = getRoles(claims);
console.log(roles); // ['FI-clinician', 'FI-staff']
```

## API Reference

### Types

#### `Role`
```typescript
type Role = 'FI-superadmin' | 'FI-clinician' | 'FI-staff' | 'FI-patient';
```

#### `TokenClaims`
```typescript
interface TokenClaims {
  sub: string;
  roles?: Role[];
  email?: string;
  name?: string;
}
```

### Functions

#### `hasRole(claims, role): boolean`
Check if user has a specific role.

#### `getRoles(claims): Role[]`
Get all roles from token claims.

#### `hasAnyRole(claims, roles): boolean`
Check if user has any of the specified roles.

#### `hasAllRoles(claims, roles): boolean`
Check if user has all of the specified roles.

## License

MIT © Aurity Team
