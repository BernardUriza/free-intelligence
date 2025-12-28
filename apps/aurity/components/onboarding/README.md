# Onboarding Domain

This module implements a cohesive onboarding flow for the AURITY application using a declarative orchestration pattern.

## Structure

- `types/`: Type definitions and contracts
- `steps/`: Individual step components (presentational)
- `flow/`: Main flow orchestrator
- `hooks/`: State management and business logic
- `services/`: Side-effect services (HDF5, export, etc.)
- `tests/`: Unit and integration tests

## Adding a New Step

1. Define the step ID in `types/index.ts` under `Phase`
2. Add the step to `phaseOrder` in `hooks/useOnboardingFlow.ts`
3. Create a new step component in `steps/`
4. Add the step definition to `stepDefinitions` in the hook
5. Export the component in `steps/index.ts`

Example:

```typescript
// 1. Add to Phase type
export type Phase = "welcome" | "survey" | "new_step" | ...

// 2. Add to phaseOrder
const phaseOrder: Phase[] = ["welcome", "survey", "new_step", ...];

// 3. Create NewStep.tsx
export function NewStep({ context, callbacks, status }: StepProps) {
  return <div>New Step Content</div>;
}

// 4. Add to stepDefinitions
{
  id: "new_step",
  component: NewStep,
  canProceed: (context) => true, // validation logic
  title: "New Step",
  description: "Description",
}

// 5. Export in index
export { NewStep } from "./NewStep";
```

## State Machine

The flow uses a simple state machine with phases in order. Each step receives:

- `context`: Shared state (survey, patient, etc.)
- `callbacks`: Navigation and update functions
- `status`: Busy/error state

## Services

Side effects are isolated in services:

- `HDF5Service`: HDF5 file operations
- Future: ExportService, SimulationService, etc.

## Chat Components

Chat UI is deduplicated where possible. Shared components are used from `@/components/chat/`. Onboarding-specific components remain in this module.