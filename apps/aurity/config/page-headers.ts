/**
 * Page Header Configurations
 *
 * Centralized config for all page headers in the AURITY app.
 * Each page can override or extend these defaults.
 */

import type { PageHeaderConfig } from '../components/layout/PageHeader'

export type PageHeaderFactory = (data?: any) => PageHeaderConfig

/**
 * Dashboard header config (Command Center)
 * @param data - { waitingCount, avgWaitTime, appointmentsToday }
 */
export const dashboardHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'layoutDashboard',
  iconColor: 'text-purple-400',
  title: 'Centro de Mando',
  subtitle: 'Control de sala de espera y pantalla TV',
  metrics: [
    ...(data?.waitingCount !== undefined ? [{
      icon: 'users' as const,
      label: 'en espera',
      value: data.waitingCount,
    }] : []),
    ...(data?.avgWaitTime !== undefined ? [{
      icon: 'clock' as const,
      label: 'min',
      value: data.avgWaitTime,
    }] : []),
    ...(data?.appointmentsToday !== undefined ? [{
      icon: 'calendarDays' as const,
      label: 'citas hoy',
      value: data.appointmentsToday,
    }] : []),
  ],
})

/**
 * Timeline header config
 * @param data - { totalEvents, p95Latency, sessionId, successRate, totalDuration }
 */
export const timelineHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  title: 'Timeline Continuo',
  subtitle: data?.sessionId
    ? `Conversación infinita · Filtro: ${data.sessionId.slice(0, 8)}...`
    : 'Conversación infinita',
  metrics: data?.totalEvents > 0 ? [
    {
      icon: 'activity',
      label: '',
      value: data.totalEvents,
    },
    {
      icon: 'checkCircle2',
      label: '',
      value: `${data.successRate.toFixed(0)}%`,
    },
    {
      icon: 'zap',
      label: '',
      value: `p95: ${data.p95Latency.toFixed(0)}ms`,
    },
    {
      icon: 'clock',
      label: '',
      value: `${data.totalDuration.toFixed(1)}s`,
    },
  ] : [],
})

/**
 * Audit Log header config
 * @param data - { logsCount, selectedOperation }
 */
export const auditHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'shield',
  iconColor: 'text-blue-400',
  title: 'Audit Log',
  subtitle: 'System security trail · Append-only',
  metrics: [
    {
      icon: 'activity',
      label: '',
      value: `${data?.logsCount || 0} events`,
    },
    ...(data?.selectedOperation && data.selectedOperation !== 'ALL' ? [{
      icon: 'filter',
      label: '',
      value: data.selectedOperation,
      variant: 'primary' as const,
    }] : []),
  ],
})

/**
 * Medical AI header config
 * @param data - { subtitle, patientName }
 */
export const medicalAiHeader: PageHeaderFactory = (data) => ({
  showLogo: true,
  showBackButton: true,
  backPath: '/',
  icon: 'stethoscope',
  iconColor: 'text-emerald-400',
  title: 'Medical AI Workflow',
  subtitle: data?.subtitle || 'Selecciona paciente o continúa consulta',
  metrics: [],
})

/**
 * Policy Viewer header config
 * @param data - { version, source, timestamp }
 */
export const policyHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'fileText',
  iconColor: 'text-purple-400',
  title: 'Policy Configuration',
  subtitle: data?.version
    ? `Effective policy · Version ${data.version} · Read-only snapshot`
    : 'Effective policy configuration · Read-only',
  metrics: data?.version ? [
    {
      icon: 'tag',
      label: '',
      value: `v${data.version}`,
    },
    ...(data.timestamp && data.timestamp !== 'unknown' ? [{
      icon: 'clock',
      label: '',
      value: data.timestamp,
    }] : []),
  ] : [],
})

/**
 * User Profile header config
 * @param data - { userName, email, role, emailVerified }
 */
export const profileHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'user',
  iconColor: 'text-blue-400',
  title: 'Mi Perfil',
  subtitle: data?.email
    ? `${data.email}${data.emailVerified ? ' · Verificado' : ''}`
    : 'Información de usuario',
  metrics: data?.role ? [
    {
      icon: 'shield',
      label: 'Rol',
      value: data.role,
    },
  ] : [],
})

/**
 * Settings/Config header config
 * @param data - { section }
 * Note: Config and Profile share the same /profile endpoint
 */
export const configHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'settings',
  iconColor: 'text-slate-400',
  title: 'Configuración',
  subtitle: data?.section
    ? `${data.section} · Configuración de usuario`
    : 'Configuración de usuario',
  metrics: [],
})

/**
 * Chat header config
 * @param data - { isAuthenticated, messageCount }
 */
export const chatHeader: PageHeaderFactory = (data) => ({
  showLogo: true,
  showBackButton: true,
  backPath: '/',
  icon: 'messageCircle',
  iconColor: 'text-indigo-400',
  title: 'Free Intelligence',
  subtitle: data?.isAuthenticated
    ? 'Chat con memoria infinita'
    : 'Chat · Sin registro requerido',
  metrics: data?.messageCount ? [
    {
      icon: 'activity',
      label: '',
      value: `${data.messageCount} mensajes`,
    },
  ] : [],
})

/**
 * Onboarding header config
 * @param data - { step, totalSteps }
 */
export const onboardingHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'zap',
  iconColor: 'text-emerald-400',
  title: 'Onboarding Demo',
  subtitle: data?.step
    ? `Paso ${data.step} de ${data.totalSteps || '?'}`
    : 'Simulación de flujo de trabajo',
  metrics: [],
})

/**
 * Admin Clinics header config
 * @param data - { clinicsCount }
 */
export const adminClinicsHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'building2',
  iconColor: 'text-purple-400',
  title: 'Administración de Clínicas',
  subtitle: 'Gestión de clínicas, doctores y citas',
  metrics: data?.clinicsCount ? [
    {
      icon: 'building2',
      label: '',
      value: `${data.clinicsCount} clínicas`,
    },
  ] : [],
})

/**
 * Admin Personas header config
 * @param data - { personasCount }
 */
export const adminPersonasHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'user',
  iconColor: 'text-indigo-400',
  title: 'Gestión de Personas',
  subtitle: 'Configuración de asistentes virtuales',
  metrics: data?.personasCount ? [
    {
      icon: 'user',
      label: '',
      value: `${data.personasCount} personas`,
    },
  ] : [],
})

/**
 * Admin Appointments header config
 * @param data - { appointmentsToday }
 */
export const adminAppointmentsHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'calendarDays',
  iconColor: 'text-blue-400',
  title: 'Calendario de Citas',
  subtitle: 'Programación de consultas médicas',
  metrics: data?.appointmentsToday ? [
    {
      icon: 'calendar',
      label: 'Hoy',
      value: data.appointmentsToday,
    },
  ] : [],
})

/**
 * NAS Installer header config
 */
export const nasInstallerHeader: PageHeaderFactory = () => ({
  showBackButton: true,
  backPath: '/',
  icon: 'database',
  iconColor: 'text-cyan-400',
  title: 'NAS Installer',
  subtitle: 'Self-hosted deployment configuration',
  metrics: [],
})

/**
 * Admin LLM Models header config
 * @param data - { modelsCount }
 */
export const adminLLMModelsHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'brain',
  iconColor: 'text-emerald-400',
  title: 'Modelos LLM',
  subtitle: 'Configuración de modelos de IA disponibles',
  metrics: data?.modelsCount ? [
    {
      icon: 'zap',
      label: '',
      value: `${data.modelsCount} modelos`,
    },
  ] : [],
})

/**
 * Admin Knowledge Base header config
 * @param data - { documentsCount, indexedCount }
 */
export const adminKnowledgeHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'bookOpen',
  iconColor: 'text-emerald-400',
  title: 'Knowledge Base',
  subtitle: 'Documentos para asistentes RAG',
  metrics: data?.documentsCount ? [
    {
      icon: 'fileText',
      label: '',
      value: `${data.documentsCount} docs`,
    },
    ...(data.indexedCount !== undefined ? [{
      icon: 'checkCircle2',
      label: '',
      value: `${data.indexedCount} indexados`,
    }] : []),
  ] : [],
})

/**
 * Admin Users header config
 * @param data - { usersCount }
 */
export const adminUsersHeader: PageHeaderFactory = (data) => ({
  showBackButton: true,
  backPath: '/',
  icon: 'users',
  iconColor: 'text-blue-400',
  title: 'Gestión de Usuarios',
  subtitle: 'Administración de usuarios y roles',
  metrics: data?.usersCount ? [
    {
      icon: 'users',
      label: '',
      value: `${data.usersCount} usuarios`,
    },
  ] : [],
})

/**
 * Admin Licenses header config (Superadmin License Generator)
 */
export const adminLicensesHeader: PageHeaderFactory = () => ({
  showBackButton: true,
  backPath: '/admin/users',
  icon: 'key',
  iconColor: 'text-purple-400',
  title: 'Generador de Licencias',
  subtitle: 'Crear licencias para Aurity Desktop',
  metrics: [],
})

/**
 * Centralized header configs by route
 */
export const PAGE_HEADERS = {
  dashboard: dashboardHeader,
  timeline: timelineHeader,
  audit: auditHeader,
  'medical-ai': medicalAiHeader,
  policy: policyHeader,
  profile: profileHeader,
  config: configHeader,
  chat: chatHeader,
  onboarding: onboardingHeader,
  'admin-clinics': adminClinicsHeader,
  'admin-personas': adminPersonasHeader,
  'admin-appointments': adminAppointmentsHeader,
  'admin-llm-models': adminLLMModelsHeader,
  'admin-knowledge': adminKnowledgeHeader,
  'admin-users': adminUsersHeader,
  'admin-licenses': adminLicensesHeader,
  'nas-installer': nasInstallerHeader,
} as const

export type PageRoute = keyof typeof PAGE_HEADERS
