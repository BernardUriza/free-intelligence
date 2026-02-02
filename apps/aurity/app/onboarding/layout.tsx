/**
 * Onboarding Layout
 *
 * This layout bypasses the ProtectedLayout (auth requirement) for onboarding.
 * The onboarding flow should be accessible without authentication.
 *
 * Card: FI-ONBOARD-REDESIGN-001
 */

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Return children directly without any auth wrapper
  // The root layout still provides ThemeProvider, etc.
  return <>{children}</>;
}
