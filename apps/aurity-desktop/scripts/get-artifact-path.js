#!/usr/bin/env node
/**
 * Get Artifact Path - Dynamic version resolution for CI/CD
 *
 * Usage:
 *   node get-artifact-path.js <app> <target-triple> <type>
 *
 * Examples:
 *   node get-artifact-path.js aurity aarch64-apple-darwin dmg
 *   node get-artifact-path.js fi-monitor x86_64-pc-windows-msvc nsis
 *
 * Output (JSON):
 *   {
 *     "version": "1.0.0",
 *     "productName": "Aurity",
 *     "file": "Aurity_1.0.0_aarch64.dmg",
 *     "path": "src-tauri/target/.../bundle/dmg/Aurity_1.0.0_aarch64.dmg",
 *     "sig": "src-tauri/target/.../bundle/dmg/Aurity_1.0.0_aarch64.dmg.sig"
 *   }
 */

const fs = require('fs');
const path = require('path');

const [,, app, triple, type] = process.argv;

if (!app || !triple || !type) {
  console.error('Usage: node get-artifact-path.js <app> <target-triple> <type>');
  console.error('Example: node get-artifact-path.js aurity aarch64-apple-darwin dmg');
  process.exit(1);
}

// Encontrar el root del repo (buscar hacia arriba hasta encontrar package.json con workspaces)
function findRepoRoot(startDir) {
  let currentDir = startDir;
  while (currentDir !== path.parse(currentDir).root) {
    const packagePath = path.join(currentDir, 'package.json');
    if (fs.existsSync(packagePath)) {
      try {
        const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
        // Si tiene workspaces, es el root del monorepo
        if (pkg.workspaces) {
          return currentDir;
        }
      } catch (e) {
        // Ignorar errores de parsing
      }
    }
    currentDir = path.dirname(currentDir);
  }
  return null;
}

const repoRoot = findRepoRoot(__dirname) || process.cwd();

// Mapeo de apps a configuraciones (paths relativos al repo root)
const configs = {
  'fi-monitor': path.join(repoRoot, 'apps/fi-monitor/src-tauri/tauri.conf.json'),
  'aurity': path.join(repoRoot, 'apps/aurity-desktop/src-tauri/tauri.conf.json')
};

const configPath = configs[app];
if (!configPath) {
  console.error(`Unknown app: ${app}. Valid apps: ${Object.keys(configs).join(', ')}`);
  process.exit(1);
}

// Leer configuración de Tauri
let config;
try {
  const configContent = fs.readFileSync(configPath, 'utf8');
  config = JSON.parse(configContent);
} catch (error) {
  console.error(`Failed to read config at ${configPath}: ${error.message}`);
  process.exit(1);
}

const { version, productName } = config;

if (!version || !productName) {
  console.error('Missing version or productName in tauri.conf.json');
  process.exit(1);
}

// Mapeo de tipos de artifact a nombres de archivo
const artifacts = {
  nsis: `${productName}_${version}_x64-setup.exe`,
  dmg: `${productName}_${version}_aarch64.dmg`,
  appimage: `${productName}_${version}_amd64.AppImage`
};

// Mapeo de tipos de artifact a paths base
const basePaths = {
  nsis: `src-tauri/target/${triple}/release/bundle/nsis`,
  dmg: `src-tauri/target/${triple}/release/bundle/dmg`,
  appimage: `src-tauri/target/${triple}/release/bundle/appimage`
};

if (!artifacts[type] || !basePaths[type]) {
  console.error(`Unknown artifact type: ${type}. Valid types: ${Object.keys(artifacts).join(', ')}`);
  process.exit(1);
}

const file = artifacts[type];
const artifactPath = `${basePaths[type]}/${file}`;
const sigPath = `${artifactPath}.sig`;

// Output como JSON
const output = {
  version,
  productName,
  file,
  path: artifactPath,
  sig: sigPath
};

console.log(JSON.stringify(output, null, 2));
