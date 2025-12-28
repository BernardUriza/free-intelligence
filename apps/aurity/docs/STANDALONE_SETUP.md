# Aurity Standalone Setup Guide

**Version:** 1.0.0  
**Date:** December 18, 2025  
**Estimated Setup Time:** 15-30 minutes

---

## 🎯 Overview

This guide helps you run Aurity frontend **independently** from the main free-intelligence monorepo.

### What You Get

✅ **Fully independent development** - No need for parent repository  
✅ **Mock backend support** - Develop without running backend  
✅ **Standalone deployment** - Deploy to any static hosting  
✅ **Complete functionality** - All features work independently

---

## 📋 Prerequisites

- **Node.js:** 20.10.0 or higher
- **pnpm:** 9.0.0 or higher
- **Git:** For cloning the repository

### Install Prerequisites

```bash
# Install Node.js 20 (using nvm)
nvm install 20
nvm use 20

# Install pnpm
npm install -g pnpm@latest

# Verify versions
node --version   # Should be v20.x.x
pnpm --version   # Should be v9.x.x
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Clone Repository

```bash
# Clone the standalone repository
git clone https://github.com/BernardUriza/aurity.git
cd aurity
```

### Step 2: Install Dependencies

```bash
# Install all dependencies (takes 2-3 minutes)
pnpm install
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.local.example .env.local

# Edit with your editor
nano .env.local  # or vim, code, etc.
```

**Minimal configuration for development:**

```bash
# .env.local
NEXT_PUBLIC_USE_MOCK_AUTH=true
NEXT_PUBLIC_MOCK_BACKEND=true
NEXT_PUBLIC_BACKEND_URL=http://localhost:7001
```

### Step 4: Start Development Server

```bash
pnpm dev
```

🎉 **Open http://localhost:9000** in your browser!

---

## 🔧 Configuration Options

### Mode 1: Fully Mocked (No Backend Required)

Perfect for **frontend-only development** and **UI testing**.

```bash
# .env.local
NEXT_PUBLIC_USE_MOCK_AUTH=true
NEXT_PUBLIC_MOCK_BACKEND=true
NEXT_PUBLIC_ALLOW_DEV_AUTOLOGIN=true
```

**What works:**
- ✅ All UI components
- ✅ Mock chat responses
- ✅ Mock session data
- ✅ Authentication flow (mocked)

**What doesn't work:**
- ❌ Real AI responses
- ❌ Real transcription
- ❌ Data persistence

---

### Mode 2: Mock Auth + Real Backend

Perfect for **testing against backend** without Auth0 setup.

```bash
# .env.local
NEXT_PUBLIC_USE_MOCK_AUTH=true
NEXT_PUBLIC_BACKEND_URL=http://localhost:7001
```

**Requirements:**
- Backend server running on localhost:7001

**Setup backend:**
```bash
# In another terminal
cd /path/to/free-intelligence
make run  # Starts backend on port 7001
```

---

### Mode 3: Full Production Mode

Perfect for **staging/production** deployment.

```bash
# .env.local
NEXT_PUBLIC_AUTH0_DOMAIN=your-tenant.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your_client_id
NEXT_PUBLIC_BACKEND_URL=https://api.aurity.io
NEXT_PUBLIC_BASE_URL=https://app.aurity.io
```

**Requirements:**
- Auth0 account and application
- Backend server running and accessible

---

## 🏗️ Build & Deploy

### Development Build

```bash
# Run development server
pnpm dev

# Access at http://localhost:9000
```

### Production Build

```bash
# Build for production
pnpm build

# Preview production build locally
pnpm start

# Access at http://localhost:9000
```

### Static Export (CDN/S3/Spaces)

```bash
# 1. Enable static export in next.config.mjs
# Uncomment line: output: 'export'

# 2. Build static files
pnpm build

# 3. Static files are in ./out/
# Deploy to: Vercel, Netlify, S3, DigitalOcean Spaces, etc.
```

---

## 📚 Project Structure

```
aurity/
├── app/                    # Next.js 16 App Router
│   ├── page.tsx           # Landing page
│   ├── layout.tsx         # Root layout
│   ├── dashboard/         # Main dashboard
│   ├── chat/              # AI chat interface
│   ├── medical-ai/        # Medical AI tools
│   └── admin/             # Admin panel
│
├── components/            # React components
│   ├── auth/             # Authentication
│   ├── chat/             # Chat UI
│   ├── medical/          # Medical forms
│   └── shared/           # Shared components
│
├── lib/                  # Core utilities
│   ├── api/             # API clients
│   ├── internal/        # ⭐ Standalone utilities
│   │   ├── auth.ts      # Auth utilities (extracted)
│   │   └── observability.ts  # Logging utilities (extracted)
│   └── hooks/           # React hooks
│
├── docs/                # Documentation
│   ├── API_CONTRACT.md  # ⭐ Backend API reference
│   └── STANDALONE_SETUP.md  # This file
│
├── .env.local.example   # ⭐ Environment template
├── package.json         # Dependencies (standalone)
├── tsconfig.json        # TypeScript config
└── next.config.mjs      # Next.js config
```

### ⭐ Key Files for Standalone Operation

1. **`lib/internal/auth.ts`** - Extracted from workspace package
2. **`lib/internal/observability.ts`** - Extracted from workspace package
3. **`lib/api/mock-backend.ts`** - Mock API for development
4. **`docs/API_CONTRACT.md`** - Backend API documentation
5. **`.env.local.example`** - Configuration template

---

## 🧪 Testing

### Run All Tests

```bash
# Unit tests
pnpm test

# E2E tests (if configured)
pnpm test:e2e

# Type checking
pnpm type-check

# Linting
pnpm lint
```

---

## 🐛 Troubleshooting

### Issue: Dependencies Won't Install

```bash
# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Issue: Port 9000 Already in Use

```bash
# Use different port
PORT=9001 pnpm dev
```

### Issue: Auth0 Login Not Working

1. Check Auth0 credentials in `.env.local`
2. Verify callback URL in Auth0 dashboard: `http://localhost:9000/callback`
3. Try mock auth: `NEXT_PUBLIC_USE_MOCK_AUTH=true`

### Issue: Backend Connection Failed

1. Check backend is running: `curl http://localhost:7001/health`
2. Check CORS settings in backend
3. Try mock backend: `NEXT_PUBLIC_MOCK_BACKEND=true`

---

## 📦 Deployment Platforms

### Vercel (Recommended)

```bash
# Install Vercel CLI
pnpm add -g vercel

# Deploy
vercel
```

### Netlify

```bash
# Build command: pnpm build
# Publish directory: .next (or ./out for static)

# Deploy
netlify deploy --prod
```

### DigitalOcean App Platform

```bash
# Dockerfile included in project
docker build -t aurity:latest .
docker run -p 9000:9000 aurity:latest
```

---

## 🔒 Security Checklist

Before deploying to production:

- [ ] Set strong `NEXT_PUBLIC_AUTH0_CLIENT_ID` and `NEXT_PUBLIC_AUTH0_DOMAIN`
- [ ] Use HTTPS for `NEXT_PUBLIC_BACKEND_URL` and `NEXT_PUBLIC_BASE_URL`
- [ ] Disable mock modes: `NEXT_PUBLIC_USE_MOCK_AUTH=false`, `NEXT_PUBLIC_MOCK_BACKEND=false`
- [ ] Configure CORS in backend to allow only your domain
- [ ] Review `NEXT_PUBLIC_SUPERADMIN_EMAILS` list
- [ ] Enable rate limiting on backend
- [ ] Set up monitoring and error tracking (Sentry, etc.)

---

## 📞 Support & Resources

- **Documentation:** [docs/](./docs/)
- **API Contract:** [docs/API_CONTRACT.md](./API_CONTRACT.md)
- **Issues:** [GitHub Issues](https://github.com/BernardUriza/aurity/issues)
- **Discussions:** [GitHub Discussions](https://github.com/BernardUriza/aurity/discussions)

---

## 🎓 Next Steps

1. ✅ Complete setup (you are here)
2. 📖 Read [API_CONTRACT.md](./API_CONTRACT.md) to understand backend
3. 🎨 Explore UI components in `components/`
4. 🔧 Customize configuration in `.env.local`
5. 🚀 Deploy to your platform of choice

---

**Happy Coding! 🎉**

Made with ❤️ by the Aurity Team
