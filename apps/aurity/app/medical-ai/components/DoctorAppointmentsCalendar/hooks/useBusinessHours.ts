/**
 * useBusinessHours
 *
 * Transforms a DoctorAvailability's weeklySchedule into
 * FullCalendar's businessHours format.
 */

import { useMemo } from 'react';
import type { DoctorAvailability } from '@/components/admin/clinics/availability-designer/types';

const DEFAULT_BUSINESS_HOURS = {
  daysOfWeek: [1, 2, 3, 4, 5],
  startTime: '09:00',
  endTime: '18:00',
} as const;

export function useBusinessHours(availability?: DoctorAvailability | null) {
  return useMemo(() => {
    if (!availability?.weeklySchedule?.length) {
      return DEFAULT_BUSINESS_HOURS;
    }

    return availability.weeklySchedule.map((slot) => ({
      daysOfWeek: [slot.day],
      startTime: slot.start,
      endTime: slot.end,
    }));
  }, [availability?.weeklySchedule]);
}
