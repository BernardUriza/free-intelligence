/**
 * Standardized Gradient Utilities
 * 
 * Simplified palette matching app's slate + emerald/cyan medical theme.
 * Usage: import { gradients } from '@/lib/styles/gradients';
 */

/**
 * Core Gradients - Minimal, cohesive palette
 */
export const gradients = {
  // Primary - Medical/Success (emerald-cyan) - Main brand color
  primary: 'bg-gradient-to-r from-emerald-500 to-cyan-500',
  primaryHover: 'hover:from-emerald-600 hover:to-cyan-600',
  primaryStrong: 'bg-gradient-to-r from-emerald-600 to-cyan-600',
  primarySubtle: 'bg-gradient-to-r from-emerald-500/10 to-cyan-500/10',
  
  // Slate - Backgrounds and subtle elements
  slate: 'bg-gradient-to-r from-slate-900/90 to-slate-800/90',
  slateStrong: 'bg-gradient-to-r from-slate-900 to-slate-800',
  
  // Dividers - Transparent for separation
  divider: 'bg-gradient-to-r from-transparent via-slate-700/50 to-transparent',
  dividerReverse: 'bg-gradient-to-l from-transparent via-slate-700/50 to-transparent',
  
  // Alert - Only for critical warnings (amber-orange)
  alert: 'bg-gradient-to-r from-amber-500 to-orange-500',
  alertHover: 'hover:from-amber-600 hover:to-orange-600',
} as const;

/**
 * Gradient variants for common UI patterns
 */
export const gradientVariants = {
  // Buttons - Use primary for all CTAs
  button: {
    primary: `${gradients.primary} ${gradients.primaryHover}`,
    alert: `${gradients.alert} ${gradients.alertHover}`,
  },
  
  // Headers - Keep it simple with primary or slate
  header: {
    primary: gradients.primaryStrong,
    subtle: gradients.slate,
  },
  
  // Progress bars
  progress: gradients.primary,
  
  // Backgrounds
  background: {
    subtle: gradients.primarySubtle,
    dark: gradients.slate,
    darkStrong: gradients.slateStrong,
  },
} as const;

/**
 * Helper function to combine gradient with additional classes
 */
export function withGradient(gradientKey: keyof typeof gradients, additionalClasses = ''): string {
  return `${gradients[gradientKey]} ${additionalClasses}`.trim();
}

/**
 * Type-safe gradient keys
 */
export type GradientKey = keyof typeof gradients;
export type GradientVariant = keyof typeof gradientVariants;
