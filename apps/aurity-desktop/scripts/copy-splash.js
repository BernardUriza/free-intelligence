#!/usr/bin/env node
/**
 * Cross-platform script to copy splashscreen.html to the frontend output directory.
 * Used by Tauri build process.
 */

const fs = require('fs');
const path = require('path');

const srcFile = path.join(__dirname, '..', 'src-tauri', 'splashscreen.html');
const destDir = path.join(__dirname, '..', '..', 'aurity', 'out');
const destFile = path.join(destDir, 'splashscreen.html');

// Ensure destination directory exists
if (!fs.existsSync(destDir)) {
    console.log(`Creating directory: ${destDir}`);
    fs.mkdirSync(destDir, { recursive: true });
}

// Copy the file
try {
    fs.copyFileSync(srcFile, destFile);
    console.log(`Copied splashscreen.html to ${destFile}`);
} catch (err) {
    console.error(`Failed to copy splashscreen: ${err.message}`);
    process.exit(1);
}
