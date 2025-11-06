# FI-Stride

**Progressive Web App (PWA) para entrenamiento personalizado de personas con síndrome de Down (T21)**

## Arquitectura

FI-Stride es una SPA (Single Page Application) basada en **Vite + React 18.3 + TypeScript** que implementa un patrón **multiplexor** en `App.tsx`:

```
App.tsx (Multiplexor)
├── LoginPage (Sin autenticación)
│   ├── Selector de rol: Coach | Athlete
│   └── Formulario de login
├── CoachDashboard (role === 'coach')
│   ├── Gestión de deportistas
│   ├── Sesiones registradas
│   └── Configuración
└── AthleteFlow (role === 'athlete')
    ├── Consentimiento informado
    ├── Permisos de dispositivo
    ├── Configuración de perfil
    └── Check-in de sesión
```

## Stack Tecnológico

| Categoría | Tecnología |
|-----------|-----------|
| **Framework** | Vite 5.0 + React 18.3 |
| **Lenguaje** | TypeScript 5.3 |
| **Estado** | Zustand (store global) |
| **Estilos** | CSS Modules (sin Tailwind) |
| **PWA** | vite-plugin-pwa con Workbox |
| **Puerto** | 9050 |
| **Proxy Backend** | http://localhost:7001 (FI Backend API) |

## Componentes Principales

### 1. **LoginPage** (`src/components/LoginPage.tsx`)
- Selector de rol (Deportista / Entrenador)
- Formulario de email + contraseña
- Almacenamiento en localStorage

### 2. **AthleteFlow** (`src/components/AthleteFlow.tsx`)
- **4 pasos progresivos:**
  1. Consentimiento informado (privacidad, encriptación, datos)
  2. Permisos de dispositivo (cámara, micrófono, ubicación)
  3. Configuración de perfil
  4. Confirmación de listo para entrenar

### 3. **CoachDashboard** (`src/components/CoachDashboard.tsx`)
- Gestión de deportistas asignados
- Historial de sesiones
- Configuración de cuenta

### 4. **App.tsx** (Multiplexor)
- Lógica de enrutamiento basada en auth + rol
- Persistencia de sesión (localStorage)
- Service Worker registration

## Estado Global (Zustand)

### `useAuthStore` (`src/store/authStore.ts`)

```typescript
{
  user: User | null,           // Usuario actual
  isAuthenticated: boolean,    // Estado de autenticación
  isLoading: boolean,          // Cargando login
  error: string | null,        // Mensajes de error
  login(email, password, role),  // Método de login
  logout(),                      // Logout
  setUser(user),                 // Actualizar usuario
  setError(error)                // Actualizar error
}
```

## Tipos (`src/types/index.ts`)

```typescript
type UserRole = 'coach' | 'athlete'

interface User {
  id: string
  name: string
  email: string
  role: UserRole
  avatar?: string
  createdAt: Date
}

interface Session {
  id: string
  athleteId: string
  coachId: string
  name: string
  duration: number
  rpe?: number // Rate of Perceived Exertion
  emotionalCheckIn?: string
  achievements?: string[]
  status: 'draft' | 'active' | 'completed'
}
```

## Configuración PWA

### Manifest
```json
{
  "name": "FI-Stride",
  "short_name": "FI-Stride",
  "description": "Entrenamiento personalizado para personas con T21",
  "display": "standalone",
  "start_url": "/",
  "scope": "/"
}
```

### Service Worker (vite-plugin-pwa)
- Estrategia: **NetworkFirst** para APIs, **CacheFirst** para assets
- Caché de sesiones offline
- Sincronización en background

## Desarrollo

### Instalar
```bash
cd apps/fi-stride
pnpm install
```

### Dev (HMR activo)
```bash
pnpm dev
# O desde root:
make stride-dev
```

### Build
```bash
pnpm build
# Output: dist/
```

### Type Check
```bash
pnpm type-check
```

### Lint
```bash
pnpm lint
```

## Integraciones con FI Backend

### API Proxy (vite.config.ts)
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:7001',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '/api')
  }
}
```

### Endpoints esperados:
- `POST /api/auth/login` → Autenticación
- `POST /api/sessions` → Crear sesión
- `GET /api/sessions/{id}` → Obtener sesión
- `GET /api/athletes` → Listar deportistas (coach)

## Demo Credentials

| Rol | Email | Password |
|-----|-------|----------|
| Deportista | `athlete@test.com` | `demo123` |
| Entrenador | `coach@test.com` | `demo123` |

> Nota: Actualmente con login mock. Integrar con `/api/auth/login` en producción.

## Estructura de Directorios

```
fi-stride/
├── src/
│   ├── components/
│   │   ├── LoginPage.tsx
│   │   ├── AthleteFlow.tsx
│   │   └── CoachDashboard.tsx
│   ├── store/
│   │   └── authStore.ts
│   ├── types/
│   │   └── index.ts
│   ├── styles/
│   │   ├── login.module.css
│   │   ├── athlete-flow.module.css
│   │   └── dashboard.module.css
│   ├── App.tsx (Multiplexor)
│   ├── App.css
│   ├── main.tsx
│   └── index.css
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── .eslintrc.cjs
```

## Responsive Design

- **Desktop**: Layout de 2+ columnas, navegación horizontal
- **Tablet**: Layout flexible, botones más grandes
- **Mobile**: Stack vertical, touch-friendly, viewport mínimo 320px

## Accessibility (a11y)

- Contraste mínimo WCAG AA (4.5:1)
- Navegación por teclado (Tab, Enter, Escape)
- Labels explícitos en formularios
- Descripciones de imágenes y iconos
- Progress indicator para pasos (AthleteFlow)

## Próximas Fases

- [ ] **FI-STRIDE-PWA-BASE-01**: Shell PWA + routing (ACTUAL)
- [ ] **FI-STRIDE-ONBOARDING-02**: Integración con Backend auth
- [ ] **FI-STRIDE-T21-PACK-03**: UI pack específico para T21
- [ ] **FI-STRIDE-SESION-04**: Sesión en vivo con cronómetro
- [ ] **FI-STRIDE-SESION-05**: Check-in emocional y logros
- [ ] Offline-first: Queue de sesiones, sync en background
- [ ] Encryption: Dead-Drop relay para privacidad

## Documentación Relacionada

- **AURITY**: Admin/physician dashboard (Next.js, puerto 9000)
- **Backend FI**: API core + diarization (FastAPI, puerto 7001)
- **CLAUDE.md**: Kernel de arquitectura y decisiones
