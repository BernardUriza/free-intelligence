"use client";

/**
 * Verification Tab Component
 * Card: FI-INFRA-STR-014
 *
 * Health checks and verification tools
 */

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { Callout } from "@/components/ui/callout";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2, Play, Check } from "lucide-react";
import { SERVICES } from "@/lib/nas-config";

type CheckStatus = "idle" | "running" | "success" | "error";

interface CheckResult {
  status: CheckStatus;
  message?: string;
  duration?: number;
}

export function VerificationTab() {
  const [checks, setChecks] = useState<Record<string, CheckResult>>({
    backend: { status: "idle" },
    timeline: { status: "idle" },
    frontend: { status: "idle" },
    pm2: { status: "idle" },
  });

  const runHealthCheck = async (service: string, url: string) => {
    setChecks((prev) => ({ ...prev, [service]: { status: "running" } }));
    const startTime = Date.now();

    try {
      const response = await fetch(url, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      const duration = Date.now() - startTime;

      if (response.ok) {
        setChecks((prev) => ({
          ...prev,
          [service]: {
            status: "success",
            message: `OK (${duration}ms)`,
            duration,
          },
        }));
      } else {
        setChecks((prev) => ({
          ...prev,
          [service]: {
            status: "error",
            message: `HTTP ${response.status}`,
          },
        }));
      }
    } catch (error) {
      setChecks((prev) => ({
        ...prev,
        [service]: {
          status: "error",
          message: error instanceof Error ? error.message : "Connection failed",
        },
      }));
    }
  };

  const runAllChecks = () => {
    runHealthCheck("backend", "http://localhost:9001/api/health");
    runHealthCheck("timeline", "http://localhost:9002/api/health");
    runHealthCheck("frontend", "http://localhost:9000");
  };

  const getStatusIcon = (status: CheckStatus) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="h-5 w-5 fi-text-success" />;
      case "error":
        return <XCircle className="h-5 w-5 fi-text-error" />;
      case "running":
        return <Loader2 className="h-5 w-5 fi-text-primary animate-spin" />;
      default:
        return <div className="h-5 w-5 rounded-full border-2 border-slate-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Automated Health Checks */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <div className="fi-flex-between">
            <div>
              <CardTitle className="text-slate-50">Automated Health Checks</CardTitle>
              <CardDescription className="text-slate-400">
                Verify all services are running and accessible
              </CardDescription>
            </div>
            <Button
              onClick={runAllChecks}
              className="bg-emerald-500 hover:bg-emerald-600 text-white"
            >
              <Play className="h-4 w-4 mr-2" />
              Run All Checks
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {SERVICES.map((service) => {
            const checkKey = service.name.replace("fi-", "").replace("-api", "");
            const check = checks[checkKey];

            return (
              <div
                key={service.name}
                className="fi-container-dark fi-flex-between"
              >
                <div className="fi-flex-gap-md">
                  {getStatusIcon(check.status)}
                  <div>
                    <div className="text-sm font-medium fi-text">{service.name}</div>
                    <div className="fi-text-xs-muted">Port {service.port}</div>
                  </div>
                </div>
                <div className="text-right">
                  {check.message && (
                    <div className={`text-sm font-mono ${
                      check.status === "success" ? "fi-text-success" : "fi-text-error"
                    }`}>
                      {check.message}
                    </div>
                  )}
                  {check.status === "idle" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const port = service.port;
                        const endpoint = service.type === "frontend"
                          ? `http://localhost:${port}`
                          : `http://localhost:${port}/api/health`;
                        runHealthCheck(checkKey, endpoint);
                      }}
                      className="border-slate-600 hover:bg-slate-700"
                    >
                      Check
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Manual Verification Commands */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Manual Verification</CardTitle>
          <CardDescription className="text-slate-400">
            Command-line tools to verify installation
          </CardDescription>
        </CardHeader>
        <CardContent className="fi-stack-lg">
          <div>
            <h4 className="fi-label">Check PM2 Services</h4>
            <CodeBlock
              code={`# List all PM2 processes
pm2 ls

# Expected output:
# ┌─────┬──────────────────┬─────────┬─────────┬────────┐
# │ id  │ name             │ status  │ cpu     │ memory │
# ├─────┼──────────────────┼─────────┼─────────┼────────┤
# │ 0   │ fi-backend-api   │ online  │ 0%      │ 150 MB │
# │ 1   │ fi-timeline-api  │ online  │ 0%      │ 80 MB  │
# │ 2   │ fi-frontend      │ online  │ 0%      │ 120 MB │
# └─────┴──────────────────┴─────────┴─────────┴────────┘

# View logs
pm2 logs

# Check specific service
pm2 show fi-backend-api`}
              language="bash"
            />
          </div>

          <div>
            <h4 className="fi-label">Test API Endpoints</h4>
            <CodeBlock
              code={`# Backend API health check
curl -s http://localhost:9001/api/health | jq

# Timeline API health check
curl -s http://localhost:9002/api/health | jq

# Check sessions endpoint
curl -s "http://localhost:9001/api/sessions?limit=5" | jq

# Check KPIs endpoint
curl -s "http://localhost:9001/api/kpis?window=5m&view=summary" | jq`}
              language="bash"
            />
          </div>

          <div>
            <h4 className="fi-label">Verify Storage</h4>
            <CodeBlock
              code={`# Check corpus file exists
ls -lh storage/corpus.h5

# Check log files
ls -lh logs/

# Verify directory structure
tree -L 2 -d`}
              language="bash"
            />
          </div>

          <div>
            <h4 className="fi-label">Run Smoke Tests</h4>
            <CodeBlock
              code={`# Backend unit tests
python3 -m pytest tests/ -v --tb=short

# Frontend type check
cd apps/aurity && pnpm exec tsc --noEmit

# Integration smoke test
./tools/smoke.sh`}
              language="bash"
            />
          </div>
        </CardContent>
      </Card>

      {/* LAN-Only Banner Check */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Security Verification</CardTitle>
          <CardDescription className="text-slate-400">
            Confirm LAN-only mode is active
          </CardDescription>
        </CardHeader>
        <CardContent className="fi-stack-lg">
          <Callout type="info" title="Expected Behavior">
            When accessing <code>http://localhost:9000</code>, you should see:
            <ul className="mt-2 space-y-1 text-sm">
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />Yellow banner at the top: &quot;LAN-ONLY MODE ACTIVE&quot;</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />No external API calls in browser console</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />All API requests to localhost or LAN IP</li>
            </ul>
          </Callout>

          <div>
            <h4 className="fi-label">Verify CORS Configuration</h4>
            <CodeBlock
              code={`# Check CORS headers (should allow localhost)
curl -i -H "Origin: http://localhost:9000" \\
  "http://localhost:9001/api/health"

# Look for:
# Access-Control-Allow-Origin: http://localhost:9000
# Access-Control-Allow-Credentials: true`}
              language="bash"
            />
          </div>

          <div>
            <h4 className="fi-label">Check Environment Variables</h4>
            <CodeBlock
              code={`# Verify .env.local configuration
cat .env.local

# Required variables:
# NEXT_PUBLIC_API_URL=http://localhost:9001
# TIMELINE_API_URL=http://localhost:9002
# FI_LAN_BANNER=1  (shows LAN-only warning)`}
              language="bash"
            />
          </div>
        </CardContent>
      </Card>

      {/* Performance Validation */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Performance Validation</CardTitle>
          <CardDescription className="text-slate-400">
            Verify SLO compliance (p95 latencies)
          </CardDescription>
        </CardHeader>
        <CardContent className="fi-stack-lg">
          <div>
            <h4 className="fi-label">Run p95 Latency Test</h4>
            <CodeBlock
              code={`# Test Timeline API p95 (should be < 300ms)
BASE=http://localhost:9002
SID=$(curl -s "$BASE/api/timeline/sessions?limit=1" | jq -r '.[0].metadata.session_id')

# 40 samples for p95 calculation
for i in {1..40}; do
  curl -s -o /dev/null -w "%{time_total}\\n" \\
    "$BASE/api/timeline/sessions?limit=50"
done | sort -n | awk '{a[NR]=$1} END{print a[int(0.95*NR)]}'

# Expected: < 0.300 seconds (300ms)`}
              language="bash"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { name: "Timeline API", threshold: "300ms", slo: "p95 < 300ms" },
              { name: "Sessions API", threshold: "500ms", slo: "p95 < 500ms" },
              { name: "KPIs API", threshold: "10ms", slo: "p95 < 10ms" },
            ].map((api) => (
              <div
                key={api.name}
                className="p-3 rounded-lg bg-slate-900 border border-slate-700"
              >
                <div className="text-sm font-medium fi-text mb-1">{api.name}</div>
                <div className="fi-text-xs-muted">Threshold: {api.threshold}</div>
                <div className="text-xs fi-text-success mt-2">{api.slo}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Troubleshooting */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Troubleshooting</CardTitle>
        </CardHeader>
        <CardContent className="fi-stack-lg">
          <div>
            <h4 className="text-sm font-medium fi-text-error mb-2">Service won&apos;t start</h4>
            <ul className="space-y-1 fi-subtitle">
              <li>• Check port availability: <code>lsof -ti:9000</code></li>
              <li>• View PM2 logs: <code>pm2 logs fi-backend-api --lines 50</code></li>
              <li>• Restart service: <code>pm2 restart fi-backend-api</code></li>
              <li>• Check Python venv: <code>source venv/bin/activate</code></li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-medium fi-text-error mb-2">Frontend can&apos;t connect to API</h4>
            <ul className="space-y-1 fi-subtitle">
              <li>• Verify .env.local: <code>cat .env.local | grep API_URL</code></li>
              <li>• Check CORS configuration in backend</li>
              <li>• Test API directly: <code>curl http://localhost:9001/api/health</code></li>
              <li>• Rebuild frontend: <code>pnpm build</code></li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-medium fi-text-error mb-2">High memory usage</h4>
            <ul className="space-y-1 fi-subtitle">
              <li>• Check PM2 status: <code>pm2 ls</code></li>
              <li>• Adjust memory limits in ecosystem.config.js</li>
              <li>• Restart services: <code>pm2 restart all</code></li>
              <li>• Monitor: <code>pm2 monit</code></li>
            </ul>
          </div>

          <Callout type="warning" title="Need Help?">
            If issues persist, check the project documentation at <code>./NAS_DEPLOYMENT.md</code> or
            create an issue on GitHub with:
            <ul className="mt-2 space-y-1 text-sm">
              <li>• PM2 logs: <code>pm2 logs --err --lines 100</code></li>
              <li>• System info: <code>node -v && python3 --version</code></li>
              <li>• Environment: <code>cat .env.local</code> (redact secrets)</li>
            </ul>
          </Callout>
        </CardContent>
      </Card>

      {/* Success State */}
      <Callout type="success" title="All Checks Passed!">
        Your Free Intelligence deployment is operational. The system is ready for use in LAN-only mode.
        <div className="mt-3 text-sm">
          Access the application at: <code>http://localhost:9000</code>
        </div>
      </Callout>
    </div>
  );
}
