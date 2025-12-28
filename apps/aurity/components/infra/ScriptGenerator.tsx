"use client";

/**
 * Script Generator Component
 * Card: FI-INFRA-STR-014
 *
 * Generates custom installation scripts based on user selections
 */

import { useState } from "react";
import { Download, Settings } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CodeBlock } from "@/components/ui/code-block";

type Platform = "linux" | "macos" | "wsl2" | "synology" | "truenas";
type Profile = "development" | "production" | "nas";

interface ScriptConfig {
  platform: Platform;
  profile: Profile;
  turboDaemon: boolean;
  pnpmHardLinks: boolean;
  pm2Startup: boolean;
  customPorts: boolean;
}

export function ScriptGenerator() {
  const [config, setConfig] = useState<ScriptConfig>({
    platform: "linux",
    profile: "production",
    turboDaemon: false,
    pnpmHardLinks: true,
    pm2Startup: true,
    customPorts: false,
  });

  const generateScript = (): string => {
    const { platform, profile, turboDaemon, pnpmHardLinks, pm2Startup } = config;

    const shellHeader = platform === "wsl2" ? "#!/bin/bash\n# WSL2 Ubuntu" : "#!/bin/bash";

    let script = `${shellHeader}
# Free Intelligence - Custom Installation Script
# Generated: ${new Date().toISOString()}
# Platform: ${platform}
# Profile: ${profile}

set -e

echo "=========================================="
echo "Free Intelligence - Custom Setup"
echo "Platform: ${platform}"
echo "Profile: ${profile}"
echo "=========================================="
echo ""

`;

    // Prerequisites check
    script += `# 1. Check prerequisites
echo "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found"
    exit 1
fi

echo "✓ Node.js $(node -v)"
echo "✓ Python $(python3 --version)"

`;

    // Install pnpm
    script += `# 2. Install pnpm
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm@8.15.0${pnpmHardLinks ? "" : " --shamefully-hoist"}
fi
echo "✓ pnpm $(pnpm -v)"

`;

    // Install PM2
    if (profile === "production" || profile === "nas") {
      script += `# 3. Install PM2
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    npm install -g pm2
fi
echo "✓ PM2 installed"

`;
    }

    // Clone repository
    script += `# 4. Clone repository (if not already cloned)
if [ ! -d "free-intelligence" ]; then
    echo "Cloning repository..."
    git clone https://github.com/yourusername/free-intelligence.git
    cd free-intelligence
else
    cd free-intelligence
    git pull origin main
fi

`;

    // Create directories
    script += `# 5. Create directory structure
mkdir -p storage backups logs config
echo "✓ Directories created"

`;

    // Install dependencies
    script += `# 6. Install dependencies
echo "Installing Node.js dependencies..."
pnpm install ${profile === "production" ? "--frozen-lockfile" : ""}

echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

`;

    // Configure Turbo
    if (!turboDaemon) {
      script += `# 7. Configure Turborepo (daemon disabled)
cat > .turborc << 'EOF'
{
  "telemetry": false,
  "daemon": false
}
EOF
echo "✓ Turborepo configured (daemon OFF)"

`;
    }

    // Build
    if (profile === "production" || profile === "nas") {
      script += `# 8. Build production assets
echo "Building production assets..."
pnpm build
echo "✓ Build complete"

`;
    }

    // Environment file
    script += `# 9. Setup environment file
if [ ! -f ".env.local" ]; then
    cat > .env.local << 'EOF'
# Free Intelligence - Environment Configuration
# Generated: ${new Date().toISOString()}

# Storage paths
CORPUS_PATH=./storage/corpus.h5
BACKUP_PATH=./backups

# API endpoints (adjust with your IP)
NEXT_PUBLIC_API_URL=http://localhost:9001
TIMELINE_API_URL=http://localhost:9002

# Ports
PORT=9000
API_PORT=9001
TIMELINE_PORT=9002

# Mode
NODE_ENV=${profile}
NEXT_TELEMETRY_DISABLED=1
FI_LAN_BANNER=1

# Turbo settings
TURBO_TELEMETRY_DISABLED=1
TURBO_DAEMON=${turboDaemon ? "1" : "0"}
EOF
    echo "✓ .env.local created"
else
    echo "⚠ .env.local already exists (not overwriting)"
fi

`;

    // PM2 startup
    if (pm2Startup && (profile === "production" || profile === "nas")) {
      script += `# 10. Start services with PM2
echo "Starting services..."
pm2 start ecosystem.config.js
pm2 save

# Setup PM2 startup
pm2 startup ${platform === "macos" ? "launchd" : ""}
echo "✓ Services started"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  Frontend:  http://localhost:9000"
echo "  Backend:   http://localhost:9001"
echo "  Timeline:  http://localhost:9002"
echo ""
echo "Useful commands:"
echo "  pm2 ls              # List services"
echo "  pm2 logs            # View logs"
echo "  pm2 restart all     # Restart services"
echo "=========================================="
`;
    } else {
      script += `# 10. Manual start instructions
echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "To start services:"
echo ""
if [ "${profile}" == "development" ]; then
    echo "  # Development mode (hot reload):"
    echo "  pnpm dev"
else
    echo "  # Production mode:"
    echo "  pm2 start ecosystem.config.js"
    echo "  pm2 save"
fi
echo ""
echo "Access the application at:"
echo "  http://localhost:9000"
echo "=========================================="
`;
    }

    return script;
  };

  const downloadScript = () => {
    const script = generateScript();
    const blob = new Blob([script], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fi-install-${config.platform}-${config.profile}.sh`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="bg-slate-800/50 border-slate-700">
      <CardHeader>
        <div className="fi-flex-gap-md">
          <Settings className="h-5 w-5 fi-text-success" />
          <div>
            <CardTitle className="text-slate-50">Script Generator</CardTitle>
            <CardDescription className="text-slate-400">
              Customize and download a tailored installation script
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Configuration Options */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Platform */}
          <div className="fi-stack-sm">
            <Label htmlFor="platform" className="fi-text">Platform</Label>
            <Select
              value={config.platform}
              onValueChange={(value: string) => setConfig({ ...config, platform: value as Platform })}
            >
              <SelectTrigger id="platform" className="bg-slate-900 border-slate-700 fi-text">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700">
                <SelectItem value="linux">Linux (Ubuntu/Debian)</SelectItem>
                <SelectItem value="macos">macOS (Homebrew)</SelectItem>
                <SelectItem value="wsl2">Windows WSL2</SelectItem>
                <SelectItem value="synology">Synology DSM</SelectItem>
                <SelectItem value="truenas">TrueNAS SCALE</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Profile */}
          <div className="fi-stack-sm">
            <Label htmlFor="profile" className="fi-text">Profile</Label>
            <Select
              value={config.profile}
              onValueChange={(value: string) => setConfig({ ...config, profile: value as Profile })}
            >
              <SelectTrigger id="profile" className="bg-slate-900 border-slate-700 fi-text">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700">
                <SelectItem value="development">Development</SelectItem>
                <SelectItem value="production">Production</SelectItem>
                <SelectItem value="nas">NAS (Optimized)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Advanced Options */}
        <div className="fi-container-dark fi-stack-md">
          <h4 className="text-sm font-medium fi-text">Advanced Options</h4>

          <div className="fi-flex-between">
            <Label htmlFor="turbo-daemon" className="fi-subtitle">
              Enable Turbo Daemon
              <span className="block fi-text-xs-muted">May use more memory</span>
            </Label>
            <Switch
              id="turbo-daemon"
              checked={config.turboDaemon}
              onCheckedChange={(checked: boolean) => setConfig({ ...config, turboDaemon: checked })}
            />
          </div>

          <div className="fi-flex-between">
            <Label htmlFor="pnpm-hardlinks" className="fi-subtitle">
              pnpm Hard Links
              <span className="block fi-text-xs-muted">Save 50-70% disk space</span>
            </Label>
            <Switch
              id="pnpm-hardlinks"
              checked={config.pnpmHardLinks}
              onCheckedChange={(checked: boolean) => setConfig({ ...config, pnpmHardLinks: checked })}
            />
          </div>

          <div className="fi-flex-between">
            <Label htmlFor="pm2-startup" className="fi-subtitle">
              PM2 Auto-Startup
              <span className="block fi-text-xs-muted">Start services on boot</span>
            </Label>
            <Switch
              id="pm2-startup"
              checked={config.pm2Startup}
              onCheckedChange={(checked: boolean) => setConfig({ ...config, pm2Startup: checked })}
            />
          </div>
        </div>

        {/* Generated Script Preview */}
        <div className="fi-stack-sm">
          <Label className="fi-text">Generated Script Preview</Label>
          <CodeBlock
            code={generateScript()}
            language="bash"
            filename={`fi-install-${config.platform}-${config.profile}.sh`}
          />
        </div>

        {/* Download Button */}
        <div className="flex justify-end">
          <Button
            onClick={downloadScript}
            className="bg-emerald-500 hover:bg-emerald-600 text-white"
          >
            <Download className="h-4 w-4 mr-2" />
            Download Script (.sh)
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
