/**
 * Bryntum Patch Hook
 *
 * This module exposes a global validation function that the patched
 * Bryntum JS calls to validate working hours.
 *
 * The patch in schedulerpro.wc.module.js calls:
 *   window.__FI_VALIDATE_WORKING_TIME__(resourceId, date)
 *
 * This hook connects that call to our isDateInWorkingHours function.
 *
 * Card: FI-BRYNTUM-CSS-001
 */

import type { Doctor } from './appointment-transform.utils';
import { isDateInWorkingHours } from './working-hours.resolver';

// Global type declaration
declare global {
  interface Window {
    __FI_VALIDATE_WORKING_TIME__?: (resourceId: string, date: Date) => boolean;
    __FI_DOCTORS_CACHE__?: Doctor[];
  }
}

/**
 * Initialize the Bryntum patch hook with doctor data
 *
 * Call this when doctors are loaded to enable working hours validation.
 *
 * @param doctors - Array of doctors with working hours configuration
 */
export function initBryntumPatchHook(doctors: Doctor[]): void {
  // Cache doctors for validation
  window.__FI_DOCTORS_CACHE__ = doctors;

  // Expose validation function
  window.__FI_VALIDATE_WORKING_TIME__ = (resourceId: string, date: Date): boolean => {
    const doctor = window.__FI_DOCTORS_CACHE__?.find(d => d.doctor_id === resourceId);

    if (!doctor) {
      console.warn(`[FI Patch] Doctor not found: ${resourceId}`);
      return true; // Allow if doctor not found (shouldn't happen)
    }

    const isAllowed = isDateInWorkingHours(doctor, date);

    if (!isAllowed) {
      console.log(
        `[FI Patch] Blocked at ${date.toISOString()} - outside working hours for ${doctor.display_name || doctor.nombre}`
      );
    }

    return isAllowed;
  };

  console.log(`[FI Patch] Initialized with ${doctors.length} doctors`);
}

/**
 * Update the cached doctors (call when doctors change)
 */
export function updateDoctorsCache(doctors: Doctor[]): void {
  window.__FI_DOCTORS_CACHE__ = doctors;
}

/**
 * Cleanup the hook (call on unmount)
 */
export function cleanupBryntumPatchHook(): void {
  delete window.__FI_VALIDATE_WORKING_TIME__;
  delete window.__FI_DOCTORS_CACHE__;
}
