#!/usr/bin/env node
/**
 * Conditional Frontend Build Script
 *
 * Builds the frontend only if it hasn't been pre-built.
 * This allows the CI/CD to build frontend once and reuse across platforms.
 *
 * Usage:
 *   node build-frontend-if-needed.js
 *
 * Logic:
 *   - If apps/aurity/out/ exists with content: SKIP (frontend pre-built)
 *   - If apps/aurity/out/ empty or missing: BUILD (normal flow)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const FRONTEND_OUT = path.join(__dirname, '../../aurity/out');

function checkPreBuilt() {
  try {
    const stats = fs.statSync(FRONTEND_OUT);
    if (stats.isDirectory()) {
      const files = fs.readdirSync(FRONTEND_OUT);
      if (files.length > 0) {
        console.log('✅ Frontend already pre-built (found in apps/aurity/out/)');
        console.log(`   ${files.length} files detected - skipping build`);
        return true;
      }
    }
  } catch (err) {
    // Directory doesn't exist
  }
  return false;
}

function buildFrontend() {
  console.log('🔨 Building frontend (apps/aurity/out/ not found)...');
  try {
    // Run the normal build command
    execSync('pnpm --filter aurity build && node scripts/copy-splash.js', {
      cwd: path.join(__dirname, '..'),
      stdio: 'inherit'
    });
    console.log('✅ Frontend build complete');
  } catch (error) {
    console.error('❌ Frontend build failed:', error.message);
    process.exit(1);
  }
}

// Main
if (checkPreBuilt()) {
  console.log('⏭️  Skipping frontend build (using pre-built artifact)');
  process.exit(0);
} else {
  buildFrontend();
  process.exit(0);
}
