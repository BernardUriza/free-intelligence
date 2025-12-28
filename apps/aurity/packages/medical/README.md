# @aurity-standalone/medical

Medical workflow components and utilities for Aurity healthcare platform.

## Installation

```bash
pnpm add @aurity-standalone/medical
```

## Usage

```typescript
import { 
  WorkflowSteps, 
  usePatientManagement, 
  useSessionManagement 
} from '@aurity-standalone/medical';

function MedicalWorkflow() {
  const { currentPatient, selectPatient } = usePatientManagement();
  const { sessions, loadSessions } = useSessionManagement(currentPatient?.id);
  
  return (
    <WorkflowSteps 
      patient={currentPatient}
      onStepChange={(step) => console.log('Step:', step)}
    />
  );
}
```

## Features

- ✅ SOAP note generation
- ✅ Medical workflow orchestration
- ✅ Patient & session management hooks
- ✅ Encounter tracking
- ✅ Clinical order management
- ✅ HIPAA-compliant (no PHI in logs)
- ✅ Type-safe with TypeScript

## Workflow Steps

1. **Escuchar** - Listen to patient (audio recording)
2. **Revisar** - Review transcription and diarization
3. **Notas** - Clinical notes (SOAP format)
4. **Evidencia** - Evidence pack generation
5. **Órdenes** - Orders (labs, imaging, prescriptions)
6. **Resumen** - Summary and completion

## Available Exports

- **WorkflowSteps** - Main workflow step configuration
- **usePatientManagement** - Patient selection and management
- **useSessionManagement** - Session loading and status tracking

## License

MIT
