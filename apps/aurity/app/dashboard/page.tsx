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
 * - /dashboard?mode=tv&clinic_id=XXX: Fullscreen TV for waiting room
 * - /dashboard?mode=recepcion: Staff preview
 *
 * Card: FI-UI-DASH-002
 * Inspired by: Command center UIs, OBS Studio, Streaming dashboards
 */

import React, { useEffect, useState, Suspense, memo, useCallback } from "react"
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
  Activity,
  ChevronLeft,
  Maximize,
  Building2,
} from "lucide-react"
import { useCurrentDoctor } from "@/hooks/useCurrentDoctor"
import { useRBAC, ROLES } from "@/hooks/useRBAC"
import { fetchClinics, fetchClinic, type Clinic } from "@/lib/api/clinics"
import { ClinicSelector } from "@/components/shared/ClinicSelector"

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
interface TVModeDisplayProps {
  clinicId: string;
  clinicName: string;
}

const TVModeDisplay = memo(function TVModeDisplay({ clinicId, clinicName }: TVModeDisplayProps) {
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
        const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/list?active_only=true`)
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
    <div className="h-[100dvh] bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col overflow-hidden">
      <div className="flex-shrink-0">
        <QueueStatusBar patients={queuePatients} />
      </div>
      <main className="flex-1 w-full px-2 sm:px-3 md:px-4 lg:px-6 py-2 sm:py-3 overflow-hidden flex flex-col">
        <div className="flex-1 min-h-0 grid gap-2 sm:gap-3 md:gap-4" style={{ gridTemplateColumns: 'minmax(0, 1fr)', gridTemplateRows: '1fr auto' }}>
          <div className="contents lg:grid lg:grid-cols-[3fr_1fr] xl:grid-cols-[4fr_1fr] lg:gap-4">
            <div className="overflow-hidden flex flex-col min-h-0 order-1">
              <div className="flex-1 overflow-hidden flex flex-col min-h-0 bg-gradient-to-br from-slate-800/40 to-slate-900/40 border border-slate-700/30 rounded-xl sm:rounded-2xl" style={{ minHeight: 'clamp(200px, 50vh, 600px)' }}>
                <div className="flex-1 overflow-hidden flex flex-col min-h-0 p-2 sm:p-3 md:p-4 lg:p-5">
                  <WaitingRoomHost mode="broadcast" clinicName={clinicName} doctorMessage={doctorMessage} clinicSlides={slides} />
                </div>
              </div>
            </div>
            {/* QR Check-in Panel */}
            <div className="flex flex-row lg:flex-col gap-2 sm:gap-3 order-2 overflow-hidden min-h-0">
              <div className="flex-1 overflow-hidden min-h-0" style={{ minHeight: 'clamp(120px, 25vh, 400px)' }}>
                <CheckinQRDisplay clinicId={clinicId} clinicName={clinicName} />
              </div>
            </div>
          </div>
        </div>
      </main>
      <div className="flex-shrink-0">
        <InfoBar clinicName={clinicName} />
      </div>
    </div>
  )
})

// =============================================================================
// TV MODE WRAPPER - Reads clinic from URL params or fetches it
// =============================================================================
function TVModeWrapper() {
  const searchParams = useSearchParams()
  const clinicIdParam = searchParams.get("clinic_id")
  const [clinic, setClinic] = useState<{ id: string; name: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadClinic() {
      if (!clinicIdParam) {
        // No clinic_id in URL - show error
        setError("No se especificó una clínica. Use /dashboard?mode=tv&clinic_id=XXX")
        setLoading(false)
        return
      }

      try {
        const clinicData = await fetchClinic(clinicIdParam)
        setClinic({ id: clinicData.clinic_id, name: clinicData.name })
      } catch (err) {
        console.error("Failed to fetch clinic:", err)
        setError("No se pudo cargar la información de la clínica")
      } finally {
        setLoading(false)
      }
    }

    loadClinic()
  }, [clinicIdParam])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-8 h-8 fi-text-success animate-spin mx-auto mb-3" />
          <p className="text-slate-400 text-sm">Cargando clínica...</p>
        </div>
      </div>
    )
  }

  if (error || !clinic) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Clínica no configurada</h2>
          <p className="text-slate-400 text-sm mb-4">
            {error || "Para mostrar el Dashboard TV, configure la clínica desde el centro de comando."}
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Ir al Centro de Comando
          </Link>
        </div>
      </div>
    )
  }

  return <TVModeDisplay clinicId={clinic.id} clinicName={clinic.name} />
}

// =============================================================================
// RECEPCION MODE - Staff preview with clinic selector
// =============================================================================
function RecepcionModeDisplay() {
  const { membership, loading: membershipLoading } = useCurrentDoctor()
  const { hasRole } = useRBAC()
  const isSuperadmin = hasRole(ROLES.SUPERADMIN)

  // Clinic state
  const [clinics, setClinics] = useState<Clinic[]>([])
  const [selectedClinic, setSelectedClinic] = useState<Clinic | null>(null)
  const [clinicsLoading, setClinicsLoading] = useState(false)

  // Load clinics for superadmin
  useEffect(() => {
    if (isSuperadmin) {
      setClinicsLoading(true)
      fetchClinics()
        .then(data => {
          setClinics(data)
          if (data.length > 0 && !selectedClinic) {
            setSelectedClinic(data[0])
          }
        })
        .catch(err => console.error("Failed to fetch clinics:", err))
        .finally(() => setClinicsLoading(false))
    }
  }, [isSuperadmin, selectedClinic])

  // Set clinic from membership for non-superadmin
  useEffect(() => {
    if (!isSuperadmin && membership && !selectedClinic) {
      setSelectedClinic({
        clinic_id: membership.clinic_id,
        name: membership.clinic_name,
        specialty: '',
        timezone: 'America/Mexico_City',
        welcome_message: null,
        primary_color: null,
        logo_url: null,
        checkin_qr_enabled: true,
        chat_enabled: true,
        payments_enabled: false,
        subscription_plan: 'basic',
        is_active: true,
        created_at: '',
        updated_at: null,
      })
    }
  }, [isSuperadmin, membership, selectedClinic])

  const isLoading = membershipLoading || clinicsLoading

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-8 h-8 fi-text-success animate-spin mx-auto mb-3" />
          <p className="text-slate-400 text-sm">Cargando...</p>
        </div>
      </div>
    )
  }

  // No clinic assigned
  if (!selectedClinic) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Sin clínica asignada</h2>
          <p className="text-slate-400 text-sm">
            No tienes una clínica asignada. Contacta al administrador para vincular tu cuenta.
          </p>
        </div>
      </div>
    )
  }

  const tvModeUrl = `/dashboard?mode=tv&clinic_id=${selectedClinic.clinic_id}`

  return (
    <ProtectedRoute>
      <div className="h-[100dvh] bg-slate-950 flex flex-col">
        <header className="flex-shrink-0 px-4 py-3 border-b border-slate-800">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
                <ChevronLeft className="w-5 h-5" />
              </Link>
              <h1 className="fi-title">Vista Recepción</h1>
              <span className="fi-text-xs-muted">Preview de pantalla de pacientes</span>
            </div>

            <div className="flex items-center gap-3">
              {/* Clinic Selector for superadmin */}
              {isSuperadmin && clinics.length > 1 && (
                <ClinicSelector
                  clinics={clinics}
                  selectedClinic={selectedClinic}
                  onSelectClinic={setSelectedClinic}
                  loading={clinicsLoading}
                  compact
                />
              )}

              {/* Current clinic badge for non-superadmin */}
              {!isSuperadmin && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg">
                  <Building2 className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm text-white font-medium">{selectedClinic.name}</span>
                </div>
              )}

              <Link
                href={tvModeUrl}
                target="_blank"
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded-lg transition-colors"
              >
                <Maximize className="w-4 h-4" />
                Pantalla Completa
              </Link>
            </div>
          </div>
        </header>
        <main className="flex-1 p-4 overflow-hidden">
          <div className="max-w-6xl mx-auto h-full">
            <div className="h-full bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden">
              <TVModeDisplay clinicId={selectedClinic.clinic_id} clinicName={selectedClinic.name} />
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

  if (mode === "tv") return <TVModeWrapper />
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
