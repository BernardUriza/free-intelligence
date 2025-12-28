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
    console.warn(`[temporal] ${message}. Falling back to ${DEFAULT_TZ}.`, { error });
    return DEFAULT_TZ;
  }
}

function resolveClinicTimeZone(): string {
  const envZone = process.env.CLINIC_TZ || process.env.NEXT_PUBLIC_CLINIC_TZ;

  if (!envZone) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('CLINIC_TZ is required in production. Set a valid IANA time zone.');
    }
    console.warn(`[temporal] CLINIC_TZ missing; using default ${DEFAULT_TZ} for dev/demo.`);
    return DEFAULT_TZ;
  }

  return validateTimeZone(envZone);
}

export function getClinicTimeZone(): string {
  return resolveClinicTimeZone();
}

export const TemporalAPI = Temporal;
