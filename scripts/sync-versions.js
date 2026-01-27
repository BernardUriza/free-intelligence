#!/usr/bin/env node

// Version Synchronization Script
//
// Single Source of Truth: apps/*/src-tauri/tauri.conf.json
//
// This script synchronizes versions from tauri.conf.json to:
// - package.json (npm/pnpm version)
// - Cargo.toml (Rust package version)
//
// Modes:
// - --check: Validate consistency (exit 1 if mismatch)
// - --fix: Synchronize all files to tauri.conf.json
//
// Usage:
//   node scripts/sync-versions.js --check
//   node scripts/sync-versions.js --fix

const fs = require('fs');
const path = require('path');

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logError(message) {
  log(`❌ ${message}`, 'red');
}

function logSuccess(message) {
  log(`✅ ${message}`, 'green');
}

function logWarning(message) {
  log(`⚠️  ${message}`, 'yellow');
}

function logInfo(message) {
  log(`ℹ️  ${message}`, 'cyan');
}

// Project structure
const APPS = [
  {
    name: 'fi-monitor',
    tauriConfig: 'apps/fi-monitor/src-tauri/tauri.conf.json',
    packageJson: 'apps/fi-monitor/package.json',
    cargoToml: 'apps/fi-monitor/src-tauri/Cargo.toml'
  },
  {
    name: 'aurity-desktop',
    tauriConfig: 'apps/aurity-desktop/src-tauri/tauri.conf.json',
    packageJson: 'apps/aurity-desktop/package.json',
    cargoToml: 'apps/aurity-desktop/src-tauri/Cargo.toml'
  }
];

// Read version from tauri.conf.json
function readTauriVersion(configPath) {
  try {
    const content = fs.readFileSync(configPath, 'utf-8');
    const config = JSON.parse(content);
    return config.version;
  } catch (error) {
    logError(`Failed to read ${configPath}: ${error.message}`);
    return null;
  }
}

// Read version from package.json
function readPackageVersion(packagePath) {
  try {
    const content = fs.readFileSync(packagePath, 'utf-8');
    const pkg = JSON.parse(content);
    return pkg.version;
  } catch (error) {
    logError(`Failed to read ${packagePath}: ${error.message}`);
    return null;
  }
}

// Read version from Cargo.toml
function readCargoVersion(cargoPath) {
  try {
    const content = fs.readFileSync(cargoPath, 'utf-8');
    const match = content.match(/^version\s*=\s*"([^"]+)"/m);
    return match ? match[1] : null;
  } catch (error) {
    logError(`Failed to read ${cargoPath}: ${error.message}`);
    return null;
  }
}

// Update version in package.json
function updatePackageVersion(packagePath, newVersion) {
  try {
    const content = fs.readFileSync(packagePath, 'utf-8');
    const pkg = JSON.parse(content);
    pkg.version = newVersion;
    fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2) + '\n', 'utf-8');
    return true;
  } catch (error) {
    logError(`Failed to update ${packagePath}: ${error.message}`);
    return false;
  }
}

// Update version in Cargo.toml
function updateCargoVersion(cargoPath, newVersion) {
  try {
    const content = fs.readFileSync(cargoPath, 'utf-8');
    const updated = content.replace(
      /^version\s*=\s*"[^"]+"/m,
      `version = "${newVersion}"`
    );
    fs.writeFileSync(cargoPath, updated, 'utf-8');
    return true;
  } catch (error) {
    logError(`Failed to update ${cargoPath}: ${error.message}`);
    return false;
  }
}

// Check version consistency for a single app
function checkAppVersions(app) {
  const tauriVersion = readTauriVersion(app.tauriConfig);
  const packageVersion = readPackageVersion(app.packageJson);
  const cargoVersion = readCargoVersion(app.cargoToml);

  if (!tauriVersion || !packageVersion || !cargoVersion) {
    logError(`${app.name}: Failed to read versions`);
    return { ok: false, app: app.name };
  }

  const allMatch = tauriVersion === packageVersion && tauriVersion === cargoVersion;

  if (allMatch) {
    logSuccess(`${app.name}: All versions match (${tauriVersion})`);
    return { ok: true, app: app.name, version: tauriVersion };
  } else {
    logError(`${app.name}: Version mismatch detected`);
    logInfo(`  tauri.conf.json: ${tauriVersion}`);
    logInfo(`  package.json:    ${packageVersion}`);
    logInfo(`  Cargo.toml:      ${cargoVersion}`);
    return {
      ok: false,
      app: app.name,
      tauri: tauriVersion,
      package: packageVersion,
      cargo: cargoVersion
    };
  }
}

// Synchronize versions for a single app
function syncAppVersions(app) {
  const tauriVersion = readTauriVersion(app.tauriConfig);

  if (!tauriVersion) {
    logError(`${app.name}: Cannot read tauri.conf.json version`);
    return false;
  }

  logInfo(`${app.name}: Syncing to ${tauriVersion}...`);

  const packageVersion = readPackageVersion(app.packageJson);
  const cargoVersion = readCargoVersion(app.cargoToml);

  let updated = false;

  if (packageVersion !== tauriVersion) {
    logInfo(`  Updating package.json: ${packageVersion} → ${tauriVersion}`);
    if (updatePackageVersion(app.packageJson, tauriVersion)) {
      updated = true;
    } else {
      return false;
    }
  }

  if (cargoVersion !== tauriVersion) {
    logInfo(`  Updating Cargo.toml: ${cargoVersion} → ${tauriVersion}`);
    if (updateCargoVersion(app.cargoToml, tauriVersion)) {
      updated = true;
    } else {
      return false;
    }
  }

  if (updated) {
    logSuccess(`${app.name}: Synchronized to ${tauriVersion}`);
  } else {
    logInfo(`${app.name}: Already synchronized (${tauriVersion})`);
  }

  return true;
}

// Main execution
function main() {
  const args = process.argv.slice(2);
  const mode = args[0];

  if (!mode || !['--check', '--fix'].includes(mode)) {
    log('Usage:', 'bold');
    log('  node scripts/sync-versions.js --check', 'cyan');
    log('  node scripts/sync-versions.js --fix', 'cyan');
    log('', 'reset');
    log('Modes:', 'bold');
    log('  --check: Validate version consistency (exit 1 if mismatch)', 'cyan');
    log('  --fix:   Synchronize all files to tauri.conf.json', 'cyan');
    process.exit(1);
  }

  log('', 'reset');
  log('🔍 Version Synchronization Tool', 'bold');
  log('Source of Truth: apps/*/src-tauri/tauri.conf.json', 'cyan');
  log('', 'reset');

  if (mode === '--check') {
    log('Mode: Validation', 'yellow');
    log('', 'reset');

    const results = APPS.map(checkAppVersions);
    const allOk = results.every(r => r.ok);

    log('', 'reset');
    if (allOk) {
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
      logSuccess('All versions synchronized');
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
      process.exit(0);
    } else {
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'red');
      logError('Version mismatch detected');
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'red');
      log('', 'reset');
      log('Fix with:', 'yellow');
      log('  pnpm version:sync', 'cyan');
      log('', 'reset');
      process.exit(1);
    }
  }

  if (mode === '--fix') {
    log('Mode: Synchronization', 'yellow');
    log('', 'reset');

    const results = APPS.map(syncAppVersions);
    const allOk = results.every(r => r);

    log('', 'reset');
    if (allOk) {
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
      logSuccess('All versions synchronized');
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
      log('', 'reset');
      logInfo('Next steps:');
      log('  1. Review changes: git diff', 'cyan');
      log('  2. Commit: git add . && git commit -m "chore: sync versions"', 'cyan');
      log('', 'reset');
      process.exit(0);
    } else {
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'red');
      logError('Synchronization failed');
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'red');
      log('', 'reset');
      process.exit(1);
    }
  }
}

// Run
main();
