
import React from 'react';
import {
  Users,
  Layers,
  MessageSquare,
  X,
  Bell,
  Activity,
} from "lucide-react"
import { SlideManager } from "@/components/dashboard/SlideManager"
import type { ContentItem } from '@/components/dashboard/FIAvatar';
import { DoctorControlPanel } from "@/components/dashboard/DoctorControlPanel"

// Minimal Patient shape used in SidePanel
interface Patient {
  ticketNumber: string;
  status?: 'waiting' | 'in_progress' | string;
  estimatedWait?: number;
}

interface SidePanelProps {
  sidePanelTab: 'queue' | 'content' | 'message';
  setSidePanelTab: (tab: SidePanelProps['sidePanelTab']) => void;
  setShowSidePanel: (show: boolean) => void;
  calledPatient?: Patient | null;
  handleMarkComplete: (ticketNumber: string) => void;
  firstWaitingPatient?: Patient | null;
  handleCallNext: (ticketNumber: string) => void;
  queuePatients: Patient[];
  waitingCount: number;
  inProgressCount: number;
  carouselContent?: ContentItem[];
  setDoctorMessage: (msg: string) => void;
  doctorMessage?: string;
  success: (msg: string) => void;
}

export const SidePanel: React.FC<SidePanelProps> = ({
  sidePanelTab,
  setSidePanelTab,
  setShowSidePanel,
  calledPatient,
  handleMarkComplete,
  firstWaitingPatient,
  handleCallNext,
  queuePatients,
  waitingCount,
  inProgressCount,
  carouselContent,
  setDoctorMessage,
  doctorMessage,
  success,
}) => (
  <aside className="w-96 flex-shrink-0 flex flex-col bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-2xl overflow-hidden">
    <div className="flex items-center justify-between px-4 py-3 fi-border-bottom">
      <div className="fi-flex-gap-sm">
        <button
          onClick={() => setSidePanelTab('queue')}
          className={sidePanelTab === 'queue' ? 'fi-filter-btn-blue' : 'fi-filter-btn'}
        >
          <Users className="w-3.5 h-3.5 inline mr-1" />
          Turnos
        </button>
        <button
          onClick={() => setSidePanelTab('content')}
          className={sidePanelTab === 'content' ? 'fi-filter-btn-purple' : 'fi-filter-btn'}
        >
          <Layers className="w-3.5 h-3.5 inline mr-1" />
          Contenido
        </button>
        <button
          onClick={() => setSidePanelTab('message')}
          className={sidePanelTab === 'message' ? 'fi-filter-btn-emerald' : 'fi-filter-btn'}
        >
          <MessageSquare className="w-3.5 h-3.5 inline mr-1" />
          Mensaje
        </button>
      </div>
      <button
        onClick={() => setShowSidePanel(false)}
        className="fi-btn-close"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
    <div className="flex-1 overflow-y-auto p-4">
      {sidePanelTab === 'queue' && (
        <div className="space-y-4">
          {calledPatient && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
              <div className="fi-flex-between">
                <div className="fi-flex-gap-md">
                  <Bell className="w-5 h-5 fi-text-success animate-bounce" />
                  <div>
                    <p className="text-xs fi-text-success/70">Turno llamado</p>
                    <p className="text-xl font-bold text-emerald-300 font-mono">{calledPatient.ticketNumber}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleMarkComplete(calledPatient.ticketNumber)}
                  className="fi-btn-success-solid"
                >
                  Iniciar consulta
                </button>
              </div>
            </div>
          )}
          {!calledPatient && firstWaitingPatient && (
            <button
              onClick={() => handleCallNext(firstWaitingPatient.ticketNumber)}
              className="fi-btn-call-next"
            >
              <Bell className="w-5 h-5" />
              Llamar: {firstWaitingPatient.ticketNumber}
            </button>
          )}
          {waitingCount > 0 && (
            <div>
              <p className="fi-text-xs-muted mb-2">En espera ({waitingCount})</p>
              <div className="flex flex-wrap gap-2">
                {queuePatients.filter((p: Patient) => p.status === 'waiting').map((p: Patient, i: number) => (
                  <button
                    key={p.ticketNumber}
                    onClick={() => !calledPatient && handleCallNext(p.ticketNumber)}
                    disabled={!!calledPatient}
                    className={`px-3 py-2 rounded-lg text-sm font-mono font-medium transition-all ${
                      i === 0 && !calledPatient
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30 hover:bg-blue-500/30'
                        : 'bg-slate-700 text-slate-400 border border-slate-600'
                    } ${calledPatient ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    {p.ticketNumber}
                    {p.estimatedWait && <span className="fi-text-xs-muted ml-1">~{p.estimatedWait}m</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
          {inProgressCount > 0 && (
            <div>
              <p className="fi-text-xs-muted mb-2">En consulta ({inProgressCount})</p>
              <div className="flex flex-wrap gap-2">
                {queuePatients.filter((p: Patient) => p.status === 'in_progress').map((p: Patient) => (
                  <div
                    key={p.ticketNumber}
                    className="px-3 py-2 rounded-lg text-sm font-mono font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-2"
                  >
                    <Activity className="w-3 h-3 animate-pulse" />
                    {p.ticketNumber}
                  </div>
                ))}
              </div>
            </div>
          )}
          {waitingCount === 0 && !calledPatient && (
            <div className="text-center py-8 text-slate-500">
              <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No hay pacientes en espera</p>
            </div>
          )}
        </div>
      )}
      {sidePanelTab === 'content' && (
        <SlideManager
          clinicId="7f6ef952-d755-43d9-b668-32c3b6879149"
          carouselContent={carouselContent}
        />
      )}
      {sidePanelTab === 'message' && (
        <DoctorControlPanel
          onMessageSend={(message) => {
            setDoctorMessage(message)
            success('Mensaje enviado a pantalla')
          }}
          currentMessage={doctorMessage}
          clinicName="Clínica AURITY"
          doctorId="demo-doctor-001"
          clinicId="7f6ef952-d755-43d9-b668-32c3b6879149"
        />
      )}
    </div>
  </aside>
);
