/**
 * Medical Icons Mapping
 *
 * Centralized Lucide icons for medical/clinical contexts.
 * Replaces emojis for consistency and better visual design.
 */

import {
  Stethoscope,
  Syringe,
  Microscope,
  ClipboardList,
  Building2,
  Brain,
  Lightbulb,
  Leaf,
  Pill,
  Camera,
  Video,
  MessageCircle,
  Zap,
  Search,
  Bot,
  BarChart3,
  FileText,
  Shield,
  Activity,
  Heart,
  ThermometerSun,
  Salad,
  Dumbbell,
  FlaskConical,
  Hand,
  FileX,
  TestTube,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Medical service icons - used in FeaturedServicesWidget, appointments, etc.
 */
export const MEDICAL_SERVICE_ICONS: Record<string, LucideIcon> = {
  consultation: Stethoscope,
  consulta_general: Stethoscope,
  specialist: Stethoscope,
  especialista: Stethoscope,
  vaccination: Syringe,
  vacunacion: Syringe,
  laboratory: Microscope,
  laboratorio: Microscope,
  checkup: ClipboardList,
  check_up: ClipboardList,
  clinic: Building2,
  clinica: Building2,
  hospital: Building2,
} as const;

/**
 * Health category icons - used in DailyTipWidget, health tips
 */
export const HEALTH_CATEGORY_ICONS: Record<string, LucideIcon> = {
  nutrition: Salad,
  nutricion: Salad,
  exercise: Dumbbell,
  ejercicio: Dumbbell,
  actividad_fisica: Dumbbell,
  mental_health: Brain,
  salud_mental: Brain,
  prevention: Shield,
  prevencion: Shield,
  heart: Heart,
  corazon: Heart,
  temperature: ThermometerSun,
} as const;

/**
 * Content type icons - used in SlideManager, content management
 */
export const CONTENT_TYPE_ICONS: Record<string, LucideIcon> = {
  image: Camera,
  imagen: Camera,
  clinic_image: Camera,
  video: Video,
  clinic_video: Video,
  message: MessageCircle,
  mensaje: MessageCircle,
  clinic_message: MessageCircle,
  trivia: Brain,
  daily_tip: Lightbulb,
  tip: Lightbulb,
  calming: Leaf,
  naturaleza: Leaf,
  breathing: Activity,
  respiracion: Activity,
  welcome: Hand,
  bienvenida: Hand,
  philosophy: Building2,
  filosofia: Building2,
  doctor_message: MessageCircle,
} as const;

/**
 * Clinical/SOAP icons - used in order entry, clinical workflows
 */
export const CLINICAL_ICONS: Record<string, LucideIcon> = {
  medication: Pill,
  medicamento: Pill,
  lab: FlaskConical,
  laboratorio: FlaskConical,
  imaging: FileX,
  imagen_medica: FileX,
  xray: FileX,
  test: TestTube,
  prueba: TestTube,
  soap: FileText,
  notes: FileText,
  notas: FileText,
  statistics: BarChart3,
  estadisticas: BarChart3,
} as const;

/**
 * AI/System icons - used in chat, AI features
 */
export const AI_ICONS: Record<string, LucideIcon> = {
  ai: Bot,
  assistant: Bot,
  asistente: Bot,
  brain: Brain,
  cerebro: Brain,
  speed: Zap,
  velocidad: Zap,
  search: Search,
  buscar: Search,
  chat: MessageCircle,
  message: MessageCircle,
} as const;

/**
 * Get icon for a medical service by key
 */
export function getMedicalServiceIcon(key: string): LucideIcon {
  return MEDICAL_SERVICE_ICONS[key.toLowerCase()] || ClipboardList;
}

/**
 * Get icon for a health category
 */
export function getHealthCategoryIcon(key: string): LucideIcon {
  return HEALTH_CATEGORY_ICONS[key.toLowerCase()] || Heart;
}

/**
 * Get icon for content type
 */
export function getContentTypeIcon(key: string): LucideIcon {
  return CONTENT_TYPE_ICONS[key.toLowerCase()] || FileText;
}

/**
 * Get icon for clinical context
 */
export function getClinicalIcon(key: string): LucideIcon {
  return CLINICAL_ICONS[key.toLowerCase()] || FileText;
}

/**
 * Get AI/system icon
 */
export function getAIIcon(key: string): LucideIcon {
  return AI_ICONS[key.toLowerCase()] || Bot;
}
