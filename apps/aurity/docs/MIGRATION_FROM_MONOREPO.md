# Migration Guide: From Monorepo to Standalone

**Date:** December 18, 2025  
**Estimated Time:** 30 minutes  
**Difficulty:** Easy

---

## 🎯 Overview

This guide helps you migrate from using Aurity within the `free-intelligence` monorepo to running it as a **standalone project**.

### What Changed

| Before (Monorepo) | After (Standalone) |
|-------------------|-------------------|
| `@aurity/fi-auth` workspace package | `lib/internal/auth.ts` |
| `@aurity/fi-observability` workspace package | `lib/internal/observability.ts` |
| Parent repo dependencies | Self-contained |
| Monorepo build system | Independent build |

---

## 📋 Migration Steps

### Step 1: Backup Your Current Setup

```bash
# Create backup of your local changes
cd /path/to/free-intelligence/apps/aurity
git stash save "backup-before-standalone-migration"

# Or commit your changes
git add .
git commit -m "WIP: Before standalone migration"
```

---

### Step 2: Clone Standalone Repository

```bash
# Clone to new location
cd ~/Projects  # or your preferred location
git clone https://github.com/BernardUriza/aurity.git aurity-standalone
cd aurity-standalone
```

---

### Step 3: Copy Your Custom Code

```bash
# Copy your custom components/pages
# Example:
cp -r /path/to/free-intelligence/apps/aurity/app/custom-page ./app/
cp -r /path/to/free-intelligence/apps/aurity/components/custom ./components/

# Copy your .env.local (if you have one)
cp /path/to/free-intelligence/apps/aurity/.env.local ./.env.local
```

---

### Step 4: Update Import Statements

**Old imports (monorepo):**
```typescript
import { hasRole } from '@aurity/fi-auth';
import { sanitizeMessagePreview } from '@aurity/fi-observability';
```

**New imports (standalone):**
```typescript
import { hasRole } from '@/lib/internal/auth';
import { sanitizeMessagePreview } from '@/lib/internal/observability';
```

**Automated migration:**
```bash
# Find all files that need updates
grep -r "@aurity/fi-auth" app/ components/ lib/ hooks/

# Replace with standalone imports
find app components lib hooks -type f \( -name "*.ts" -o -name "*.tsx" \) \
  -exec sed -i '' "s/@aurity\/fi-auth/@\/lib\/internal\/auth/g" {} +

find app components lib hooks -type f \( -name "*.ts" -o -name "*.tsx" \) \
  -exec sed -i '' "s/@aurity\/fi-observability/@\/lib\/internal\/observability/g" {} +
```

---

### Step 5: Install Dependencies

```bash
# Install all dependencies
pnpm install

# Verify no errors
pnpm type-check
```

---

### Step 6: Test Your Setup

```bash
# Start development server
pnpm dev

# Open http://localhost:9000
# Test all your custom features
```

---

## 🔄 API Changes

### No Breaking Changes!

The standalone version maintains **100% API compatibility** with the monorepo version.

All backend endpoints remain the same:
- ✅ `/api/workflows/aurity/sessions`
- ✅ `/api/workflows/aurity/assistant/chat`
- ✅ `/api/workflows/aurity/stream`
- etc.

---

## 📦 Package.json Changes

### Before (Monorepo)

```json
{
  "dependencies": {
    "@aurity/fi-auth": "workspace:*",
    "@aurity/fi-observability": "workspace:*",
    "next": "16.0.1",
    "react": "^19.2.0"
  }
}
```

### After (Standalone)

```json
{
  "dependencies": {
    "next": "16.0.1",
    "react": "^19.2.0"
  }
}
```

**Note:** Workspace dependencies removed, replaced with internal utilities.

---

## 🧪 Verify Migration Success

### Checklist

- [ ] Project runs: `pnpm dev` works without errors
- [ ] Type checking passes: `pnpm type-check`
- [ ] All custom pages load correctly
- [ ] Authentication works (or mock auth enabled)
- [ ] API calls succeed (or mock backend enabled)
- [ ] Build succeeds: `pnpm build`

### Test Script

```bash
#!/bin/bash
echo "🧪 Testing standalone migration..."

echo "1. Type checking..."
pnpm type-check || exit 1

echo "2. Linting..."
pnpm lint || exit 1

echo "3. Building..."
pnpm build || exit 1

echo "✅ All tests passed! Migration successful."
```

---

## 🔧 Troubleshooting

### Issue: Import Errors After Migration

**Symptom:**
```
Cannot find module '@aurity/fi-auth'
```

**Solution:**
```bash
# Verify all imports were updated
grep -r "@aurity/" app/ components/ lib/

# Manual fix if needed
# Replace @aurity/fi-auth → @/lib/internal/auth
# Replace @aurity/fi-observability → @/lib/internal/observability
```

---

### Issue: Type Errors

**Symptom:**
```typescript
Type 'Role' is not assignable to type 'string'
```

**Solution:**
```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules
pnpm install

# Rebuild
pnpm build
```

---

### Issue: Backend Connection Failed

**Symptom:**
```
Failed to fetch: http://localhost:7001/api/workflows/aurity/sessions
```

**Solution:**

**Option 1: Start backend**
```bash
cd /path/to/free-intelligence
make run
```

**Option 2: Enable mock backend**
```bash
# .env.local
NEXT_PUBLIC_MOCK_BACKEND=true
```

---

## 🚀 Deploy Standalone Version

### Vercel

```bash
vercel
```

### DigitalOcean App Platform

```bash
# Push to GitHub
git push origin main

# Connect to DigitalOcean App Platform via UI
# Build command: pnpm build
# Output directory: .next
```

### Docker

```bash
docker build -t aurity:latest .
docker run -p 9000:9000 --env-file .env.local aurity:latest
```

---

## 🔄 Reverting to Monorepo

If you need to go back to the monorepo setup:

```bash
# 1. Go to monorepo
cd /path/to/free-intelligence/apps/aurity

# 2. Restore your stashed changes
git stash pop

# 3. Reinstall monorepo dependencies
cd ../..  # Go to root
pnpm install

# 4. Start monorepo dev server
make dev-all
```

---

## 📊 Comparison: Monorepo vs Standalone

| Feature | Monorepo | Standalone |
|---------|----------|-----------|
| **Setup Time** | 5 minutes | 15 minutes |
| **Repo Size** | ~500 MB | ~50 MB |
| **Dependencies** | Shared workspace | Self-contained |
| **Build Time** | 3-4 minutes | 1-2 minutes |
| **Backend Coupling** | Tight | Loose (API-only) |
| **Independent Deploy** | ❌ No | ✅ Yes |
| **Team Coordination** | Required | Minimal |

---

## 🎓 Next Steps After Migration

1. ✅ **Update your development workflow**
   - New repo location
   - Independent `git` commands
   - Standalone CI/CD pipeline

2. 📖 **Read new documentation**
   - [STANDALONE_SETUP.md](./STANDALONE_SETUP.md)
   - [API_CONTRACT.md](./API_CONTRACT.md)

3. 🔧 **Configure environment**
   - `.env.local` with your settings
   - Auth0 credentials
   - Backend URL

4. 🚀 **Deploy to production**
   - Choose your platform
   - Set production env vars
   - Configure CORS on backend

---

## 📞 Support

- **Issues with migration?** [Create an issue](https://github.com/BernardUriza/aurity/issues)
- **Questions?** [GitHub Discussions](https://github.com/BernardUriza/aurity/discussions)
- **Need help?** Contact the team

---

**Migration completed! 🎉**

You're now running Aurity as an independent project.
