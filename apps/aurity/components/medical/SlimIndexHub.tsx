"use client";

/**
 * SlimIndexHub Component
 * Card: FI-UI-FEAT-209
 *
 * Minimal navigation hub - header + tiles + keyboard shortcuts only
 * Updated: HIPAA G-003 - Integrated UserDisplay in header
 * Updated: FI-UI-FEAT-NAV-001 - Integrated AppNavigation in header
 * Updated: 2025-12-12 - Grouped tiles by category (SaaS UX best practices)
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getRouteByShortcut, getGroupedRoutes } from "@/lib/navigation";
import { AccessTile } from "../dashboard/AccessTile";
import { AppTemplate } from "@/components/layout/AppTemplate";
import { useRBAC } from "@aurity-standalone/hooks/useRBAC";
import { Hospital, Brain, Settings, EyeOff, Lock } from "lucide-react";

// Icon mapping for categories
const CATEGORY_ICONS = {
  hospital: Hospital,
  brain: Brain,
  settings: Settings,
  'eye-off': EyeOff,
} as const;

export function SlimIndexHub() {
  const router = useRouter();
  const { isSuperAdmin } = useRBAC();
  const [onboardingCompleted, setOnboardingCompleted] = useState(false);

  // Check onboarding status (superadmins bypass onboarding requirement)
  useEffect(() => {
    const completed = localStorage.getItem('aurity_onboarding_completed') === 'true';
    setOnboardingCompleted(completed);
  }, []);

  // Superadmins have full access regardless of onboarding status
  const hasFullAccess = isSuperAdmin || onboardingCompleted;

  // Keyboard shortcuts (1-9)
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ignore if typing in input/textarea
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Number shortcuts 1-9
      if (e.key >= "1" && e.key <= "9") {
        const route = getRouteByShortcut(e.key);
        if (route) {
          e.preventDefault();
          router.push(route.href);
        }
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [router]);

  return (
    <AppTemplate
      headerConfig={{ showLogo: true, title: 'AURITY', subtitle: 'v0.1.0', showAcronym: true }}
      padding="0"
      maxWidth="full"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="min-h-screen flex flex-col">
        {/* Main Content */}
        <div className="relative flex-1 max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-16">
        {/* Onboarding Banner - Neo-minimalist glassmorphism (hidden for superadmins) */}
        {!hasFullAccess && (
          <div className="mb-8 p-6 bg-blue-950/30 backdrop-blur-xl border border-blue-800/30 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between gap-6">
              <div>
                <h3 className="text-xl font-bold text-blue-200 tracking-tight">Welcome to Aurity Framework</h3>
                <p className="text-sm fi-text/80 mt-2 font-light">Complete the quick onboarding to get started with the platform</p>
              </div>
              <a
                href="/onboarding"
                className="fi-btn-cta-lg-blue"
              >
                Start Onboarding →
              </a>
            </div>
          </div>
        )}

        {/* Medical AI Workflow - Neo-minimalist glassmorphism */}
        <div className={`mb-8 p-6 bg-emerald-950/30 backdrop-blur-xl border border-emerald-800/30 rounded-2xl shadow-lg hover:shadow-xl transition-all relative ${
          !hasFullAccess ? 'opacity-50 pointer-events-none' : ''
        }`}>
          {!hasFullAccess && (
            <div className="absolute top-3 right-3 px-3 py-1.5 bg-slate-800/80 backdrop-blur-sm border border-slate-600/50 rounded-lg text-xs fi-text font-medium shadow-md flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" />
              Complete onboarding first
            </div>
          )}
          <div className="flex items-center justify-between gap-6">
            <div>
              <h3 className="text-xl font-bold text-emerald-200 tracking-tight">Medical AI Workflow</h3>
              <p className="text-sm fi-text/80 mt-2 font-light">AI-powered medical consultation workflow with transcription</p>
            </div>
            <a
              href="/medical-ai"
              className="fi-btn-cta-lg-emerald"
            >
              Start Workflow →
            </a>
          </div>
        </div>

        {/* Navigation Tiles - Grouped by Category */}
        <div className={`space-y-8 ${
          !hasFullAccess ? 'opacity-50 pointer-events-none' : ''
        }`}>
          {getGroupedRoutes().map(({ category, routes }) => {
            const IconComponent = CATEGORY_ICONS[category.icon as keyof typeof CATEGORY_ICONS];
            return (
            <div key={category.id}>
              {/* Category Header */}
              <div className="flex items-center gap-3 mb-4">
                {IconComponent && <IconComponent className="w-6 h-6 text-slate-400" />}
                <div>
                  <h3 className="text-lg font-semibold text-slate-200">{category.label}</h3>
                  <p className="fi-text-muted">{category.description}</p>
                </div>
              </div>

              {/* Category Tiles Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {routes.filter(route => route.id !== 'onboarding').map((route) => (
                  <AccessTile key={route.id} route={route} />
                ))}
              </div>
            </div>
            );
          })}
        </div>
      </div>

      {/* Minimal Footer - Neo-minimalist glassmorphism */}
      <footer className="relative fi-border-top/50 bg-slate-900/60 backdrop-blur-xl shadow-lg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="flex items-center justify-center h-14 fi-subtitle/80 font-light tracking-wide">
            <span>Shortcuts: 1-9 to navigate</span>
          </div>
        </div>
      </footer>
      </div>
    </AppTemplate>
  );
}
