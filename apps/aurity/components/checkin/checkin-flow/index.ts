/**
 * CheckinFlow Module
 *
 * Orchestrates the full check-in flow on patient's mobile device.
 *
 * Modular structure:
 * - types.ts: TypeScript interfaces (FlowState, IdentificationMethod)
 * - hooks/: useCheckinFlow (all state and handlers)
 * - components/: Step components (Identification, ConfirmIdentity, PendingActions, Success)
 */

export { CheckinFlow, default } from './CheckinFlow';
export type { CheckinFlowProps, IdentificationMethod, FlowState } from './types';
