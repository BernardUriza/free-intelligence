/**
 * T21 Messages - Easy-to-read text for athletes with Down Syndrome (Trisomy 21)
 */

export const t21Messages = {
  common: {
    hello: '¡Hola, deportista! 👋',
    welcome: 'Bienvenido a Aurity',
    great: '¡Muy bien! 💪',
    excellent: '¡Excelente trabajo! 🎉',
    good: '¡Qué bien! 😊',
    done: '¡Hecho! ✅',
    continue: 'Continuar',
    start: 'Empezar',
    finish: 'Terminar',
    next: 'Siguiente',
    back: 'Atrás',
  },

  session: {
    ready: '¿Estás listo para ejercitar?',
    warmup: 'Vamos a calentar 🔥',
    exercise: 'Ahora a ejercitar 💪',
    cooldown: 'Relajémonos 😌',
    finished: '¡Sesión terminada! 🏆',
    timer: 'Tiempo',
    rest: 'Descansa un poco',
  },

  rpe: {
    label: '¿Cómo te sientes?',
    description: 'Elige una carita',
    easy: 'Fácil',
    medium: 'Normal',
    hard: 'Difícil',
    veryHard: 'Muy difícil',
  },

  feedback: {
    encouragement: '¡Vas muy bien! 🌟',
    pushHarder: 'Puedes más. Adelante! 💪',
    goodPace: 'Vas al buen ritmo 🎯',
    impressive: '¡Increíble! 🔥',
    fantastic: '¡Fantástico! 🎊',
  },

  medals: {
    bronze: 'Medalla de Bronce 🥉',
    silver: 'Medalla de Plata 🥈',
    gold: 'Medalla de Oro 🥇',
    champion: '¡Campeón! 🏆',
  },

  nutrition: {
    water: 'Bebe agua 💧',
    healthy: 'Come sano 🥗',
    rest: 'Descansa bien 😴',
    recovery: 'Recuperación 🌿',
  },

  motivational: [
    '¡Eres un campeón! 🏆',
    '¡Lo estás haciendo genial! 💪',
    '¡Sigue adelante! 🚀',
    '¡Eres increíble! ⭐',
    '¡Nunca te rindas! 💯',
    '¡Estoy orgulloso de ti! 👏',
    '¡Cada día eres mejor! 📈',
    '¡Tu esfuerzo vale la pena! 💖',
  ],
};

export function getRandomMotivation(): string {
  const messages = t21Messages.motivational;
  return messages[Math.floor(Math.random() * messages.length)];
}

export function formatSimpleTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function getAchievementMessage(durationSeconds: number, rpeScores: number[]): string {
  const avgRPE = rpeScores.length > 0 ? rpeScores.reduce((a, b) => a + b, 0) / rpeScores.length : 0;

  if (durationSeconds > 1800 && avgRPE > 3) {
    return t21Messages.medals.champion;
  }
  if (durationSeconds > 1200 && avgRPE > 2) {
    return t21Messages.medals.gold;
  }
  if (durationSeconds > 600) {
    return t21Messages.medals.silver;
  }
  return t21Messages.medals.bronze;
}
