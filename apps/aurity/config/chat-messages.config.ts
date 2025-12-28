/**
 * Chat Messages Configuration
 *
 * Centralized content and settings for ChatWidgetMessages components
 * Following 4pt grid system and accessibility best practices
 */

/**
 * Empty State Configuration
 */
export const emptyStateConfig = {
  emoji: '💬',
  welcomeTitle: (userName?: string) => `Hola ${userName || 'Doctor'} 👋`,
  welcomeSubtitle: 'Soy tu asistente de Free Intelligence. Puedo ayudarte con:',
  features: [
    {
      icon: '✓',
      text: 'Consultas sobre pacientes y expedientes',
    },
    {
      icon: '✓',
      text: 'Generación de notas clínicas (SOAP)',
    },
    {
      icon: '✓',
      text: 'Análisis de datos médicos',
    },
  ],
  ctaText: 'Escribe tu pregunta abajo para comenzar...',
};

/**
 * Loading State Configuration
 */
export const loadingStateConfig = {
  skeletonBars: [
    { width: '75%' }, // w-3/4
    { width: '50%' }, // w-1/2
    { width: '83%' }, // w-5/6
  ],
  loadingText: 'Cargando conversación...',
  loadOlderText: 'Cargando mensajes anteriores...',
};

/**
 * Legal Disclaimer Configuration
 */
export const legalDisclaimerConfig = {
  emoji: '⚕️',
  title: 'Aviso Legal y Protección de Datos',
  mainContent: `Esta aplicación cumple con estándares de protección de información de salud (HIPAA). Tus datos están encriptados y protegidos en nuestros servidores seguros. Como asistente de IA, no tengo acceso directo a PHI sin tu autorización explícita.`,
  footerNote: 'Opción self-hosted disponible para instituciones que requieran control total de infraestructura.',

  // Timer configuration (ephemeral behavior)
  timer: {
    fadeStartMs: 14000, // Start fade-out at 14 seconds
    hideCompleteMs: 15000, // Hide completely at 15 seconds
    fadeDurationMs: 1000, // 1 second fade-out animation
  },
};

/**
 * Accessibility Labels
 */
export const a11yLabels = {
  messagesContainer: 'Historial de mensajes del chat',
  loadingConversation: 'Cargando conversación',
  loadingOlderMessages: 'Cargando mensajes anteriores',
  emptyState: 'Sin mensajes',
  typingIndicator: 'El asistente está escribiendo',
  legalInfo: 'Información legal',
  newMessageAnnouncement: {
    user: 'Mensaje enviado',
    assistant: 'Nuevo mensaje del asistente',
  },
};

/**
 * Spacing Constants (ultra-compact density mode)
 * Maximizes message visibility - 75%+ viewport for content
 */
export const spacing = {
  container: {
    horizontal: 'px-3', // 12px desktop/mobile
    top: 'pt-1.5', // 6px (was 8px)
    bottom: 'pb-1.5', // 6px (was 8px)
  },
  messages: {
    grouped: 'mt-0.5', // 2px ultra-tight
    ungrouped: 'mt-1', // 4px minimal
    dayDivider: 'mb-1.5', // 6px (was 8px)
  },
  sections: {
    typingIndicator: 'mt-0.5', // 2px (was 4px)
    legalDisclaimer: 'mt-2', // 8px (was 16px)
  },
};

// ============================================================================
// FI RECEPTIONIST CONFIGURATION
// ============================================================================

/**
 * Receptionist Empty State Configuration
 * For patient check-in flow after QR scan
 */
export const receptionistEmptyStateConfig = {
  emoji: '🏥',
  welcomeTitle: (patientName?: string) =>
    patientName ? `¡Hola ${patientName}! 👋` : '¡Bienvenido! 👋',
  welcomeSubtitle: 'Soy el asistente virtual de la clínica. Puedo ayudarte con:',
  features: [
    {
      icon: '✓',
      text: 'Check-in para tu cita programada',
    },
    {
      icon: '✓',
      text: 'Información sobre tiempos de espera',
    },
    {
      icon: '✓',
      text: 'Pagos y documentos pendientes',
    },
    {
      icon: '✓',
      text: 'Preguntas sobre preparación para tu cita',
    },
  ],
  ctaText: 'Escribe tu mensaje o selecciona una opción...',
};

/**
 * Receptionist Quick Actions
 * Pre-defined actions for common patient requests
 */
export const receptionistQuickActions = [
  {
    id: 'checkin',
    label: 'Hacer check-in',
    icon: '✅',
    message: 'Quiero hacer check-in para mi cita',
  },
  {
    id: 'wait_time',
    label: '¿Cuánto tiempo de espera?',
    icon: '⏱️',
    message: '¿Cuánto tiempo tengo que esperar?',
  },
  {
    id: 'pay_copay',
    label: 'Pagar copago',
    icon: '💳',
    message: 'Quiero pagar mi copago',
  },
  {
    id: 'reschedule',
    label: 'Reagendar cita',
    icon: '📅',
    message: 'Necesito reagendar mi cita',
  },
];

/**
 * Receptionist Intent Responses
 * Template responses for detected intents
 */
export const receptionistIntentResponses = {
  checkin_success: (patientName: string, position: number, waitMinutes: number) =>
    `¡Listo ${patientName}! Tu check-in está completo. ` +
    `Eres el número ${position} en la fila. ` +
    `Tiempo estimado de espera: ${waitMinutes} minutos. ` +
    `Te llamaremos por tu nombre cuando sea tu turno.`,

  checkin_pending_payment: (amount: number, currency: string) =>
    `Antes de completar el check-in, tienes un copago pendiente de ${currency} ${amount.toFixed(2)}. ` +
    `¿Deseas pagarlo ahora?`,

  checkin_pending_consent: (documentName: string) =>
    `Necesitamos tu firma en el documento "${documentName}" antes de la consulta. ` +
    `¿Puedes revisarlo y firmarlo?`,

  wait_time: (position: number, waitMinutes: number, doctorName: string) =>
    `Actualmente hay ${position - 1} pacientes antes de ti. ` +
    `${doctorName} estará contigo en aproximadamente ${waitMinutes} minutos. ` +
    `Te avisaremos cuando sea tu turno.`,

  no_appointment: () =>
    `No encontré una cita programada para hoy con tu información. ` +
    `¿Podrías verificar tu código de check-in o CURP?`,

  reschedule_info: () =>
    `Para reagendar tu cita, puedo mostrarte los horarios disponibles ` +
    `o conectarte con la recepción. ¿Qué prefieres?`,

  generic_help: () =>
    `Estoy aquí para ayudarte. Puedes preguntarme sobre:\n` +
    `• Tu cita y tiempo de espera\n` +
    `• Pagos pendientes\n` +
    `• Documentos por firmar\n` +
    `• Preparación para tu consulta`,
};

/**
 * Receptionist Loading State
 */
export const receptionistLoadingConfig = {
  loadingText: 'Buscando tu información...',
  processingPayment: 'Procesando pago...',
  updatingCheckin: 'Actualizando check-in...',
};
