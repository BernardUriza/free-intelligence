import {
  LayoutDashboard,
  FileText,
  Clock,
  Shield,
} from 'lucide-react';

import type { DemoSession } from './types';

export const DEMO_STORAGE_KEY = 'fi_demo_dataset';
export const DEMO_LOADED_KEY = 'fi_demo_loaded';

export const DEEP_LINKS = [
  {
    href: '/dashboard',
    icon: LayoutDashboard,
    label: 'Dashboard',
    description: 'Panel de control principal',
    color: 'fi-text-success',
    cardClass: 'demo-link-emerald',
  },
  {
    href: '/sessions',
    icon: FileText,
    label: 'Sessions',
    description: 'Lista de sesiones activas',
    color: 'fi-text-primary',
    cardClass: 'demo-link-blue',
  },
  {
    href: '/timeline',
    icon: Clock,
    label: 'Timeline',
    description: 'Línea de tiempo de eventos',
    color: 'fi-text-purple',
    cardClass: 'demo-link-purple',
  },
  {
    href: '/audit',
    icon: Shield,
    label: 'Audit',
    description: 'Registro de auditoría',
    color: 'fi-text-warning',
    cardClass: 'demo-link-amber',
  },
] as const;

/** Maps session type to its badge CSS class. */
export function getTypeBadgeClass(type: DemoSession['type']): string {
  switch (type) {
    case 'medical':
      return 'demo-badge-medical';
    case 'legal':
      return 'demo-badge-legal';
    case 'code':
      return 'demo-badge-code';
    default:
      return 'demo-badge-default';
  }
}
