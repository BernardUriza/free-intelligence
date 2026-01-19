const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const configPath = path.join(__dirname, '../src-tauri/tauri.conf.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

// Get version from args or git
const version = process.argv[2] || `0.0.0-${execSync('git rev-parse --short HEAD').toString().trim()}`;

config.version = version;
fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n');
console.log(`✅ Set version to ${version}`);
