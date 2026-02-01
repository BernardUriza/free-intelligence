# Next.js Static Export Learnings

**Date**: 2025-12-11
**Context**: CI/CD deployment to DigitalOcean
**Card**: FI-UI-FEAT-205

## Problem

Next.js static export (`output: 'export'`) failing with error:
```
Page "/viewer/[id]" is missing "generateStaticParams()" so it cannot be used with "output: export" config.
```

Even though `generateStaticParams()` was defined in the page component.

## Root Cause

**Known Next.js bug** (versions 14-16): When `generateStaticParams()` returns an empty array `[]`, Next.js incorrectly reports the function as missing.

Reference: https://github.com/vercel/next.js/issues/71862

## Solution

Return a placeholder object instead of empty array:

```typescript
// BAD - triggers bug
export function generateStaticParams() {
  return [];
}

// GOOD - workaround
export function generateStaticParams() {
  return [{ id: 'placeholder' }];
}
```

## Additional Constraints

### 1. Server vs Client Components

`generateStaticParams()` must be in a **Server Component**. If your page uses `'use client'`, split it:

```
app/viewer/[id]/
├── page.tsx          # Server component with generateStaticParams()
└── ViewerClient.tsx  # Client component with interactive logic
```

### 2. dynamicParams Incompatibility

```typescript
// This does NOT work with static export:
export const dynamicParams = true;
```

Error: `'dynamicParams: true' cannot be used with 'output: export'`

The placeholder approach is sufficient - Next.js will still serve any dynamic ID at runtime.

## Pattern for Conditional Static Export

In `next.config.js`:
```javascript
const nextConfig = {
  // Enable static export only when STATIC_EXPORT=true
  ...(process.env.STATIC_EXPORT === 'true' && { output: 'export' }),
};
```

In CI/CD workflow:
```yaml
env:
  STATIC_EXPORT: 'true'
```

This allows `pnpm dev` to work normally while CI builds static assets.

## Verification

```bash
# Local verification
STATIC_EXPORT=true pnpm --filter aurity build

# Should output:
# ✓ Generating static pages (30/30)
# Including /viewer/placeholder
```

## Key Takeaways

1. Empty arrays in `generateStaticParams()` = bug trigger
2. Always use placeholder for dynamic routes in static export
3. Split server/client components when using App Router features
4. `dynamicParams: true` incompatible with static export
5. Use env var for conditional static export to maintain dev ergonomics
