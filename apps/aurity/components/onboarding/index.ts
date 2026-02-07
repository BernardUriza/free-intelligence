/**
 * Onboarding Module Index
 *
 * Card: FI-ONBOARD-REDESIGN-001
 *
 * The onboarding flow now uses ChatWidget with useOnboardingChat hook.
 * This module only exports the CompletionCelebration component.
 *
 * Usage:
 *   import { CompletionCelebration } from '@/components/onboarding';
 *
 * The main onboarding logic is in:
 *   - app/onboarding/page.tsx (uses ChatWidget)
 *   - hooks/useOnboardingChat.tsx (custom chat hook)
 */

export { CompletionCelebration } from './CompletionCelebration';
export { DesktopSetupWizard } from './DesktopSetupWizard';
