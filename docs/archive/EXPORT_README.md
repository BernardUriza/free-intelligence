# Export Demo Evidence Script

> **Sprint SPR-2025W44** - Generate timestamped evidence of demo execution
> Version: 0.1.0

## Overview

Automated script that executes the 3 core cases (V/A/R) and generates timestamped evidence reports in JSON and Markdown formats.

**NO PHI** - All data is synthetic IoT sensor data only.

## Features

- ✅ Executes all 3 cases automatically
- ✅ Timestamps for each step
- ✅ Detailed step-by-step evidence
- ✅ JSON export (machine-readable)
- ✅ Markdown export (human-readable)
- ✅ Error capture and reporting
- ✅ NO PHI verification

## Usage

### Run the Export Script

```bash
# From project root
npx ts-node aurity/scripts/export-demo-evidence.ts
```

### Output

The script creates an `evidence/` directory with two files:

```
evidence/
├── demo-evidence-{timestamp}.json    # Machine-readable evidence
└── demo-evidence-{timestamp}.md      # Human-readable evidence
```

## Evidence Structure

### JSON Format

```json
{
  "sprint": "SPR-2025W44",
  "executionDate": "2025-10-28T...",
  "timestamp": 1730088000000,
  "version": "0.1.0",
  "cases": {
    "casoV": { ... },
    "casoA": { ... },
    "casoR": { ... }
  },
  "summary": {
    "totalDuration": 1234,
    "allCasesPassed": true,
    "noPhiVerified": true
  }
}
```

### Case Evidence Structure

Each case includes:

```typescript
{
  name: string;                    // Case name
  status: 'PASSED' | 'FAILED';    // Overall status
  startTime: number;              // Unix timestamp
  endTime: number;                // Unix timestamp
  duration: number;               // Milliseconds
  steps: StepEvidence[];          // Detailed steps
  errors: string[];               // Error messages if any
}
```

### Step Evidence Structure

Each step includes:

```typescript
{
  step: number;                   // Step number
  description: string;            // Step description
  timestamp: number;              // Unix timestamp
  status: 'SUCCESS' | 'FAILED';  // Step status
  details?: any;                  // Step-specific data
  error?: string;                 // Error message if failed
}
```

## Cases Executed

### Caso V: VERIFICAR - Authentication & Integrity

1. Initialize Authentication System
2. Login as Admin (Omnipotent)
3. Verify Admin Permissions
4. Review Audit Logs

### Caso A: ALMACENAR - Storage System

1. Initialize Storage System
2. Store Temperature Data (FI-Cold)
3. Store Humidity Data (FI-Cold)
4. Store Access Log Data (FI-Entry)
5. Store Equipment Status (FI-Assets)
6. Review Storage Statistics

### Caso R: RECUPERAR - Retrieve & Validate

1. List Available Buffers
2. Verify Integrity of All Buffers
3. Final Storage Statistics

## Example Output (Markdown)

```markdown
# Aurity Framework - Demo Evidence Report

**Sprint:** SPR-2025W44
**Execution Date:** 2025-10-28T10:30:45.123Z
**Version:** 0.1.0
**Total Duration:** 1234ms

## Summary

- **All Cases Passed:** ✅ YES
- **NO PHI Verified:** ✅ YES

## CASO V: VERIFICAR - Authentication & Integrity

**Status:** PASSED
**Duration:** 345ms

### Steps:

1. **Initialize Authentication System** - SUCCESS
   ```json
   {
     "message": "AuthManager initialized"
   }
   ```

2. **Login as Admin (Omnipotent)** - SUCCESS
   ```json
   {
     "user": "admin@aurity.local",
     "role": "admin",
     "permissions": 8
   }
   ```

...
```

## Console Output

When running the script, you'll see:

```
🚀 AURITY FRAMEWORK - Generating Demo Evidence
Sprint: SPR-2025W44
Execution Time: 2025-10-28T10:30:45.123Z

📋 Executing Case V (Verificar)...
   ✅ CASO V: VERIFICAR - Authentication & Integrity

📋 Executing Case A (Almacenar)...
   ✅ CASO A: ALMACENAR - Storage System

📋 Executing Case R (Recuperar)...
   ✅ CASO R: RECUPERAR - Retrieve & Validate

📊 Summary:
   Total Duration: 1234ms
   All Cases Passed: ✅ YES
   NO PHI Verified: ✅ YES

✅ JSON Evidence exported to: /path/to/evidence/demo-evidence-1730088045123.json
✅ Markdown Evidence exported to: /path/to/evidence/demo-evidence-1730088045123.md

🎉 Evidence export completed successfully!
```

## NO PHI Verification

The script verifies NO PHI by:

1. **Data Source:** All test data is synthetic IoT sensor data
2. **Buffer Types:** Only non-PHI buffer types used:
   - TEMPERATURE
   - HUMIDITY
   - ACCESS_LOG
   - EQUIPMENT_STATUS
3. **Tags:** All buffers tagged with 'no-phi'
4. **Content:** No patient names, IDs, SSN, or other identifiers

### Example Synthetic Data

```json
{
  "sensorId": "FRIDGE-001",
  "temperature": 4.2,
  "unit": "celsius"
}
```

**NO** patient information:
- ❌ Patient names
- ❌ Patient IDs
- ❌ SSN or driver's license
- ❌ Medical record numbers
- ❌ Addresses or phone numbers

## Storage Location

Evidence files are stored in:
```
{project-root}/evidence/
```

Temporary demo storage:
```
/tmp/aurity-demo-evidence/storage/
```

## Use Cases

### 1. Sprint Review

Generate evidence before sprint review:

```bash
npx ts-node aurity/scripts/export-demo-evidence.ts
```

Share the Markdown file with stakeholders.

### 2. Compliance Documentation

Use the timestamped evidence for compliance audits.

### 3. CI/CD Integration

```bash
# In CI pipeline
npm run demo:evidence || exit 1
```

### 4. Automated Testing

```typescript
import { generateEvidenceReport } from './aurity/scripts/export-demo-evidence';

test('All demo cases pass', async () => {
  const evidence = await generateEvidenceReport();
  expect(evidence.summary.allCasesPassed).toBe(true);
  expect(evidence.summary.noPhiVerified).toBe(true);
});
```

## Troubleshooting

### Error: Cannot find module

Ensure you're running from project root:

```bash
cd /path/to/aurity
npx ts-node aurity/scripts/export-demo-evidence.ts
```

### Error: EACCES /tmp/aurity-demo-evidence

Create directory with correct permissions:

```bash
mkdir -p /tmp/aurity-demo-evidence
chmod 755 /tmp/aurity-demo-evidence
```

### Error: Module not found

Install dependencies:

```bash
npm install
```

## Script Exits

- **Exit 0:** All cases passed, evidence exported successfully
- **Exit 1:** Export failed (see error message)

## Integration with package.json

Add to `package.json`:

```json
{
  "scripts": {
    "demo:evidence": "ts-node aurity/scripts/export-demo-evidence.ts"
  }
}
```

Then run:

```bash
npm run demo:evidence
```

---

**Version:** 0.1.0
**Sprint:** SPR-2025W44
**Status:** Production Ready
**Last Updated:** 2025-10-28
