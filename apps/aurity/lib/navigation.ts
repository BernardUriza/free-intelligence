/**
 * Navigation Configuration
 * Card: FI-UI-FEAT-208
 *
 * Defines all routes and keyboard shortcuts for Index Hub
 * Organized by logical workflow categories following SaaS UX best practices.
 *
 * Architecture:
 * - Categories group routes by mental model (what does the user want to do?)
 * - 80/20 rule: most-used functions at top
 * - Single-click access (no deep submenus)
 *
 * @see https://www.nngroup.com/articles/menu-design/
 * @see https://medium.com/design-bootcamp/designing-a-layout-structure-for-saas-products-best-practices
 */

import {
  LayoutDashboard,
  Clock,
  Shield,
  FileText,
  Stethoscope,
  BookOpen,
  Brain,
  Building2,
  CalendarDays,
  MessageSquare,
  MessageCircle,
  Zap,
  Users,
  Cpu,
  Download,
  Key,
  type LucideIcon,
} from "lucide-react";

// =============================================================================
// CATEGORY DEFINITIONS
// =============================================================================

export type NavCategory = 'clinical' | 'ai_config' | 'admin' | 'hidden';

export interface CategoryMeta {
  id: NavCategory;
  label: string;
  description: string;
  icon: string;
  order: number;
}

export const CATEGORIES: Record<NavCategory, CategoryMeta> = {
  clinical: {
    id: 'clinical',
    label: 'Clinical Workflow',
    description: 'Día a día del médico',
    icon: 'hospital',
    order: 1,
  },
  ai_config: {
    id: 'ai_config',
    label: 'AI Configuration',
    description: 'Cerebro del sistema',
    icon: 'brain',
    order: 2,
  },
  admin: {
    id: 'admin',
    label: 'Administration',
    description: 'Gestión del sistema',
    icon: 'settings',
    order: 3,
  },
  hidden: {
    id: 'hidden',
    label: 'Hidden',
    description: 'Rutas especiales',
    icon: 'eye-off',
    order: 99,
  },
};

// =============================================================================
// ROUTE INTERFACE
// =============================================================================

export interface NavRoute {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  shortcut: string;
  badge?: string;
  /** Category for grouping in navigation */
  category: NavCategory;
  /** Order within category (lower = higher priority) */
  order: number;
  /** Hidden routes don't appear in navigation menu (e.g., patient-only pages accessible via QR) */
  hidden?: boolean;
  /** Only visible in web mode (hidden in desktop/Tauri app) */
  webOnly?: boolean;
}

// =============================================================================
// CLINICAL WORKFLOW - Día a día del médico (80% del uso)
// =============================================================================

const CLINICAL_ROUTES: NavRoute[] = [
  {
    id: "dashboard",
    title: "Panel de Control",
    description: "Gestión de sala de espera y citas",
    href: "/dashboard",
    icon: LayoutDashboard,
    shortcut: "2",
    category: "clinical",
    order: 1,
  },
  {
    id: "medical-ai",
    title: "Medical AI Workflow",
    description: "Workflow médico completo con IA",
    href: "/medical-ai",
    icon: Stethoscope,
    shortcut: "1",
    badge: "AI",
    category: "clinical",
    order: 2,
  },
  {
    id: "appointments-calendar",
    title: "Agenda de Citas",
    description: "Calendario de citas con Bryntum Scheduler",
    href: "/admin/appointments",
    icon: CalendarDays,
    shortcut: "0",
    category: "clinical",
    order: 3,
  },
  {
    id: "timeline",
    title: "Memoria Longitudinal",
    description: "Chats + Consultas en un timeline unificado",
    href: "/timeline",
    icon: Clock,
    shortcut: "3",
    badge: "Unificado",
    category: "clinical",
    order: 4,
  },
];

// =============================================================================
// AI CONFIGURATION - Cerebro del sistema
// =============================================================================

const AI_CONFIG_ROUTES: NavRoute[] = [
  {
    id: "chat",
    title: "Free Intelligence Chat",
    description: "Chat con IA médica · Disponible sin registro",
    href: "/chat",
    icon: MessageCircle,
    shortcut: "C",
    badge: "Público",
    category: "ai_config",
    order: 1,
  },
  {
    id: "personas-admin",
    title: "AI Personas",
    description: "Personalidades médicas del sistema",
    href: "/admin/personas",
    icon: Brain,
    shortcut: "8",
    badge: "Admin",
    category: "ai_config",
    order: 2,
  },
  {
    id: "llm-models-admin",
    title: "LLM Models",
    description: "Modelos de IA disponibles para personas",
    href: "/admin/models",
    icon: Cpu,
    shortcut: "M",
    badge: "Superadmin",
    category: "ai_config",
    order: 3,
  },
  {
    id: "knowledge-admin",
    title: "Knowledge Base",
    description: "Documentos y RAG para asistentes IA",
    href: "/admin/knowledge",
    icon: BookOpen,
    shortcut: "K",
    badge: "Admin",
    category: "ai_config",
    order: 4,
  },
];

// =============================================================================
// ADMINISTRATION - Gestión del sistema
// =============================================================================

const ADMIN_ROUTES: NavRoute[] = [
  {
    id: "downloads",
    title: "Descargas",
    description: "Descarga Aurity Desktop para tu sistema operativo",
    href: "/downloads",
    icon: Download,
    shortcut: "D",
    badge: "Desktop",
    category: "admin",
    order: 0,
    webOnly: true,
  },
  {
    id: "users-admin",
    title: "Usuarios",
    description: "Gestión de usuarios y roles",
    href: "/admin/users",
    icon: Users,
    shortcut: "U",
    badge: "Superadmin",
    category: "admin",
    order: 1,
  },
  {
    id: "licenses-admin",
    title: "Licencias",
    description: "Generador de licencias para Aurity Desktop",
    href: "/admin/licenses",
    icon: Key,
    shortcut: "L",
    badge: "Superadmin",
    category: "admin",
    order: 1.5,
    webOnly: true,
  },
  {
    id: "clinics-admin",
    title: "Clínicas",
    description: "Multi-tenant: clínicas, doctores y check-in",
    href: "/admin/clinics",
    icon: Building2,
    shortcut: "9",
    badge: "Admin",
    category: "admin",
    order: 2,
  },
  {
    id: "policy",
    title: "Policy",
    description: "Políticas de exportación y privacidad",
    href: "/policy",
    icon: Shield,
    shortcut: "4",
    category: "admin",
    order: 3,
  },
  {
    id: "audit",
    title: "Audit",
    description: "Log de auditoría del sistema",
    href: "/audit",
    icon: FileText,
    shortcut: "5",
    category: "admin",
    order: 4,
  },
];

// =============================================================================
// HIDDEN ROUTES - Rutas especiales (no aparecen en menú)
// =============================================================================

const HIDDEN_ROUTES: NavRoute[] = [
  {
    id: "onboarding",
    title: "Onboarding Demo",
    description: "Simulación de flujo de trabajo médico",
    href: "/onboarding",
    icon: Zap,
    shortcut: "O",
    badge: "Demo",
    category: "hidden",
    order: 1,
    hidden: true,
  },
  {
    id: "fi-receptionist",
    title: "FI Receptionist",
    description: "Asistente de check-in conversacional",
    href: "/checkin/chat?clinic=demo",
    icon: MessageSquare,
    shortcut: "R",
    badge: "Pacientes",
    category: "hidden",
    order: 2,
    hidden: true,
  },
  {
    id: "bryntum-demo",
    title: "Bryntum Scheduler Demo",
    description: "Pruebas de Bryntum con datos hardcodeados",
    href: "/demos/bryntum",
    icon: CalendarDays,
    shortcut: "B",
    badge: "Debug",
    category: "hidden",
    order: 3,
    hidden: true,
  },
];

// =============================================================================
// COMBINED ROUTES (ordenadas por categoría y orden interno)
// =============================================================================

export const NAV_ROUTES: NavRoute[] = [
  ...CLINICAL_ROUTES,
  ...AI_CONFIG_ROUTES,
  ...ADMIN_ROUTES,
  ...HIDDEN_ROUTES,
].sort((a, b) => {
  // Primero por categoría
  const catA = CATEGORIES[a.category].order;
  const catB = CATEGORIES[b.category].order;
  if (catA !== catB) return catA - catB;
  // Luego por orden dentro de categoría
  return a.order - b.order;
});

/**
 * Validate uniqueness of shortcuts
 */
function validateUniqueShortcuts(routes: NavRoute[]): void {
  const shortcutSet = new Set<string>();
  for (const route of routes) {
    if (shortcutSet.has(route.shortcut)) {
      throw new Error(`Duplicate shortcut detected: ${route.shortcut} in route ${route.id}`);
    }
    shortcutSet.add(route.shortcut);
  }
}

// Validate shortcuts at runtime
validateUniqueShortcuts(NAV_ROUTES);

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get route by shortcut key (1-9, letters)
 */
export function getRouteByShortcut(key: string): NavRoute | undefined {
  return NAV_ROUTES.find((route) => route.shortcut.toUpperCase() === key.toUpperCase());
}

/**
 * Get route by href
 */
export function getRouteByHref(href: string): NavRoute | undefined {
  return NAV_ROUTES.find((route) => route.href === href);
}

/**
 * Get routes by category (excluding hidden routes unless specified)
 */
export function getRoutesByCategory(category: NavCategory, includeHidden = false): NavRoute[] {
  return NAV_ROUTES
    .filter((route) => route.category === category && (includeHidden || !route.hidden))
    .sort((a, b) => a.order - b.order);
}

/**
 * Get all visible categories with their routes (for rendering grouped navigation)
 */
export function getGroupedRoutes(): Array<{ category: CategoryMeta; routes: NavRoute[] }> {
  const visibleCategories: NavCategory[] = ['clinical', 'ai_config', 'admin'];

  return visibleCategories
    .map((catId) => ({
      category: CATEGORIES[catId],
      routes: getRoutesByCategory(catId),
    }))
    .filter((group) => group.routes.length > 0)
    .sort((a, b) => a.category.order - b.category.order);
}

/**
 * Get all visible routes (excluding hidden)
 */
export function getVisibleRoutes(): NavRoute[] {
  return NAV_ROUTES.filter((route) => !route.hidden);
}
