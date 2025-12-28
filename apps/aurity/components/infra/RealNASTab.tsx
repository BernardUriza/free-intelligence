"use client";

/**
 * Real NAS Tab Component
 * Card: FI-INFRA-STR-014
 *
 * Installation instructions for real NAS devices
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { Callout } from "@/components/ui/callout";
import { PLATFORMS, REQUIREMENTS } from "@/lib/nas-config";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ScriptGenerator } from "./ScriptGenerator";

export function RealNASTab() {
  return (
    <div className="space-y-6">
      {/* Script Generator */}
      <ScriptGenerator />

      {/* Prerequisites */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">System Requirements</CardTitle>
          <CardDescription className="text-slate-400">
            Minimum and recommended specifications for NAS deployment
          </CardDescription>
        </CardHeader>
        <CardContent className="fi-stack-lg">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="fi-container-dark-sm">
              <div className="fi-text-xs-muted mb-1">Node.js</div>
              <div className="font-mono text-sm fi-text-success">{REQUIREMENTS.node.recommended}</div>
              <div className="fi-text-xs-muted mt-1">min: {REQUIREMENTS.node.min}</div>
            </div>
            <div className="fi-container-dark-sm">
              <div className="fi-text-xs-muted mb-1">Python</div>
              <div className="font-mono text-sm fi-text-success">{REQUIREMENTS.python.recommended}</div>
              <div className="fi-text-xs-muted mt-1">min: {REQUIREMENTS.python.min}</div>
            </div>
            <div className="fi-container-dark-sm">
              <div className="fi-text-xs-muted mb-1">Memory</div>
              <div className="font-mono text-sm fi-text-success">{REQUIREMENTS.memory.recommended}</div>
              <div className="fi-text-xs-muted mt-1">min: {REQUIREMENTS.memory.min}</div>
            </div>
            <div className="fi-container-dark-sm">
              <div className="fi-text-xs-muted mb-1">Disk Space</div>
              <div className="font-mono text-sm fi-text-success">{REQUIREMENTS.disk.recommended}</div>
              <div className="fi-text-xs-muted mt-1">min: {REQUIREMENTS.disk.min}</div>
            </div>
          </div>

          <Callout type="info" title="Supported Architectures">
            {REQUIREMENTS.cpu.arch.join(", ")} · {REQUIREMENTS.cpu.cores}+ cores recommended
          </Callout>
        </CardContent>
      </Card>

      {/* One-Command Installation */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Quick Installation (Recommended)</CardTitle>
          <CardDescription className="text-slate-400">
            One-command installer script that handles all setup steps automatically
          </CardDescription>
        </CardHeader>
        <CardContent className="fi-stack-lg">
          <CodeBlock
            code={`# Download and run the setup script
curl -fsSL https://raw.githubusercontent.com/yourusername/free-intelligence/main/scripts/nas-setup.sh | bash

# Or clone the repository first
git clone https://github.com/yourusername/free-intelligence.git
cd free-intelligence
chmod +x scripts/nas-setup.sh
./scripts/nas-setup.sh`}
            language="bash"
            filename="quick-install.sh"
          />

          <Callout type="warning" title="Important">
            After installation completes, edit <code>.env.local</code> with your NAS IP address before starting services.
          </Callout>

          <div className="pt-2">
            <h4 className="fi-label">What the script does:</h4>
            <ul className="space-y-1 fi-subtitle">
              <li className="flex items-start gap-2">
                <span className="fi-text-success mt-0.5">✓</span>
                <span>Checks prerequisites (Node 18+, Python 3.11+)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="fi-text-success mt-0.5">✓</span>
                <span>Installs pnpm if not present</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="fi-text-success mt-0.5">✓</span>
                <span>Creates required directories (storage, logs, backups)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="fi-text-success mt-0.5">✓</span>
                <span>Installs Node.js and Python dependencies</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="fi-text-success mt-0.5">✓</span>
                <span>Builds production assets with Turborepo</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="fi-text-success mt-0.5">✓</span>
                <span>Generates .env.local template</span>
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Manual Installation */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Manual Installation</CardTitle>
          <CardDescription className="text-slate-400">
            Step-by-step manual installation for advanced users
          </CardDescription>
        </CardHeader>
        <CardContent className="fi-stack-lg">
          <div className="fi-stack-lg">
            {/* Step 1 */}
            <div>
              <h4 className="fi-label">1. Install Prerequisites</h4>
              <CodeBlock
                code={`# Check Node.js version (must be 18+)
node -v

# Check Python version (must be 3.11+)
python3 --version

# Install pnpm globally
npm install -g pnpm@8.15.0

# Install PM2 for process management
npm install -g pm2`}
                language="bash"
              />
            </div>

            {/* Step 2 */}
            <div>
              <h4 className="fi-label">2. Clone Repository</h4>
              <CodeBlock
                code={`git clone https://github.com/yourusername/free-intelligence.git
cd free-intelligence`}
                language="bash"
              />
            </div>

            {/* Step 3 */}
            <div>
              <h4 className="fi-label">3. Install Dependencies</h4>
              <CodeBlock
                code={`# Install Node.js dependencies
pnpm install --frozen-lockfile

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt`}
                language="bash"
              />
            </div>

            {/* Step 4 */}
            <div>
              <h4 className="fi-label">4. Configure Environment</h4>
              <CodeBlock
                code={`# Copy environment template
cp .env.example .env.local

# Edit with your NAS IP
nano .env.local

# Update these values:
# NEXT_PUBLIC_API_URL=http://YOUR_NAS_IP:9001
# TIMELINE_API_URL=http://YOUR_NAS_IP:9002`}
                language="bash"
              />
            </div>

            {/* Step 5 */}
            <div>
              <h4 className="fi-label">5. Build Production Assets</h4>
              <CodeBlock
                code={`# Build all services with Turborepo
pnpm build

# This builds:
# - Backend API (FastAPI)
# - Timeline API
# - Frontend (Next.js)`}
                language="bash"
              />
            </div>

            {/* Step 6 */}
            <div>
              <h4 className="fi-label">6. Start Services with PM2</h4>
              <CodeBlock
                code={`# Start all services
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Enable PM2 startup on boot
pm2 startup

# Check service status
pm2 ls`}
                language="bash"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Platform-Specific Notes */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Platform-Specific Notes</CardTitle>
          <CardDescription className="text-slate-400">
            Additional configuration for specific NAS platforms
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible className="w-full">
            {Object.entries(PLATFORMS)
              .filter(([key]) => ["synology", "truenas", "ubuntu"].includes(key))
              .map(([key, platform]) => (
                <AccordionItem key={key} value={key} className="border-slate-700">
                  <AccordionTrigger className="fi-text hover:text-slate-100">
                    {platform.name} ({platform.version})
                  </AccordionTrigger>
                  <AccordionContent className="text-slate-400">
                    <ul className="fi-stack-sm">
                      {platform.notes.map((note, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="fi-text-success mt-0.5">•</span>
                          <span>{note}</span>
                        </li>
                      ))}
                    </ul>
                  </AccordionContent>
                </AccordionItem>
              ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* Next Steps */}
      <Callout type="success" title="Installation Complete!">
        After starting services, access the application at:
        <ul className="mt-2 space-y-1">
          <li className="font-mono text-sm">Frontend: http://your-nas-ip:9000</li>
          <li className="font-mono text-sm">Backend API: http://your-nas-ip:9001/docs</li>
          <li className="font-mono text-sm">Timeline API: http://your-nas-ip:9002/docs</li>
        </ul>
        <div className="mt-3 text-sm">
          Proceed to the <strong>Verification</strong> tab to validate your installation.
        </div>
      </Callout>
    </div>
  );
}
