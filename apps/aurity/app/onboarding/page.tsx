/**
 * Onboarding Demo Page
 *
 * Card: FI-UX-STR-001
 * Demo: http://localhost:9000/onboarding
 */

import { OnboardingFlow } from '@/components/onboarding/onboarding-flow';

export default function OnboardingPage() {
  // OnboardingFlow already uses AppTemplate internally
  return <OnboardingFlow />;
}
