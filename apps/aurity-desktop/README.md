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
- Python 3.14+ (automatically installed with Aurity Desktop on Windows)

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

### Production Build (Windows)

```powershell
# Kill running instances
Get-Process | Where-Object {$_.ProcessName -match "Aurity"} | Stop-Process -Force
Get-Process | Where-Object {$_.ProcessName -match "aurity-backend"} | Stop-Process -Force

# Rebuild backend sidecar (PyInstaller)
cd apps/aurity-desktop/pyinstaller
python -m PyInstaller aurity-backend-x86_64-pc-windows-msvc.spec

# Rebuild Tauri app
cd ..
pnpm tauri build --target x86_64-pc-windows-msvc

# Installer output: src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis/Aurity_1.0.0_x64-setup.nsis.zip
```

**Installation:**

1. Download `Aurity_1.0.0_x64-setup.nsis.zip` from GitHub Releases
2. Extract the `.nsis.zip` file
3. Run the installer executable
4. **SmartScreen Warning (Expected):**
   - Windows SmartScreen will show "Windows protected your PC"
   - This is normal for Ed25519-signed apps (not traditional Windows certificates)
   - Click "More info" → "Run anyway" to proceed
5. The app will install to `%LOCALAPPDATA%\Programs\Aurity`
6. Shortcut created in Start Menu

**Verification:**

To verify the download integrity, compare the SHA256 hash provided in the GitHub Release notes:

```powershell
Get-FileHash Aurity_1.0.0_x64-setup.exe -Algorithm SHA256
```

### Production Build (Linux)

```bash
# Build backend sidecar
cd apps/aurity-desktop/pyinstaller
pyinstaller aurity-backend.spec

# Build Tauri app
cd ..
pnpm tauri build --target x86_64-unknown-linux-gnu

# Output: src-tauri/target/x86_64-unknown-linux-gnu/release/bundle/appimage/*.AppImage
```

### Running with Logs

**macOS:**

```bash
./target/release/bundle/macos/Aurity.app/Contents/MacOS/aurity-desktop
```

**Windows:**

```powershell
& "$env:LOCALAPPDATA\Programs\Aurity\Aurity.exe"
# Logs: %APPDATA%\io.aurity.desktop\logs\
```

**Linux:**

```bash
./Aurity_1.0.0_amd64.AppImage
```

## 📧 CI/CD Email Notifications

Windows builds envían notificación automática cuando terminan exitosamente vía **Azure Communication Services**.

### Setup de Secrets (one-time)

Los siguientes secrets deben estar configurados en GitHub:

```bash
gh secret set ACS_SMTP_USERNAME      # ResourceName|AppID|TenantID
gh secret set ACS_SMTP_PASSWORD      # Entra ID app secret
gh secret set ACS_FROM_EMAIL         # DoNotReply@xxxxx.azurecomm.net
gh secret set NOTIFY_EMAIL           # Destinatario de notificaciones
```

### Trigger manual

```bash
gh workflow run build-desktop.yml -f platform=windows
# Email llega cuando el build termina (~10-15 min)
```

### Troubleshooting

| Problema | Solución |
|----------|----------|
| Email no llega | Revisa spam, verifica secrets con `gh secret list` |
| Authentication error | Verifica formato username: `ResourceName\|AppID\|TenantID` |
| Workflow falla | Email tiene `continue-on-error: true`, no debería fallar workflow |
| Cambiar email destino | `gh secret set NOTIFY_EMAIL --body "nuevo@email.com"` |
| Rotar credentials | Generar nuevo app secret en Azure AD, actualizar `ACS_SMTP_PASSWORD` |

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

## Python Installation (Windows)

Aurity Desktop automatically installs Python 3.14 Full during setup if not already present.

**Installation details:**
- **Location:** `%LOCALAPPDATA%\Programs\Python\Python314\`
- **Scope:** Per-user (no admin required)
- **Dependencies:** Includes pip, fastapi, uvicorn, httpx, sentence-transformers

**Verify installation:**
```powershell
python --version  # Should show: Python 3.14.0
python -m pip list | Select-String "fastapi|uvicorn"
```

**Troubleshooting:**
- If `python` command not found: Restart terminal (PATH updated)
- If fi-monitor fails: Run `apps/aurity-desktop/scripts/test-python-install.ps1`
- Manual repair: Re-run Aurity installer (will re-check and reinstall if needed)
