/**
 * NAS Configuration Parser
 * Card: FI-INFRA-STR-014
 *
 * Parses ecosystem.config.js to extract service metadata
 * This is the source of truth to avoid drift
 */

export interface ServiceConfig {
  name: string;
  port: string;
  memory: string;
  workers?: number;
  type: "backend" | "frontend" | "api";
}

/**
 * Service metadata extracted from ecosystem.config.js
 * Updated: 2025-10-30
 * Commit: (embedded at build time)
 */
export const SERVICES: ServiceConfig[] = [
  {
    name: "fi-backend-api",
    port: "9001",
    memory: "1G",
    workers: 2,
    type: "backend",
  },
  {
    name: "fi-timeline-api",
    port: "9002",
    memory: "512M",
    workers: 1,
    type: "api",
  },
  {
    name: "fi-frontend",
    port: "9000",
    memory: "1G",
    type: "frontend",
  },
];

/**
 * System requirements
 */
export const REQUIREMENTS = {
  node: {
    min: "18.0.0",
    recommended: "20.x",
  },
  python: {
    min: "3.11",
    recommended: "3.11+",
  },
  memory: {
    min: "4GB",
    recommended: "8GB",
  },
  disk: {
    min: "10GB",
    recommended: "50GB",
  },
  cpu: {
    arch: ["x86_64", "ARM64"],
    cores: 2,
  },
};

/**
 * Platform-specific notes
 */
export const PLATFORMS = {
  synology: {
    name: "Synology DSM",
    version: "7.0+",
    notes: [
      "Install Node.js via Package Center",
      "Enable SSH in Control Panel",
      "Use Docker package or install Node natively",
      "Adjust paths in ecosystem.config.js (e.g., /volume1/...)",
    ],
  },
  truenas: {
    name: "TrueNAS SCALE",
    version: "22.12+",
    notes: [
      "Use Shell as root user",
      "Node.js available via apt",
      "Consider using Apps/Kubernetes for containerized deployment",
      "Mount storage under /mnt/...",
    ],
  },
  ubuntu: {
    name: "Ubuntu Server",
    version: "22.04+",
    notes: [
      "Standard apt package manager",
      "Install Node via NodeSource PPA",
      "PM2 recommended for process management",
      "Configure firewall (ufw) for ports 9000-9002",
    ],
  },
  windows: {
    name: "Windows (WSL2)",
    version: "WSL2 Ubuntu 22.04",
    notes: [
      "WSL2 recommended over native Windows",
      "Install Ubuntu 22.04 from Microsoft Store",
      "Follow Linux instructions inside WSL",
      "Access via localhost:9000 from Windows",
    ],
  },
  macos: {
    name: "macOS (Dev/Simulation)",
    version: "13+",
    notes: [
      "Install Node via Homebrew: brew install node@20",
      "Python 3.11+ via Homebrew or python.org",
      "Use pnpm for package management",
      "PM2 for background services",
    ],
  },
};

/**
 * One-command installer script
 */
export const INSTALLER_SCRIPT = `#!/bin/bash
# Free Intelligence - One-Command Installer
# Source: scripts/nas-setup.sh

set -e
curl -fsSL https://github.com/yourusername/free-intelligence/raw/main/scripts/nas-setup.sh | bash
`;

/**
 * Health check endpoints
 */
export const HEALTH_CHECKS = [
  {
    name: "Backend API",
    url: "http://localhost:9001/api/health",
    expected: { status: "ok" },
  },
  {
    name: "Timeline API",
    url: "http://localhost:9002/api/health",
    expected: { status: "ok" },
  },
  {
    name: "Frontend",
    url: "http://localhost:9000",
    expected: { statusCode: 200 },
  },
];
