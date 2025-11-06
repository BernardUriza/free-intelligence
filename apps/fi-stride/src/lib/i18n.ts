// i18n messages en ES/EN con soporte para lectura fácil

export const messages = {
  es: {
    common: {
      welcome: 'Bienvenido a Aurity',
      continue: 'Continuar',
      back: 'Atrás',
      cancel: 'Cancelar',
      save: 'Guardar',
      close: 'Cerrar',
      loading: 'Cargando...',
      error: 'Error',
    },
    accessibility: {
      highContrast: 'Alto Contraste',
      fontSize: 'Tamaño de Letra',
      textToSpeech: 'Lectura en Voz',
      settings: 'Configuración de Accesibilidad',
      fontSizeOptions: {
        normal: 'Normal',
        large: 'Grande',
        extraLarge: 'Muy Grande',
      },
    },
    rpe: {
      label: 'Esfuerzo Percibido',
      description: 'Selecciona cómo te sientes',
      levels: {
        0: 'Descansado - Sin esfuerzo',
        1: 'Muy Fácil - Puedo hablar',
        2: 'Fácil - Respiración normal',
        3: 'Moderado - Algo cansado',
        4: 'Difícil - Difícil hablar',
        5: 'Muy Difícil - No puedo hablar',
      },
    },
    onboarding: {
      title: 'Consentimiento Informado',
      description: 'Entiendo cómo se usan mis datos',
      accept: 'Acepto',
      decline: 'No acepto',
    },
    session: {
      title: 'Sesión de Ejercicio',
      startSession: 'Iniciar Sesión',
      endSession: 'Finalizar Sesión',
      timer: 'Tiempo',
      rpe: 'Esfuerzo',
    },
  },
  en: {
    common: {
      welcome: 'Welcome to Aurity',
      continue: 'Continue',
      back: 'Back',
      cancel: 'Cancel',
      save: 'Save',
      close: 'Close',
      loading: 'Loading...',
      error: 'Error',
    },
    accessibility: {
      highContrast: 'High Contrast',
      fontSize: 'Font Size',
      textToSpeech: 'Text to Speech',
      settings: 'Accessibility Settings',
      fontSizeOptions: {
        normal: 'Normal',
        large: 'Large',
        extraLarge: 'Extra Large',
      },
    },
    rpe: {
      label: 'Rate of Perceived Exertion',
      description: 'How are you feeling?',
      levels: {
        0: 'Resting - No effort',
        1: 'Very Easy - Can talk',
        2: 'Easy - Normal breathing',
        3: 'Moderate - Getting tired',
        4: 'Hard - Hard to talk',
        5: 'Very Hard - Cannot talk',
      },
    },
    onboarding: {
      title: 'Informed Consent',
      description: 'I understand how my data is used',
      accept: 'Accept',
      decline: 'Decline',
    },
    session: {
      title: 'Exercise Session',
      startSession: 'Start Session',
      endSession: 'End Session',
      timer: 'Time',
      rpe: 'Effort',
    },
  },
};

export type Language = 'es' | 'en';

export function getMessage(lang: Language, path: string) {
  const keys = path.split('.');
  let current: any = messages[lang];

  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return path; // fallback to key path if not found
    }
  }

  return current;
}

export function useI18n(lang: Language = 'es') {
  return {
    t: (path: string) => getMessage(lang, path),
    lang,
  };
}
