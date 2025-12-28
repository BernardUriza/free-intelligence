// Central map for voice id -> friendly display name
// Add entries here as needed; fallback will format the identifier
const VOICE_ALIASES: Record<string, string> = {
  'es-MX-CarlosNeural': 'Carlos (es-MX)',
  'en-US-JaneV3': 'Jane (en-US)',
  'en-US-AdamV2': 'Adam (en-US)',
};

export function getVoiceDisplayName(voice?: string | null): string | null {
  if (!voice) return null;
  if (VOICE_ALIASES[voice]) return VOICE_ALIASES[voice];

  // Fallback formatting: name (locale) if matches like en-US-Name
  const parts = voice.split('-');
  if (parts.length >= 3) {
    const locale = `${parts[0]}-${parts[1]}`;
    const name = parts.slice(2).join('-');
    return `${name} (${locale})`;
  }

  return voice;
}

export default VOICE_ALIASES;
