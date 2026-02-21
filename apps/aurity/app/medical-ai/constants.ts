/**
 * Medical AI Workflow - Constants
 *
 * Static data extracted from the page component.
 */

/** Keywords scanned in session previews for medical context badges */
export const MEDICAL_KEYWORDS = [
  'hipertensión', 'diabetes', 'asma', 'artritis', 'migraña',
  'alergia', 'penicilina', 'dolor', 'fiebre', 'tos',
  'gripe', 'covid', 'presión', 'glucosa', 'colesterol',
] as const;

/**
 * Extract medical keywords found in a text preview.
 * Returns at most 3 capitalised matches.
 */
export function extractMedicalInfo(preview: string): string[] {
  const found = new Set<string>();
  const lower = preview.toLowerCase();

  for (const kw of MEDICAL_KEYWORDS) {
    if (lower.includes(kw)) {
      found.add(kw.charAt(0).toUpperCase() + kw.slice(1));
    }
  }

  return Array.from(found).slice(0, 3);
}
