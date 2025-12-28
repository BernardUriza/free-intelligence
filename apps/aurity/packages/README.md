# Aurity Packages

Modular, reusable packages for the Aurity healthcare platform. These packages are designed to be published to npm for wider use.

## 📦 Available Packages

### [@aurity-standalone/auth](./auth/)
Authentication and RBAC utilities for healthcare applications.
- Type-safe role definitions
- JWT token claims handling
- Role checking utilities

### [@aurity-standalone/observability](./observability/)
HIPAA-compliant observability and telemetry utilities.
- Safe logging without PHI/PII exposure
- Telemetry context management
- Performance measurement utilities

## 🚀 Publishing to npm

### Prerequisites

1. Create npm account: https://www.npmjs.com/signup
2. Login: `npm login`
3. Ensure you have access to `@aurity-standalone` organization (or use your own scope)

### Publish Workflow

```bash
# 1. Build packages
cd packages/auth
pnpm build

cd ../observability
pnpm build

# 2. Test locally (optional)
npm link

# In your project
npm link @aurity-standalone/auth
npm link @aurity-standalone/observability

# 3. Publish to npm
cd packages/auth
npm publish --access public

cd ../observability
npm publish --access public
```

### Version Management

```bash
# Bump version (patch/minor/major)
cd packages/auth
npm version patch  # 0.1.0 -> 0.1.1

# Commit and tag
git add .
git commit -m "chore(auth): bump to v0.1.1"
git tag auth-v0.1.1
git push --tags
```

## 🔄 Development Workflow

### Local Development

```bash
# Install dependencies in all packages
pnpm install

# Build all packages
cd packages/auth && pnpm build
cd ../observability && pnpm build

# Watch mode for development
cd packages/auth && pnpm dev  # Terminal 1
cd packages/observability && pnpm dev  # Terminal 2
```

### Adding New Package

```bash
# 1. Create package directory
mkdir -p packages/my-new-package/src

# 2. Create package.json
cd packages/my-new-package
cat > package.json << 'EOF'
{
  "name": "@aurity-standalone/my-new-package",
  "version": "0.1.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  }
}
EOF

# 3. Create tsconfig.json
# (copy from auth/observability)

# 4. Create src/index.ts
# Add your code

# 5. Update root package.json
# Add to workspace dependencies
```

## 📚 Usage in External Projects

Once published to npm:

```bash
npm install @aurity-standalone/auth @aurity-standalone/observability
```

```typescript
import { hasRole, type TokenClaims } from '@aurity-standalone/auth';
import { sanitizeMessagePreview } from '@aurity-standalone/observability';

// Use in any TypeScript/JavaScript project
const claims: TokenClaims = { sub: 'user123', roles: ['FI-clinician'] };
if (hasRole(claims, 'FI-clinician')) {
  console.log('Access granted');
}
```

## 🔧 Maintenance

### Update Dependencies

```bash
# Update all packages
pnpm update --recursive

# Update specific package
cd packages/auth
pnpm update
```

### Run Tests

```bash
# Add vitest/jest to packages
cd packages/auth
pnpm add -D vitest

# Create tests
mkdir __tests__
touch __tests__/index.test.ts

# Run tests
pnpm test
```

## 📖 Documentation

Each package has its own README:
- [auth/README.md](./auth/README.md)
- [observability/README.md](./observability/README.md)

## 🎯 Roadmap

Future packages to consider:
- `@aurity-standalone/storage` - HDF5 and storage utilities
- `@aurity-standalone/medical` - Medical data types and validators
- `@aurity-standalone/ui` - Shared React components
- `@aurity-standalone/api` - API client utilities

## 📄 License

MIT © Aurity Team
