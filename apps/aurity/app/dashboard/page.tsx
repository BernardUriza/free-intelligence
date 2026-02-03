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
    <div className="bg-slate-900/90 backdrop-blur-sm fi-border-top/50">
      <div className="w-full px-3 sm:px-4 md:px-6 lg:px-8 py-2 sm:py-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 sm:gap-4">
          <div className="flex items-center gap-3 sm:gap-4 md:gap-6">
            <time
              className="font-bold text-white font-mono"
              style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
              dateTime={currentTime.toISOString()}
            >
              {formatTime(currentTime)}
            </time>
            <time
              className="text-slate-400 capitalize hidden sm:block"
              style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.125rem)' }}
              dateTime={currentTime.toISOString()}
            >
              {formatDate(currentTime)}
            </time>
          </div>
          <div className="hidden md:flex items-center gap-2 sm:gap-3">
            <Image
              src="/logos/aurity-logo-light.png"
              alt={`Logo de ${clinicName}`}
              width={100}
              height={28}
              style={{ height: 'clamp(1.25rem, 2.5vw, 2.5rem)', width: 'auto' }}
              className="opacity-80"
            />
            <span className="text-slate-500 hidden lg:inline">·</span>
            <span className="text-slate-400 hidden lg:inline" style={{ fontSize: 'clamp(0.75rem, 1vw, 1rem)' }}>
              {clinicName}
            </span>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
            <div className="flex items-center gap-1 sm:gap-2">
              <div
                className="bg-emerald-500 rounded-full animate-pulse"
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
        const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7001"
        const response = await fetch(`${backendURL}/api/aurity/clinic/clinic-media/list?active_only=true`)
        if (response.ok) {
          const data = await response.json()
          setSlides(data.media || [])
        }
      } catch (error) {
        console.error("Failed to fetch slides:", error)
      }
    }
    fetchSlides()
  }, [])

  return (
    <div className="h-dvh bg-linear-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col overflow-hidden">
      <div className="flex-shrink-0">
        <QueueStatusBar patients={queuePatients} />
      </div>
      <main className="flex-1 w-full px-2 sm:px-3 md:px-4 lg:px-6 py-2 sm:py-3 overflow-hidden flex flex-col">
        <div className="flex-1 min-h-0 grid gap-2 sm:gap-3 md:gap-4" style={{ gridTemplateColumns: 'minmax(0, 1fr)', gridTemplateRows: '1fr auto' }}>
          <div className="contents lg:grid lg:grid-cols-[3fr_1fr] xl:grid-cols-[4fr_1fr] lg:gap-4">
            <div className="overflow-hidden flex flex-col min-h-0 order-1">
              <div className="flex-1 overflow-hidden flex flex-col min-h-0 bg-linear-to-br from-slate-800/40 to-slate-900/40 border border-slate-700/30 rounded-xl sm:rounded-2xl" style={{ minHeight: 'clamp(200px, 50vh, 600px)' }}>
                <div className="flex-1 overflow-hidden flex flex-col min-h-0 p-2 sm:p-3 md:p-4 lg:p-5">
                  <WaitingRoomHost mode="broadcast" clinicName="Clínica AURITY" doctorMessage={doctorMessage} clinicSlides={slides} />
                </div>
              </div>
            </div>
            <div className="flex flex-row lg:flex-col gap-2 sm:gap-3 order-2 overflow-hidden min-h-0">
              <div className="flex-3 lg:flex-3 overflow-hidden min-h-0" style={{ minHeight: 'clamp(120px, 25vh, 300px)' }}>
                <CheckinQRDisplay clinicId="7f6ef952-d755-43d9-b668-32c3b6879149" clinicName="Clínica AURITY" />
              </div>
              <div className="hidden md:flex flex-1 lg:flex-1 bg-linear-to-br from-slate-800/40 to-slate-900/40 border border-slate-700/30 rounded-xl p-3 sm:p-4 flex-col justify-center overflow-hidden min-h-0">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle2 className="fi-text-success flex-shrink-0" style={{ width: 'clamp(1rem, 2vw, 1.5rem)', height: 'clamp(1rem, 2vw, 1.5rem)' }} />
                  <span className="font-semibold text-slate-200" style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}>¿Ya llegaste?</span>
                </div>
                <ol className="fi-stack-sm">
                  {[{ num: 1, text: 'Escanea el QR' }, { num: 2, text: 'Confirma llegada' }, { num: 3, text: 'Te avisamos' }].map(step => (
                    <li key={step.num} className="flex items-center gap-2">
                      <span className="rounded-full bg-emerald-500/20 fi-text-success flex items-center justify-center font-bold flex-shrink-0" style={{ width: 'clamp(1.25rem, 2vw, 1.75rem)', height: 'clamp(1.25rem, 2vw, 1.75rem)', fontSize: 'clamp(0.625rem, 1vw, 0.875rem)' }}>{step.num}</span>
                      <span className="fi-text" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1rem)' }}>{step.text}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </div>
      </main>
      <div className="flex-shrink-0">
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
      <div className="h-dvh bg-slate-950 flex flex-col">
        <header className="flex-shrink-0 px-4 py-3 border-b border-slate-800">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
                <ChevronLeft className="w-5 h-5" />
              </Link>
              <h1 className="fi-title">Vista Recepción</h1>
              <span className="fi-text-xs-muted">Preview de pantalla de pacientes</span>
            </div>
            <Link
              href="/dashboard?mode=tv"
              target="_blank"
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded-lg transition-colors"
            >
              <Maximize className="w-4 h-4" />
              Pantalla Completa
            </Link>
          </div>
        </header>
        <main className="flex-1 p-4 overflow-hidden">
          <div className="max-w-6xl mx-auto h-full">
            <div className="h-full bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden">
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
        <div className="min-h-screen bg-slate-950 flex items-center justify-center">
          <div className="text-center">
            <Activity className="w-8 h-8 fi-text-success animate-spin mx-auto mb-3" />
            <p className="text-slate-400 text-sm">Cargando dashboard...</p>
          </div>
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  )
}
