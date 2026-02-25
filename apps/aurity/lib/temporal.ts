import '@/polyfills';

declare const Temporal: any;

const DEFAULT_TZ = 'America/Mexico_City';

function validateTimeZone(value: string): string {
  try {
    Temporal.TimeZone.from(value);
    return value;
  } catch (error) {
    const message = `CLINIC_TZ must be a valid IANA zone (received "${value}")`;
    if (process.env.NODE_ENV === 'production') {
      throw new Error(message);
    }
    // Invalid timezone — falling back to default
    return DEFAULT_TZ;
  }
}

function resolveClinicTimeZone(): string {
  const envZone = process.env.CLINIC_TZ || process.env.NEXT_PUBLIC_CLINIC_TZ;

  if (!envZone) {
    return DEFAULT_TZ;
  }

  return validateTimeZone(envZone);
}

export function getClinicTimeZone(): string {
  return resolveClinicTimeZone();
}

export const TemporalAPI = Temporal;
