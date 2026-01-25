/**
 * Dynamic Icon Mapping
 *
 * Maps iconKey strings to Lucide icon components.
 * Used for configuration objects that reference icons by key.
 */

import {
  Clock,
  Users,
  Droplet,
  ClipboardList,
  Bell,
  HeartPulse,
  Smartphone,
  Salad,
  Footprints,
  Brain,
  Shield,
  Moon,
  CheckCircle,
  CreditCard,
  Calendar,
  MessageCircle,
  FileText,
  Building2,
  Bot,
  Zap,
  Search,
  Inbox,
  Hand,
  Lightbulb,
  Activity,
  Video,
  Camera,
  Leaf,
  Home,
  Mic,
  Target,
  User,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Generic icon key to Lucide icon mapping
 * Used by configuration objects like QUICK_MESSAGES, AI_CONTENT_CATEGORIES
 */
export const DYNAMIC_ICONS: Record<string, LucideIcon> = {
  // Time & Status
  clock: Clock,
  bell: Bell,
  checkCircle: CheckCircle,

  // People & Places
  users: Users,
  user: User,
  building: Building2,
  home: Home,

  // Medical & Health
  heartPulse: HeartPulse,
  brain: Brain,
  shield: Shield,
  salad: Salad,
  footprints: Footprints,
  droplet: Droplet,
  moon: Moon,
  activity: Activity,

  // Communication
  messageCircle: MessageCircle,
  smartphone: Smartphone,
  mic: Mic,

  // Documents & Data
  clipboardList: ClipboardList,
  fileText: FileText,
  search: Search,
  inbox: Inbox,

  // Actions
  creditCard: CreditCard,
  calendar: Calendar,

  // Media
  video: Video,
  camera: Camera,

  // Nature & Misc
  leaf: Leaf,
  hand: Hand,
  lightbulb: Lightbulb,
  zap: Zap,
  target: Target,
  bot: Bot,
} as const;

/**
 * Get Lucide icon by key string
 * @param key - The icon key (e.g., 'clock', 'users', 'brain')
 * @param fallback - Optional fallback icon (defaults to FileText)
 * @returns The corresponding Lucide icon component
 */
export function getDynamicIcon(key: string, fallback: LucideIcon = FileText): LucideIcon {
  return DYNAMIC_ICONS[key] || fallback;
}

/**
 * Check if an icon key exists in the mapping
 */
export function hasIconKey(key: string): boolean {
  return key in DYNAMIC_ICONS;
}
