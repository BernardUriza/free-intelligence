/**
 * PageHeader - Unified sticky header component
 *
 * Reusable header pattern with:
 * - Navigation menu (hamburger)
 * - Back button
 * - Title + metrics
 * - User display
 *
 * Card: FI-UI-FEAT-NAV-001
 */

"use client"

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { UserDisplay } from '@/components/auth/UserDisplay'
import { SystemStatus } from '@/components/ui/SystemStatus'
import { Button } from '@/components/ui/button'
import { AppNavigation } from './AppNavigation'
import {
  ArrowLeft,
  Home,
  Shield,
  Activity,
  Database,
  Zap,
  Filter,
  Clock,
  CheckCircle2,
  Stethoscope,
  User,
  Users,
  Settings,
  FileText,
  Tag,
  Building2,
  CalendarDays,
  MessageCircle,
  BookOpen,
  Brain,
  LayoutDashboard,
  type LucideIcon
} from 'lucide-react'

const ICON_MAP: Record<string, LucideIcon> = {
  home: Home,
  shield: Shield,
  activity: Activity,
  database: Database,
  zap: Zap,
  filter: Filter,
  clock: Clock,
  checkCircle2: CheckCircle2,
  stethoscope: Stethoscope,
  user: User,
  users: Users,
  settings: Settings,
  fileText: FileText,
  tag: Tag,
  building2: Building2,
  calendarDays: CalendarDays,
  calendar: CalendarDays,
  messageCircle: MessageCircle,
  bookOpen: BookOpen,
  brain: Brain,
  layoutDashboard: LayoutDashboard,
}

export interface PageHeaderMetric {
  icon: string
  label: string
  value: string | number
  variant?: 'default' | 'primary'
}

export interface PageHeaderConfig {
  /** Show navigation menu (hamburger) - default true */
  showNavigation?: boolean
  /** Show AURITY logo */
  showLogo?: boolean
  /** Show back button (ArrowLeft) */
  showBackButton?: boolean
  /** Back navigation path (default: '/') */
  backPath?: string
  /** Main icon (left side) */
  icon?: string
  iconColor?: string
  /** Page title */
  title: string
  /** Subtitle (small text below title) */
  subtitle?: string
  /** Show AURITY acronym (Advanced Universal Reliable Intelligence for Telemedicine Yield) */
  showAcronym?: boolean
  /** Metrics badges (center section) */
  metrics?: PageHeaderMetric[]
  /** Additional actions (right side, before user) */
  actions?: React.ReactNode
  /** Show user display in header (default: true) */
  showUserDisplay?: boolean
}

export function PageHeader({
  showNavigation = true,
  showLogo = false,
  showBackButton = false,
  backPath = '/',
  icon,
  iconColor = 'fi-text-success',
  title,
  subtitle,
  showAcronym = false,
  metrics = [],
  actions,
  showUserDisplay = true,
}: PageHeaderConfig) {
  const router = useRouter()

  const IconComponent = icon ? ICON_MAP[icon] : null

  return (
    <header className="layout-header">
      <div className="layout-header-inner">
        {/* Left: Navigation + Back button + Title */}
        <div className="layout-header-left">
          {showNavigation && (
            <>
              <AppNavigation compact />
              <div className="layout-header-divider" />
            </>
          )}

          {showLogo && (
            <>
              <Link href="/" className="cursor-pointer hover:opacity-100 transition-opacity">
                <Image
                  src="/logos/aurity-logo-light.png"
                  alt="AURITY"
                  width={120}
                  height={32}
                  loading="eager"
                  className="h-6 sm:h-7 w-auto opacity-90 flex-shrink-0"
                />
              </Link>
              <div className="layout-header-divider" />
            </>
          )}

          {showBackButton && (
            <>
              <Button onClick={() => router.push(backPath)} className="layout-header-back-btn group" variant="ghost" size="sm" title="Atrás">
                <ArrowLeft className="layout-header-back-icon" />
                <span className="fi-text-xs-medium">Atrás</span>
              </Button>
              <div className="layout-header-divider" />
            </>
          )}

          {!showLogo && (
            <div className="layout-header-title-wrapper">
              {IconComponent && <IconComponent className={`layout-header-icon ${iconColor.replace('400', '400/90')}`} />}
              <h1 className="layout-header-title">
                {title}
                {subtitle && <span className="layout-header-subtitle">· {subtitle}</span>}
              </h1>
            </div>
          )}

          {showLogo && subtitle && <span className="layout-header-subtitle-standalone">· {subtitle}</span>}

          {showAcronym && (
            <div className="layout-acronym">
              <span className="layout-acronym-word"><span className="layout-acronym-letter">A</span>dvanced</span>
              <span className="layout-acronym-dot">•</span>
              <span className="layout-acronym-word"><span className="layout-acronym-letter">U</span>niversal</span>
              <span className="layout-acronym-dot">•</span>
              <span className="layout-acronym-word"><span className="layout-acronym-letter">R</span>eliable</span>
              <span className="layout-acronym-dot">•</span>
              <span className="layout-acronym-word"><span className="layout-acronym-letter">I</span>ntelligence</span>
              <span className="layout-acronym-dot">•</span>
              <span className="layout-acronym-word">for <span className="layout-acronym-letter">T</span>elemedicine</span>
              <span className="layout-acronym-dot">•</span>
              <span className="layout-acronym-word"><span className="layout-acronym-letter">Y</span>ield</span>
            </div>
          )}
        </div>

        {/* Center: Metrics Badges */}
        {metrics.length > 0 && (
          <div className="layout-header-metrics">
            {metrics.map((metric, idx) => {
              const MetricIcon = ICON_MAP[metric.icon]
              const isPrimary = metric.variant === 'primary'
              return (
                <div key={idx} className={isPrimary ? 'layout-header-metric-primary' : 'layout-header-metric'}>
                  {MetricIcon && <MetricIcon className={isPrimary ? 'layout-header-metric-icon-primary' : 'layout-header-metric-icon'} />}
                  <span className="layout-header-metric-value">{metric.value}</span>
                </div>
              )
            })}
          </div>
        )}

        {/* Right: Actions + Status + User */}
        <div className="layout-header-right">
          {actions}
          <SystemStatus />
          {showUserDisplay && <UserDisplay />}
        </div>
      </div>
    </header>
  )
}
