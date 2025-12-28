#!/usr/bin/env node
/**
 * Migration script: Update type imports to use @aurity-standalone/types package
 * 
 * This script replaces all imports from '@/types/*' with '@aurity-standalone/types/*'
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Map of old import paths to new package exports
const IMPORT_MAPPINGS = {
  '@/types/assistant': '@aurity-standalone/types/assistant',
  '@/types/audit': '@aurity-standalone/types/audit',
  '@/types/chat': '@aurity-standalone/types/chat',
  '@/types/checkin': '@aurity-standalone/types/checkin',
  '@/types/knowledge': '@aurity-standalone/types/knowledge',
  '@/types/llm-model': '@aurity-standalone/types/llm',
  '@/types/medical': '@aurity-standalone/types/medical',
  '@/types/patient': '@aurity-standalone/types/patient',
  '@/types/persona': '@aurity-standalone/types/persona',
  '@/types/session': '@aurity-standalone/types/session',
  '@/types/voices': '@aurity-standalone/types/voices',
  '@/types/select-configs': '@/types/select-configs', // Keep this one - it's not in types package
};

function updateImports(filePath) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    let modified = false;

    Object.entries(IMPORT_MAPPINGS).forEach(([oldPath, newPath]) => {
      // Match: import ... from '@/types/assistant'
      // Match: import ... from "@/types/assistant"
      const singleQuotePattern = new RegExp(`from\\s+['"]${oldPath.replace(/\//g, '\\/')}['"]`, 'g');
      
      if (singleQuotePattern.test(content)) {
        content = content.replace(singleQuotePattern, `from '${newPath}'`);
        modified = true;
      }
    });

    if (modified) {
      fs.writeFileSync(filePath, content, 'utf8');
      console.log(`✓ Updated: ${filePath}`);
      return true;
    }
    return false;
  } catch (error) {
    console.error(`✗ Error updating ${filePath}:`, error.message);
    return false;
  }
}

function findFilesToUpdate() {
  try {
    const result = execSync(
      'find . -type f \\( -name "*.ts" -o -name "*.tsx" \\) ! -path "./node_modules/*" ! -path "./.next/*" ! -path "./packages/*" ! -path "./types/*" | xargs grep -l "@/types/" 2>/dev/null || true',
      { cwd: path.resolve(__dirname, '..'), encoding: 'utf8' }
    );
    
    return result
      .trim()
      .split('\n')
      .filter(Boolean)
      .map(f => path.resolve(__dirname, '..', f));
  } catch (error) {
    console.error('Error finding files:', error.message);
    return [];
  }
}

// Main execution
console.log('🔄 Starting type import migration...\n');

const files = findFilesToUpdate();
console.log(`Found ${files.length} files to check\n`);

let updatedCount = 0;
files.forEach(file => {
  if (updateImports(file)) {
    updatedCount++;
  }
});

console.log(`\n✅ Migration complete!`);
console.log(`   Updated: ${updatedCount} files`);
console.log(`   Unchanged: ${files.length - updatedCount} files`);
