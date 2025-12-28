#!/usr/bin/env node
/**
 * Migration script: Update imports to use standalone packages
 * 
 * This script updates imports from:
 * - @/lib/api/* → @aurity-standalone/api-client/*
 * - @/hooks/* → @aurity-standalone/hooks/*
 * - app/medical-ai/* → @aurity-standalone/medical/*
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Map of old import paths to new package exports
const IMPORT_MAPPINGS = {
  // API client mappings
  "@/lib/api/assistant": "@aurity-standalone/api-client/assistant",
  "@/lib/api/personas": "@aurity-standalone/api-client/personas",
  "@/lib/api/llm-models": "@aurity-standalone/api-client/llm-models",
  "@/lib/api/knowledge": "@aurity-standalone/api-client/knowledge",
  "@/lib/api/checkin": "@aurity-standalone/api-client/checkin",
  "@/lib/api/chat-history": "@aurity-standalone/api-client/chat-history",
  "@/lib/api/timeline": "@aurity-standalone/api-client/timeline",
  "@/lib/api/kpis": "@aurity-standalone/api-client/kpis",
  "@/lib/api/medical-workflow": "@aurity-standalone/api-client/medical-workflow",
  "@/lib/api/exports": "@aurity-standalone/api-client/exports",
  "@/lib/api/backend-health": "@aurity-standalone/api-client/backend-health",
  "@/lib/api/client": "@aurity-standalone/api-client",
  
  // Hooks mappings
  "@/hooks/useAuth": "@aurity-standalone/hooks/useAuth",
  "@/hooks/useRBAC": "@aurity-standalone/hooks/useRBAC",
  "@/hooks/useChat": "@aurity-standalone/hooks/useChat",
  "@/hooks/useFIConversation": "@aurity-standalone/hooks/useFIConversation",
  "@/hooks/useCheckinConversation": "@aurity-standalone/hooks/useCheckinConversation",
  "@/hooks/usePersonas": "@aurity-standalone/hooks/usePersonas",
  "@/hooks/useRecorder": "@aurity-standalone/hooks/useRecorder",
  "@/hooks/useTranscription": "@aurity-standalone/hooks/useTranscription",
  "@/hooks/useChatUpload": "@aurity-standalone/hooks/useChatUpload",
  "@/hooks/useMessageGroups": "@aurity-standalone/hooks/useMessageGroups",
  "@/hooks/useOptimisticMessages": "@aurity-standalone/hooks/useOptimisticMessages",
  "@/hooks/useEmotionalContext": "@aurity-standalone/hooks/useEmotionalContext",
  
  // Medical mappings
  "app/medical-ai/WorkflowSteps": "@aurity-standalone/medical/WorkflowSteps",
  "app/medical-ai/usePatientManagement": "@aurity-standalone/medical/usePatientManagement",
  "app/medical-ai/useSessionManagement": "@aurity-standalone/medical/useSessionManagement",
  "@/app/medical-ai/WorkflowSteps": "@aurity-standalone/medical/WorkflowSteps",
  "@/app/medical-ai/usePatientManagement": "@aurity-standalone/medical/usePatientManagement",
  "@/app/medical-ai/useSessionManagement": "@aurity-standalone/medical/useSessionManagement",
};

function updateImports(filePath) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    let modified = false;

    Object.entries(IMPORT_MAPPINGS).forEach(([oldPath, newPath]) => {
      // Match both single and double quotes
      const pattern = new RegExp(`from\\s+['"]${oldPath.replace(/\//g, '\\/')}['"]`, 'g');
      
      if (pattern.test(content)) {
        content = content.replace(pattern, `from '${newPath}'`);
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
      'find . -type f \\( -name "*.ts" -o -name "*.tsx" \\) ! -path "./node_modules/*" ! -path "./.next/*" ! -path "./packages/*" | xargs grep -l -E "@/lib/api/|@/hooks/|app/medical-ai/" 2>/dev/null || true',
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
console.log('🔄 Starting import migration to standalone packages...\n');

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
