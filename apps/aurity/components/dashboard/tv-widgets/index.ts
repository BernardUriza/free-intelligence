/**
 * TV Widgets - Modular components for Waiting Room TV
 *
 * Card: FI-UI-FEAT-TVD-001, FI-TV-002
 * Based on 2025 healthcare digital signage best practices
 *
 * Each widget is optimized for:
 * - Smart text scaling with CSS clamp() and viewport units
 * - Text legible from 3-10 meters distance
 * - Full-screen TV layouts
 */

// Time & Weather
export { WeatherWidget } from './WeatherWidget';

// Interactive Content
export { HealthTriviaWidget } from './HealthTriviaWidget';
export { BreathingExerciseWidget } from './BreathingExerciseWidget';

// Health Tips
export { DailyTipWidget } from './DailyTipWidget';

// Clinic Content
export { ClinicImageWidget } from './ClinicImageWidget';
export { ClinicVideoWidget } from './ClinicVideoWidget';
export { ClinicMessageWidget } from './ClinicMessageWidget';

// Marketing & Services
export { FeaturedServicesWidget } from './FeaturedServicesWidget';
export { PromotionBannerWidget } from './PromotionBannerWidget';
export { TestimonialWidget } from './TestimonialWidget';

// Queue & Wait Time
export { WaitTimeDisplayWidget } from './WaitTimeDisplayWidget';

// Ambient & Relaxation
export { CalmingNatureWidget } from './CalmingNatureWidget';
