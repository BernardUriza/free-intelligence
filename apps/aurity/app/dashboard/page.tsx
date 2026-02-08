"use client"

/**
 * Dashboard Page - Clinic Command Center
 *
 * REDESIGNED: TV Preview as protagonist with floating toolbars
 *
 * Layout:
 * - TV Preview: 80%+ of screen (main focus)
 * - Top Toolbar: Stats + Quick Actions (floating, compact)
 * - Bottom Controls: Carousel navigation + playback
 * - Side Panel: Queue management (collapsible overlay)
 *
 * Modes:
 * - /dashboard (default): Command center view
 * - /dashboard?mode=tv: Fullscreen TV for waiting room
 * - /dashboard?mode=recepcion: Staff preview
 *
 * Card: FI-UI-DASH-002
 * Inspired by: Command center UIs, OBS Studio, Streaming dashboards
 */

import React, { useEffect, useState, Suspense, memo } from "react"
import { useSearchParams } from "next/navigation"
import Image from "next/image"
import Link from "next/link"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"
import { WaitingRoomHost } from "@/components/dashboard/waiting-room-host"
import { CheckinQRDisplay } from "@/components/checkin"
import { QueueStatusBar } from "@/components/dashboard/QueueComponents"
import { CommandCenterDisplay } from "@/components/dashboard/command-center/CommandCenterDisplay"
import {
  MOCK_QUEUE_PATIENTS,
  type QueuePatient,
} from "@/lib/dashboard/constants"
import {
  CheckCircle2,
  Activity,
  ChevronLeft,
  Maximize,
} from "lucide-react"
import { listClinicMedia } from "@/lib/api/clinic-media"

// =============================================================================
// INFO BAR - Bottom bar with time, date, branding (for TV mode)
// =============================================================================
const InfoBar = memo(function InfoBar({ clinicName }: { clinicName: string }) {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    })
  }

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('es-MX', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    })
  }

  return (
    <div className="dash-infobar-wrap fi-border-top/50">
      <div className="dash-infobar-inner">
        <div className="dash-infobar-row">
          <div className="dash-infobar-time-group">
            <time
              className="dash-infobar-clock"
              style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
              dateTime={currentTime.toISOString()}
            >
              {formatTime(currentTime)}
            </time>
            <time
              className="dash-infobar-date"
              style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.125rem)' }}
              dateTime={currentTime.toISOString()}
            >
              {formatDate(currentTime)}
            </time>
          </div>
          <div className="dash-infobar-branding">
            <Image
              src="/logos/aurity-logo-light.png"
              alt={`Logo de ${clinicName}`}
              width={100}
              height={28}
              style={{ height: 'clamp(1.25rem, 2.5vw, 2.5rem)', width: 'auto' }}
              className="dash-infobar-logo"
            />
            <span className="dash-infobar-separator">·</span>
            <span className="dash-infobar-clinic-name" style={{ fontSize: 'clamp(0.75rem, 1vw, 1rem)' }}>
              {clinicName}
            </span>
          </div>
          <div className="dash-infobar-status-group">
            <div className="dash-infobar-status-inner">
              <div
                className="dash-infobar-status-dot"
                style={{ width: 'clamp(0.5rem, 0.8vw, 0.75rem)', height: 'clamp(0.5rem, 0.8vw, 0.75rem)' }}
              />
              <span className="fi-text-success" style={{ fontSize: 'clamp(0.625rem, 1vw, 0.875rem)' }}>
                Sistema On-Premise
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
})

// =============================================================================
// TV MODE - Patient Waiting Room Display (Fullscreen)
// =============================================================================
const TVModeDisplay = memo(function TVModeDisplay() {
  const [doctorMessage] = useState<string | null>(null)
  const [slides, setSlides] = useState<any[]>([])
  const [queuePatients] = useState<QueuePatient[]>([
    ...MOCK_QUEUE_PATIENTS.slice(0, 1),
    { ticketNumber: 'A-013', status: 'called' as const },
    ...MOCK_QUEUE_PATIENTS.slice(1),
  ])

  useEffect(() => {
    async function fetchSlides() {
      try {
        const media = await listClinicMedia({ activeOnly: true })
        setSlides(media)
      } catch (error) {
        console.error("Failed to fetch slides:", error)
      }
    }
    fetchSlides()
  }, [])

  return (
    <div className="dash-tv-shell">
      <div className="dash-tv-shrink">
        <QueueStatusBar patients={queuePatients} />
      </div>
      <main className="dash-tv-main">
        <div className="dash-tv-grid" style={{ gridTemplateColumns: 'minmax(0, 1fr)', gridTemplateRows: '1fr auto' }}>
          <div className="dash-tv-columns">
            <div className="dash-tv-media-col">
              <div className="dash-tv-media-card" style={{ minHeight: 'clamp(200px, 50vh, 600px)' }}>
                <div className="dash-tv-media-inner">
                  <WaitingRoomHost mode="broadcast" clinicName="Clínica AURITY" doctorMessage={doctorMessage} clinicSlides={slides} />
                </div>
              </div>
            </div>
            <div className="dash-tv-sidebar">
              <div className="dash-tv-qr-section" style={{ minHeight: 'clamp(120px, 25vh, 300px)' }}>
                <CheckinQRDisplay clinicId="7f6ef952-d755-43d9-b668-32c3b6879149" clinicName="Clínica AURITY" />
              </div>
              <div className="dash-tv-instructions">
                <div className="dash-tv-instructions-header">
                  <CheckCircle2 className="dash-tv-instructions-icon fi-text-success" style={{ width: 'clamp(1rem, 2vw, 1.5rem)', height: 'clamp(1rem, 2vw, 1.5rem)' }} />
                  <span className="dash-tv-instructions-title" style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}>¿Ya llegaste?</span>
                </div>
                <ol className="fi-stack-sm">
                  {[{ num: 1, text: 'Escanea el QR' }, { num: 2, text: 'Confirma llegada' }, { num: 3, text: 'Te avisamos' }].map(step => (
                    <li key={step.num} className="dash-tv-step">
                      <span className="dash-tv-step-number fi-text-success" style={{ width: 'clamp(1.25rem, 2vw, 1.75rem)', height: 'clamp(1.25rem, 2vw, 1.75rem)', fontSize: 'clamp(0.625rem, 1vw, 0.875rem)' }}>{step.num}</span>
                      <span className="fi-text" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1rem)' }}>{step.text}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </div>
      </main>
      <div className="dash-tv-shrink">
        <InfoBar clinicName="Clínica AURITY" />
      </div>
    </div>
  )
})

// =============================================================================
// RECEPCION MODE - Staff preview
// =============================================================================
function RecepcionModeDisplay() {
  return (
    <ProtectedRoute>
      <div className="dash-recep-shell">
        <header className="dash-recep-header">
          <div className="dash-recep-header-inner">
            <div className="dash-recep-header-left">
              <Link href="/dashboard" className="dash-recep-back-link">
                <ChevronLeft className="dash-recep-back-icon" />
              </Link>
              <h1 className="fi-title">Vista Recepción</h1>
              <span className="fi-text-xs-muted">Preview de pantalla de pacientes</span>
            </div>
            <Link
              href="/dashboard?mode=tv"
              target="_blank"
              className="dash-recep-fullscreen-btn"
            >
              <Maximize className="dash-recep-fullscreen-icon" />
              Pantalla Completa
            </Link>
          </div>
        </header>
        <main className="dash-recep-main">
          <div className="dash-recep-container">
            <div className="dash-recep-preview-frame">
              <TVModeDisplay />
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================
function DashboardContent() {
  const searchParams = useSearchParams()
  const mode = searchParams.get("mode")

  if (mode === "tv") return <TVModeDisplay />
  if (mode === "recepcion") return <RecepcionModeDisplay />
  return <CommandCenterDisplay />
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="dash-loading-wrapper">
          <div className="dash-loading-center">
            <Activity className="dash-loading-spinner fi-text-success" />
            <p className="dash-loading-text">Cargando dashboard...</p>
          </div>
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  )
}
