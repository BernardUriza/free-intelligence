'use client';

/**
 * Bryntum Scheduler Demo Page
 * 
 * Página de demostración para validar el funcionamiento de Bryntum SchedulerPro.
 * - Datos de prueba hardcodeados (no depende de APIs)
 * - Útil para debugging y verificar que Bryntum renderiza correctamente
 * - Implementa ambos schedulers: Timeline y Appointments
 * 
 * Created: 2025-12-13
 */

import React, { useState, useMemo, useCallback } from 'react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { Button } from '@/components/ui/button';
import { SchedulerCore } from '@/components/bryntum/core/SchedulerCore';
import {
  buildTimelineSchedulerConfig,
  buildAppointmentSchedulerConfig
} from '@/components/bryntum/utils/config-builders';
import type { UnifiedEvent } from '@/components/bryntum/types/scheduler.types';
import type { Doctor, Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import { Calendar, Users, RefreshCw, CheckCircle2, XCircle, FlaskConical, Search } from 'lucide-react';

// ============================================================================
// Demo Data - Timeline Events
// ============================================================================

const DEMO_TIMELINE_EVENTS: UnifiedEvent[] = [
  {
    id: 'demo-1',
    event_type: 'chat_user',
    content: 'Hola, necesito ayuda con mi cuenta',
    timestamp: Date.now() / 1000 - 3600 * 24, // Hace 1 día
    session_id: 'session-001',
    source: 'chat',
    persona: 'user',
  },
  {
    id: 'demo-2',
    event_type: 'chat_assistant',
    content: '¡Hola! Claro, con gusto te ayudo. ¿Qué necesitas?',
    timestamp: Date.now() / 1000 - 3600 * 23.5,
    session_id: 'session-001',
    source: 'chat',
    persona: 'assistant',
  },
  {
    id: 'demo-3',
    event_type: 'transcription',
    content: 'Transcripción de audio: El paciente reporta dolor en el brazo derecho',
    timestamp: Date.now() / 1000 - 3600 * 20,
    session_id: 'session-002',
    source: 'audio',
    duration: 45.5,
    language: 'es',
    confidence: 0.95,
  },
  {
    id: 'demo-4',
    event_type: 'chat_user',
    content: 'Quiero actualizar mi información personal',
    timestamp: Date.now() / 1000 - 3600 * 12,
    session_id: 'session-003',
    source: 'chat',
    persona: 'user',
  },
  {
    id: 'demo-5',
    event_type: 'transcription',
    content: 'Consulta médica: Evaluación de presión arterial y frecuencia cardíaca',
    timestamp: Date.now() / 1000 - 3600 * 6,
    session_id: 'session-004',
    source: 'audio',
    duration: 120.3,
    language: 'es',
    confidence: 0.98,
  },
  {
    id: 'demo-6',
    event_type: 'chat_assistant',
    content: 'Te ayudo a actualizar tus datos. ¿Qué información quieres cambiar?',
    timestamp: Date.now() / 1000 - 3600 * 5,
    session_id: 'session-003',
    source: 'chat',
    persona: 'assistant',
  },
  {
    id: 'demo-7',
    event_type: 'chat_user',
    content: 'Mi nueva dirección es Calle Principal 123',
    timestamp: Date.now() / 1000 - 3600 * 4,
    session_id: 'session-003',
    source: 'chat',
    persona: 'user',
  },
  {
    id: 'demo-8',
    event_type: 'transcription',
    content: 'Recordatorio de medicamentos: Tomar antibiótico cada 8 horas',
    timestamp: Date.now() / 1000 - 3600 * 2,
    session_id: 'session-005',
    source: 'audio',
    duration: 30.0,
    language: 'es',
    confidence: 0.92,
  },
];

// ============================================================================
// Demo Data - Appointments
// ============================================================================

const DEMO_DOCTORS: Doctor[] = [
  {
    doctor_id: 'doc-1',
    nombre: 'María',
    apellido: 'González',
    display_name: 'Dra. María González',
    especialidad: 'Cardiología',
    avg_consultation_minutes: 30,
    work_start_time: '09:00',
    work_end_time: '17:00',
    working_hours: [
      { date: '2025-01-06', day: 1, start: '', end: '', fullDayClosed: true, reason: 'Feriado' },
      { day: 1, start: '09:00', end: '17:00' },
      { day: 2, start: '09:00', end: '17:00' },
      { day: 3, start: '09:00', end: '17:00' },
      { day: 4, start: '09:00', end: '17:00' },
      { day: 5, start: '09:00', end: '17:00' },
      { day: 6, start: '09:00', end: '12:00' },
    ],
  },
  {
    doctor_id: 'doc-2',
    nombre: 'Juan',
    apellido: 'Pérez',
    display_name: 'Dr. Juan Pérez',
    especialidad: 'Pediatría',
    avg_consultation_minutes: 25,
    work_start_time: '08:30',
    work_end_time: '16:30',
    working_hours: [
      { day: 1, start: '08:30', end: '16:30' },
      { date: '2025-01-07', day: 2, start: '10:00', end: '14:00', reason: 'Capacitación' },
      { day: 2, start: '08:30', end: '16:30' },
      { day: 3, start: '08:30', end: '16:30' },
      { day: 4, start: '08:30', end: '16:30' },
      { day: 5, start: '08:30', end: '16:30' },
    ],
  },
  {
    doctor_id: 'doc-3',
    nombre: 'Ana',
    apellido: 'Martínez',
    display_name: 'Dra. Ana Martínez',
    especialidad: 'Dermatología',
    avg_consultation_minutes: 20,
    work_start_time: '10:00',
    work_end_time: '18:00',
    working_hours: [
      { day: 1, start: '10:00', end: '18:00' },
      { day: 2, start: '10:00', end: '18:30' },
      { day: 3, start: '10:00', end: '18:00' },
      { day: 4, start: '10:00', end: '18:00' },
      { day: 5, start: '10:00', end: '18:00' },
      { day: 6, start: '22:00', end: '02:00', reason: 'Turno nocturno' },
    ],
  },
];

const DEMO_APPOINTMENTS: Appointment[] = [
  {
    appointment_id: 'apt-1',
    patient_id: 'PAC-001',
    patient_name: 'Carlos Ruiz',
    doctor_id: 'doc-1',
    scheduled_at: new Date(Date.now() + 3600 * 1000 * 2).toISOString(), // En 2 horas
    appointment_type: 'FIRST_TIME',
    status: 'scheduled',
    estimated_duration: 30,
    reason: 'Consulta general cardiológica',
    clinic_id: 'clinic-demo',
    checkin_code: 'CHK001',
  },
  {
    appointment_id: 'apt-2',
    patient_id: 'PAC-002',
    patient_name: 'Laura Sánchez',
    doctor_id: 'doc-2',
    scheduled_at: new Date(Date.now() + 3600 * 1000 * 4).toISOString(), // En 4 horas
    appointment_type: 'FOLLOW_UP',
    status: 'confirmed',
    estimated_duration: 25,
    reason: 'Revisión pediátrica',
    clinic_id: 'clinic-demo',
    checkin_code: 'CHK002',
  },
  {
    appointment_id: 'apt-3',
    patient_id: 'PAC-003',
    patient_name: 'Roberto López',
    doctor_id: 'doc-3',
    scheduled_at: new Date(Date.now() + 3600 * 1000 * 6).toISOString(), // En 6 horas
    appointment_type: 'FIRST_TIME',
    status: 'checked_in',
    estimated_duration: 20,
    reason: 'Evaluación dermatológica',
    clinic_id: 'clinic-demo',
    checkin_code: 'CHK003',
  },
  {
    appointment_id: 'apt-4',
    patient_id: 'PAC-004',
    patient_name: 'Sofia Hernández',
    doctor_id: 'doc-1',
    scheduled_at: new Date(Date.now() + 3600 * 1000 * 8).toISOString(), // En 8 horas
    appointment_type: 'EMERGENCY',
    status: 'in_progress',
    estimated_duration: 45,
    reason: 'Urgencia cardiológica',
    clinic_id: 'clinic-demo',
    checkin_code: 'CHK004',
  },
];

// ============================================================================
// Types
// ============================================================================

type DemoMode = 'timeline' | 'appointments';

// ============================================================================
// Main Component
// ============================================================================

export default function BryntumDemoPage() {
  const [mode, setMode] = useState<DemoMode>('appointments');
  const [viewMode, setViewMode] = useState<'day' | 'week' | 'month'>('day');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [refreshKey, setRefreshKey] = useState(0);
  const [renderStatus, setRenderStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

  // ============================================================================
  // Timeline Config (memoized)
  // ============================================================================

  // refreshKey intentionally excluded; component key handles manual remounts
  const timelineConfig = useMemo(() => {
    console.log('[BryntumDemo] Building timeline config', {
      viewMode,
      currentDate: currentDate.toISOString(),
      eventCount: DEMO_TIMELINE_EVENTS.length,
    });

    return buildTimelineSchedulerConfig({
      viewMode,
      currentDate,
      events: DEMO_TIMELINE_EVENTS,
      onEventClick: (event) => {
        console.log('[BryntumDemo] Timeline event clicked:', event);
        alert(`Evento: ${event.content.substring(0, 50)}...`);
      },
    });
  }, [viewMode, currentDate]);

  // ============================================================================
  // Appointments Config (memoized)
  // ============================================================================

  // refreshKey intentionally excluded; component key handles manual remounts
  const appointmentsConfig = useMemo(() => {
    console.log('[BryntumDemo] Building appointments config', {
      viewMode,
      currentDate: currentDate.toISOString(),
      doctorCount: DEMO_DOCTORS.length,
      appointmentCount: DEMO_APPOINTMENTS.length,
    });

    return buildAppointmentSchedulerConfig({
      viewMode,
      currentDate,
      doctors: DEMO_DOCTORS,
      appointments: DEMO_APPOINTMENTS,
      onEventDrop: async (data) => {
        console.log('[BryntumDemo] Appointment dropped:', data);
        alert('Demo: Drag & drop detectado (no guardado)');
      },
      onEventResize: async (data) => {
        console.log('[BryntumDemo] Appointment resized:', data);
        alert('Demo: Resize detectado (no guardado)');
      },
      onEventEdit: async (data) => {
        console.log('[BryntumDemo] Appointment edited:', data);
        alert('Demo: Edit detectado (no guardado)');
      },
    });
  }, [viewMode, currentDate]);

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleRefresh = useCallback(() => {
    console.log('[BryntumDemo] Manual refresh triggered');
    setRenderStatus('loading');
    setRefreshKey((prev) => prev + 1);
    setTimeout(() => setRenderStatus('success'), 1000);
    setTimeout(() => setRenderStatus('idle'), 3000);
  }, []);

  const handleReady = useCallback((scheduler: any) => {
    console.log('[BryntumDemo] Scheduler ready:', {
      type: scheduler?.constructor?.name || 'unknown',
      startDate: scheduler?.startDate,
      endDate: scheduler?.endDate,
      resourceCount: scheduler?.resourceStore?.count || 0,
      eventCount: scheduler?.eventStore?.count || 0,
    });
    setRenderStatus('success');
    setTimeout(() => setRenderStatus('idle'), 3000);
  }, []);

  const handleError = useCallback((error: unknown) => {
    console.error('[BryntumDemo] Scheduler error:', error);
    setRenderStatus('error');
  }, []);

  const navigateDate = (direction: 'prev' | 'next') => {
    const newDate = new Date(currentDate);
    const delta = direction === 'next' ? 1 : -1;
    
    if (viewMode === 'day') {
      newDate.setDate(newDate.getDate() + delta);
    } else if (viewMode === 'week') {
      newDate.setDate(newDate.getDate() + (7 * delta));
    } else {
      newDate.setMonth(newDate.getMonth() + delta);
    }
    
    setCurrentDate(newDate);
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <AppTemplate
      headerConfig={{
        title: 'Bryntum Scheduler - Demo',
        subtitle: `Modo: ${mode === 'timeline' ? 'Timeline (Memoria)' : 'Appointments (Citas)'} • ${DEMO_TIMELINE_EVENTS.length} eventos demo`,
      }}
      backgroundGradient="emerald"
      padding="0"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="p-6">
        {/* Info Card */}
        <div className="mb-4 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
          <h3 className="text-sm font-medium fi-text-info mb-2 flex items-center gap-2">
            <FlaskConical className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
            Página de Demostración
          </h3>
          <p className="text-xs fi-text leading-relaxed">
            Esta página usa <strong>datos hardcodeados</strong> para validar que Bryntum SchedulerPro renderiza correctamente.
            No depende de APIs externas. Útil para debugging.
          </p>
          <div className="mt-2 fi-text-xs">
            • <strong>Timeline:</strong> {DEMO_TIMELINE_EVENTS.length} eventos de prueba<br />
            • <strong>Appointments:</strong> {DEMO_DOCTORS.length} doctores, {DEMO_APPOINTMENTS.length} citas<br />
            • Refresh key: {refreshKey} | Modo: {mode} | Vista: {viewMode}
          </div>
        </div>

        {/* Local Controls (outside Bryntum header) */}
        <div className="mb-3 flex flex-wrap items-center gap-3">
          {/* Mode Toggle */}
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
            <Button
              onClick={() => setMode('timeline')}
              className={mode === 'timeline' ? 'fi-toggle-cyan-active' : 'fi-toggle-cyan'}
              variant="ghost"
              size="sm"
              title="Ver Timeline"
            >
              <Calendar className="h-4 w-4" />
              Timeline
            </Button>
            <Button
              onClick={() => setMode('appointments')}
              className={mode === 'appointments' ? 'fi-toggle-cyan-active' : 'fi-toggle-cyan'}
              variant="ghost"
              size="sm"
              title="Ver Citas"
            >
              <Users className="h-4 w-4" />
              Citas
            </Button>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
            {(['day', 'week', 'month'] as const).map((v) => (
              <Button
                key={v}
                onClick={() => setViewMode(v)}
                className={viewMode === v ? 'fi-toggle-emerald-active' : 'fi-toggle-emerald'}
                variant="ghost"
                size="sm"
                title={v === 'day' ? 'Vista Día' : v === 'week' ? 'Vista Semana' : 'Vista Mes'}
              >
                {v === 'day' ? 'Día' : v === 'week' ? 'Semana' : 'Mes'}
              </Button>
            ))}
          </div>

          {/* Navigation */}
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
            <Button onClick={() => navigateDate('prev')} className="fi-nav-arrow" variant="ghost" size="sm" title="Anterior">←</Button>
            <Button onClick={() => setCurrentDate(new Date())} className="fi-nav-arrow-text" variant="ghost" size="sm" title="Hoy">Hoy</Button>
            <Button onClick={() => navigateDate('next')} className="fi-nav-arrow" variant="ghost" size="sm" title="Siguiente">→</Button>
          </div>

          {/* Refresh */}
          <Button
            onClick={handleRefresh}
            disabled={renderStatus === 'loading'}
            variant="ghost"
            size="sm"
            icon={RefreshCw}
            title="Forzar re-render"
            className={renderStatus === 'loading' ? '[&>svg]:animate-spin' : ''}
          />

          {/* Status Indicator */}
          {renderStatus === 'success' && (
            <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-500/10 fi-text-success rounded-lg text-xs">
              <CheckCircle2 className="h-3 w-3" />
              Renderizado OK
            </div>
          )}
          {renderStatus === 'error' && (
            <div className="flex items-center gap-1.5 px-2 py-1 bg-red-500/10 fi-text-error rounded-lg text-xs">
              <XCircle className="h-3 w-3" />
              Error
            </div>
          )}
        </div>

        {/* Scheduler Container */}
        <div className="bg-slate-900/50 rounded-lg border border-slate-700/50 overflow-hidden">
          <div className="h-[600px]">
            <SchedulerCore
              key={`${mode}-${refreshKey}`}
              getConfig={() => (mode === 'timeline' ? timelineConfig : appointmentsConfig)}
              onReady={handleReady}
              onError={handleError}
              isLoading={renderStatus === 'loading'}
              className="h-full"
            />
          </div>
        </div>

        {/* Debug Console */}
        <div className="mt-4 p-4 bg-slate-900/50 border border-slate-700/50 rounded-lg">
          <h4 className="fi-text-xs-medium text-slate-400 mb-2 flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
            Debug Console
          </h4>
          <div className="space-y-1 text-xs font-mono text-slate-500">
            <div>Mode: <span className="fi-text-info">{mode}</span></div>
            <div>View: <span className="fi-text-success">{viewMode}</span></div>
            <div>Date: <span className="fi-text">{currentDate.toLocaleDateString('es-MX')}</span></div>
            <div>Refresh: <span className="text-yellow-400">{refreshKey}</span></div>
            <div>Status: <span className={
              renderStatus === 'success' ? 'fi-text-success' :
              renderStatus === 'error' ? 'fi-text-error' :
              renderStatus === 'loading' ? 'text-yellow-400' :
              'text-slate-400'
            }>{renderStatus}</span></div>
          </div>
          <p className="mt-2 fi-text-xs-muted">
            Abre la consola del navegador (F12) para ver logs detallados
          </p>
        </div>
      </div>
    </AppTemplate>
  );
}
