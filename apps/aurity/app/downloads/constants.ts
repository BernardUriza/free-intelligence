import {
  Lock,
  Zap,
  Shield,
  Mic,
  FileText,
  Brain,
  ClipboardCheck,
} from 'lucide-react';

import type { Benefit, FAQ, DemoStep, SystemRequirements } from './types';

export const BENEFITS: Benefit[] = [
  {
    icon: Lock,
    title: 'Privacidad Total',
    description: 'Tus pacientes nunca tocan internet. Cada consulta queda en tu computadora.',
    stat: '0 datos en la nube',
  },
  {
    icon: Zap,
    title: 'Rapidez Extrema',
    description: 'Genera notas SOAP completas en segundos, no en minutos de dictado.',
    stat: 'Notas en segundos',
  },
  {
    icon: Shield,
    title: 'Control Absoluto',
    description: 'IA potente sin pagar $20/mes. Cumple HIPAA sin esfuerzo extra.',
    stat: 'Sin suscripciones',
  },
];

export const FAQS: FAQ[] = [
  {
    question: '¿Necesito internet para usarlo?',
    answer: 'No. Aurity Desktop funciona 100% offline. La IA corre en tu computadora usando Ollama. Puedes usarlo en consultorios sin conexión.',
  },
  {
    question: '¿Mis datos de pacientes están seguros?',
    answer: 'Absolutamente. Ningún dato sale de tu computadora. No hay servidores externos, no hay nube, no hay transmisión. Todo se almacena localmente con encriptación.',
  },
  {
    question: '¿Cuánto cuesta?',
    answer: 'El programa piloto es gratuito. Estamos buscando médicos que nos den feedback. Después del piloto, será una licencia única (sin suscripción mensual).',
  },
  {
    question: '¿Funciona con mi especialidad médica?',
    answer: 'Sí. Aurity se adapta a cualquier especialidad: medicina general, pediatría, ginecología, cardiología, etc. El modelo de IA entiende terminología médica en español.',
  },
  {
    question: 'Windows me dice que no tiene permisos o bloquea la instalación, ¿qué hago?',
    answer: 'Esto sucede porque el instalador aún no tiene firma digital de Microsoft (estamos en fase piloto). Para instalarlo: 1) Si aparece "Windows protegió su PC" (SmartScreen), haz clic en "Más información" y luego en "Ejecutar de todas formas". 2) Si tu antivirus lo bloquea, agrega una excepción temporal para el archivo descargado. 3) Si estás en una PC corporativa y necesitas permisos de administrador, pide a tu equipo de TI que autorice la instalación — Aurity se instala en tu carpeta de usuario y no modifica archivos del sistema.',
  },
  {
    question: 'Mi antivirus bloquea Aurity, ¿es seguro?',
    answer: 'Sí, es completamente seguro. Los antivirus a veces marcan aplicaciones nuevas o sin firma digital como sospechosas (falso positivo). Aurity Desktop es código abierto y se instala solo en tu carpeta de usuario. Puedes agregar una excepción en tu antivirus para la carpeta de Aurity.',
  },
];

export const DEMO_STEPS: DemoStep[] = [
  {
    id: 'dictation',
    icon: Mic,
    label: 'Dictado',
    duration: '2s',
    description: 'El médico habla naturalmente',
  },
  {
    id: 'transcription',
    icon: FileText,
    label: 'Transcripción',
    duration: '1.5s',
    description: 'Voz a texto en tiempo real',
  },
  {
    id: 'analysis',
    icon: Brain,
    label: 'Análisis IA',
    duration: '3s',
    description: 'Extracción de datos clínicos',
  },
  {
    id: 'soap',
    icon: ClipboardCheck,
    label: 'Nota SOAP',
    duration: 'Listo',
    description: 'Nota estructurada lista',
  },
];

/** Step animation durations in ms (maps to DEMO_STEPS order). */
export const STEP_DURATIONS_MS = [2000, 1500, 3000, 1500] as const;

export const SYSTEM_REQUIREMENTS: Record<string, SystemRequirements> = {
  macos: {
    os: 'macOS 12.0 (Monterey) o posterior',
    cpu: 'Apple Silicon (M1/M2/M3) o Intel',
    ram: '8 GB mínimo, 16 GB recomendado',
    disk: '10 GB de espacio libre',
  },
  windows: {
    os: 'Windows 10 (64-bit) o Windows 11',
    cpu: 'Procesador x86_64',
    ram: '8 GB mínimo, 16 GB recomendado',
    disk: '10 GB de espacio libre',
  },
  linux: {
    os: 'Ubuntu 22.04 LTS o compatible',
    cpu: 'Procesador x86_64',
    ram: '8 GB mínimo, 16 GB recomendado',
    disk: '10 GB de espacio libre',
  },
};
