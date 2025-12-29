# Aurity Desktop

Medical AI Assistant for desktop with offline-first architecture and optional cloud sync.

## Authentication

Aurity Desktop supports two authentication modes:

### 1. Auth0 Native Authentication (Recommended for Production)

Uses OAuth 2.0 + PKCE with deep links for secure authentication:

1. User clicks "Login" → Browser opens to Auth0
2. User authenticates → Auth0 redirects to `aurity://callback`
3. Tauri captures callback → Exchanges code for tokens
4. Tokens stored in OS Keychain (not localStorage)

**Setup:**

1. Go to [Auth0 Dashboard](https://manage.auth0.com) → Applications → Create Application
2. Select **Native** as the application type
3. In Settings, configure:
   - **Allowed Callback URLs:** `aurity://callback`
   - **Allowed Web Origins:** `aurity://`
   - **Token Endpoint Authentication Method:** None
4. Enable **Refresh Token Rotation** in Application Settings
5. Copy Domain and Client ID to `.env.desktop`:

```env
NEXT_PUBLIC_AUTH0_DOMAIN=your-tenant.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your-native-client-id
NEXT_PUBLIC_AUTH0_AUDIENCE=https://app.aurity.io
NEXT_PUBLIC_DESKTOP_OFFLINE=false
```

### 2. Offline Mode (Development / Air-gapped)

For development or deployments without internet access:

```env
NEXT_PUBLIC_DESKTOP_OFFLINE=true
# or
NEXT_PUBLIC_USE_MOCK_AUTH=true
```

This creates a synthetic user: `sub=desktop|local`, `email=local@desktop.local`, `roles=[FI-clinician]`.

**Security Warning:** Offline mode should NOT be enabled in production builds with sensitive data.

### 3. Controlled Offline Fallback

When Auth0 is configured but unreachable:
- User sees a dialog explaining limitations
- Must explicitly confirm to enter offline mode
- Mode expires automatically after 24 hours
- Limited functionality (no cloud sync)

## Deep Link Registration

The app registers `aurity://` URL scheme on:

| Platform | Registration Method |
|----------|---------------------|
| macOS | Info.plist (bundled with app) |
| Windows | Registry entry (on install) |
| Linux | .desktop file (on install) |

## Build Instructions

### Prerequisites

- Rust 1.70+
- Node.js 20+
- pnpm 8+
- Python 3.11+ (for backend sidecar)

### Development Build

```bash
# Install dependencies
pnpm install

# Build frontend
cd apps/aurity && pnpm build

# Run Tauri in dev mode
cd apps/aurity-desktop/src-tauri
cargo tauri dev
```

### Production Build (macOS)

```bash
# Kill running instances
pkill -f "Aurity" || true
pkill -f "aurity-backend" || true

# Rebuild backend sidecar (PyInstaller)
cd apps/aurity-desktop/pyinstaller
./build.sh

# Ensure icons are present
SRC="apps/aurity/public/icons"
DST="apps/aurity-desktop/src-tauri/icons"
sips -z 32 32 "$SRC/icon-72x72.png" --out "$DST/32x32.png"
sips -z 128 128 "$SRC/icon-128x128.png" --out "$DST/128x128.png"
sips -z 256 256 "$SRC/icon-384x384.png" --out "$DST/128x128@2x.png"
cp "$SRC/icon-512x512.png" "$DST/icon.png"

# Rebuild Tauri app
cd apps/aurity-desktop/src-tauri
cargo tauri build

# Create DMG (optional)
create-dmg --volname "Aurity" \
  --background "icons/dmg-background.png" \
  --icon "Aurity.app" 180 200 \
  --app-drop-link 480 200 \
  "Aurity.dmg" \
  "target/release/bundle/macos/Aurity.app"
```

### Running with Logs

```bash
./target/release/bundle/macos/Aurity.app/Contents/MacOS/aurity-desktop
```

## Local TLS Certificates

For HTTPS in development:

```bash
# Setup mkcert and generate certificates
./scripts/setup-dev-tls.sh

# Certificates are saved to ~/.aurity/certs/
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AURITY DESKTOP                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Frontend  │    │   Tauri     │    │  Backend    │     │
│  │  (Next.js)  │◄──►│  (Rust)     │◄──►│  (FastAPI)  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│        │                  │                   │             │
│        │                  │                   │             │
│        ▼                  ▼                   ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Auth0      │    │  Keychain   │    │  Ollama     │     │
│  │  Provider   │    │  (Tokens)   │    │  (LLM)      │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Security Notes

- Tokens are stored in OS Keychain, not localStorage
- PKCE prevents authorization code interception
- State parameter prevents CSRF attacks
- Refresh token rotation limits token reuse
- Backend validates tokens via Auth0 JWKS
- PHI is never logged
