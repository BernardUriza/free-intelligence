# AURITY Framework
## Artificial United Robust Intelligence for Telemedicine Yield

> 🏥 Edge-first telemedicine framework with data sovereignty

**Version:** 0.1.0-alpha
**Sprint:** SPR-2025W44 (2025-10-27 a 2025-11-10)
**Status:** 🚧 In Active Development

---

## 🎯 Overview

Aurity es un framework de telemedicina que integra **Free Intelligence (FI)** como sistema nervioso técnico local, proporcionando memoria clínica verificable sin dependencia de nubes opacas.

### Key Principles

- 🔐 **Data Sovereignty** - Información sensible bajo control del médico
- 🏥 **On-Premise First** - Cloud cuando sea necesario
- 🔍 **Verifiable Memory** - Integridad criptográfica en datos clínicos
- ⚡ **Progressive Enhancement** - De IoT simple a AI clínica completa

## ⚡ Tech Stack

- ⚡ Next.js 16 con App Router
- 🔷 TypeScript para type safety
- 🎨 Tailwind CSS para estilos
- 📱 Diseño responsive
- 🌙 Soporte para modo oscuro
- ✅ ESLint + Git hooks configurados
- 🚀 Optimizado para producción
- 🐳 Docker ready

## 🚀 Quick Start

### Prerequisites

- Node.js 20.x LTS
- pnpm (preferred package manager)
- Docker & Docker Compose (opcional)

### Installation

1. **Clone and install dependencies**
   ```bash
   pnpm install
   ```

2. **Setup environment**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Run development server**
   ```bash
   pnpm dev
   ```

4. **Open browser**
   Abre [http://localhost:9000](http://localhost:9000) para ver la aplicación.

## Scripts Disponibles

- `pnpm dev` - Inicia el servidor de desarrollo (puerto 9000)
- `pnpm build` - Construye la aplicación para producción
- `pnpm start` - Inicia el servidor de producción
- `pnpm lint` - Ejecuta ESLint
- `pnpm type-check` - Verifica los tipos de TypeScript

- `fi_cli`: Se está migrando la lógica operativa desde `scripts/` hacia el CLI unificado `fi_cli`.
   - Ejemplo: `python -m fi_cli auth assign-superadmin --email user@example.com` (reemplazo sugerido)

## 📁 Project Structure

```
aurity/
├── src/                    # Next.js application source
│   ├── app/               # Next.js 14 App Router
│   ├── components/        # React components
│   └── lib/               # Utilities and helpers
│
├── aurity/                # Aurity Framework modules
│   ├── core/             # Free Intelligence Core
│   ├── modules/          # Feature modules (FI-Cold, FI-Entry, etc.)
│   ├── config/           # Configuration files
│   ├── scripts/          # Utility scripts
│   ├── docs/             # Documentation
│   └── tests/            # Test suites
│
├── .env.local            # Local environment (not committed)
├── .env.local.example    # Environment template
└── .git/hooks/           # Pre-commit hooks configured
```

**📖 Documentación detallada:** Ver [aurity/README.md](./aurity/README.md)

## 🔒 Security

### ⚠️ NEVER Commit

- `.env` files with secrets
- Private keys (`.pem`, `.key`)
- PHI data (patient information)
- Database dumps with real data

**Git hooks están configurados** para prevenir commits accidentales.

## ⚙️ Sprint Current

**SPR-2025W44** - Repository & Environment Setup
- ✅ Project structure
- ✅ Environment configuration
- ✅ Git hooks
- ⏳ Module development (FI-Cold, FI-Entry)

## 📚 Resources

- [AURITY FRAMEWORK.md](./AURITY%20FRAMEWORK.md) - Complete technical specification
- [Trello Board](https://trello.com/b/77MVRL0t) - Sprint tracking
- [aurity/README.md](./aurity/README.md) - Module documentation

## 📄 License

**Proprietary** - All rights reserved
© 2025 Aurity Framework Team