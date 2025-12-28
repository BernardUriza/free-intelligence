/**
 * Demo Data Loader Page
 * Card: FI-UI-FEAT-207
 *
 * Features:
 * - Load 3 demo sessions (medical, legal, code)
 * - Deep-links to all screens (Dashboard, Sessions, Timeline, Audit)
 * - Load/Reset demo data with confirmation
 * - localStorage persistence
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Database,
  Play,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  LayoutDashboard,
  FileText,
  Clock,
  Shield,
  Trash2,
  Info,
} from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';

// Demo session types
interface DemoSession {
  id: string;
  type: 'medical' | 'legal' | 'code';
  title: string;
  description: string;
  eventCount: number;
  events: DemoEvent[];
  created_at: string;
}

interface DemoEvent {
  id: string;
  type: string;
  content: string;
  speaker?: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

// Demo data storage key
const DEMO_STORAGE_KEY = 'fi_demo_dataset';
const DEMO_LOADED_KEY = 'fi_demo_loaded';

// Generate demo sessions
function generateDemoSessions(): DemoSession[] {
  const now = Date.now();

  return [
    {
      id: 'demo_medical_001',
      type: 'medical',
      title: 'Consulta Pediátrica - Fiebre',
      description: 'Paciente de 4 años con fiebre de 38.5°C por 2 días',
      eventCount: 10,
      created_at: new Date(now - 3600000).toISOString(),
      events: [
        { id: 'ev_m_001', type: 'speech', speaker: 'Madre', content: 'Mi hija tiene fiebre desde hace dos días, llegó a 38.5 grados.', timestamp: 0 },
        { id: 'ev_m_002', type: 'speech', speaker: 'Doctor', content: '¿Ha tenido otros síntomas como tos, dolor de garganta o diarrea?', timestamp: 4000 },
        { id: 'ev_m_003', type: 'speech', speaker: 'Madre', content: 'Sí, ayer comenzó con un poco de tos y se queja de dolor de garganta.', timestamp: 8000 },
        { id: 'ev_m_004', type: 'speech', speaker: 'Doctor', content: 'Entiendo. ¿Ha estado en contacto con alguien enfermo recientemente?', timestamp: 12000 },
        { id: 'ev_m_005', type: 'speech', speaker: 'Madre', content: 'Sí, su hermano tuvo gripe la semana pasada.', timestamp: 16000 },
        { id: 'ev_m_006', type: 'diarization', content: 'Diarización completada: 2 hablantes identificados', timestamp: 18000, metadata: { speakers: 2, confidence: 0.94 } },
        { id: 'ev_m_007', type: 'vitals', content: 'T: 38.5°C, FR: 24/min, FC: 110/min', timestamp: 20000, metadata: { temp: 38.5, fr: 24, fc: 110 } },
        { id: 'ev_m_008', type: 'exam', content: 'Faringe eritematosa, sin exudado. Auscultación pulmonar sin ruidos anormales.', timestamp: 25000 },
        { id: 'ev_m_009', type: 'assessment', content: 'Infección viral de vías respiratorias superiores (probable gripe)', timestamp: 30000 },
        { id: 'ev_m_010', type: 'plan', content: 'Paracetamol 15mg/kg cada 6h PRN fiebre. Control en 48h si persiste.', timestamp: 35000 },
      ],
    },
    {
      id: 'demo_legal_002',
      type: 'legal',
      title: 'Consulta Legal - Contrato Laboral',
      description: 'Revisión de cláusulas de no competencia en contrato de trabajo',
      eventCount: 8,
      created_at: new Date(now - 7200000).toISOString(),
      events: [
        { id: 'ev_l_001', type: 'speech', speaker: 'Cliente', content: 'Me ofrecieron un nuevo trabajo pero mi contrato actual tiene una cláusula de no competencia.', timestamp: 0 },
        { id: 'ev_l_002', type: 'speech', speaker: 'Abogado', content: '¿Puede mostrarme el contrato? Necesito ver la redacción exacta de la cláusula.', timestamp: 5000 },
        { id: 'ev_l_003', type: 'document', content: 'Contrato de trabajo recibido - 12 páginas', timestamp: 8000, metadata: { pages: 12, format: 'pdf' } },
        { id: 'ev_l_004', type: 'analysis', content: 'Cláusula 15.3: Prohibición de trabajar en empresas competidoras por 2 años', timestamp: 15000 },
        { id: 'ev_l_005', type: 'speech', speaker: 'Abogado', content: 'La cláusula es muy amplia geográficamente. Esto podría ser impugnable.', timestamp: 20000 },
        { id: 'ev_l_006', type: 'research', content: 'Jurisprudencia: 3 casos similares en México (2023-2024)', timestamp: 25000, metadata: { cases: 3 } },
        { id: 'ev_l_007', type: 'recommendation', content: 'Se recomienda negociar reducción del período a 6 meses y limitación geográfica.', timestamp: 30000 },
        { id: 'ev_l_008', type: 'action', content: 'Carta de negociación preparada para envío', timestamp: 35000 },
      ],
    },
    {
      id: 'demo_code_003',
      type: 'code',
      title: 'Code Review - API Authentication',
      description: 'Review of JWT implementation and security patterns',
      eventCount: 12,
      created_at: new Date(now - 1800000).toISOString(),
      events: [
        { id: 'ev_c_001', type: 'context', content: 'Reviewing auth.ts - JWT token generation and validation', timestamp: 0 },
        { id: 'ev_c_002', type: 'file_read', content: 'src/auth/jwt.ts - 245 lines', timestamp: 2000, metadata: { lines: 245, path: 'src/auth/jwt.ts' } },
        { id: 'ev_c_003', type: 'issue', content: 'SECURITY: Token expiration set to 30 days - too long', timestamp: 5000, metadata: { severity: 'high' } },
        { id: 'ev_c_004', type: 'suggestion', content: 'Recommend 15 minute access tokens with refresh token pattern', timestamp: 8000 },
        { id: 'ev_c_005', type: 'file_read', content: 'src/middleware/auth.ts - 89 lines', timestamp: 10000, metadata: { lines: 89 } },
        { id: 'ev_c_006', type: 'issue', content: 'Missing rate limiting on login endpoint', timestamp: 12000, metadata: { severity: 'medium' } },
        { id: 'ev_c_007', type: 'code_change', content: 'Added rate limiter: 5 attempts per minute per IP', timestamp: 15000 },
        { id: 'ev_c_008', type: 'file_read', content: 'src/utils/crypto.ts - 56 lines', timestamp: 18000, metadata: { lines: 56 } },
        { id: 'ev_c_009', type: 'approval', content: 'Crypto utils using bcrypt with cost factor 12 - approved', timestamp: 20000 },
        { id: 'ev_c_010', type: 'test', content: 'Running auth test suite: 23 tests', timestamp: 22000, metadata: { total: 23 } },
        { id: 'ev_c_011', type: 'test_result', content: '23/23 tests passing', timestamp: 28000, metadata: { passed: 23, failed: 0 } },
        { id: 'ev_c_012', type: 'summary', content: 'Review complete: 2 issues found, 1 fixed, 1 pending team discussion', timestamp: 32000 },
      ],
    },
  ];
}

// Deep link destinations
const DEEP_LINKS = [
  {
    href: '/dashboard',
    icon: LayoutDashboard,
    label: 'Dashboard',
    description: 'Panel de control principal',
    color: 'fi-text-success',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/30',
  },
  {
    href: '/sessions',
    icon: FileText,
    label: 'Sessions',
    description: 'Lista de sesiones activas',
    color: 'fi-text-primary',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  {
    href: '/timeline',
    icon: Clock,
    label: 'Timeline',
    description: 'Línea de tiempo de eventos',
    color: 'fi-text-purple',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
  {
    href: '/audit',
    icon: Shield,
    label: 'Audit',
    description: 'Registro de auditoría',
    color: 'fi-text-warning',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
  },
];

export default function DemoPage() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [sessions, setSessions] = useState<DemoSession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState<'load' | 'reset' | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Check if demo data is already loaded
  useEffect(() => {
    const loaded = localStorage.getItem(DEMO_LOADED_KEY);
    if (loaded === 'true') {
      const stored = localStorage.getItem(DEMO_STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          setSessions(parsed);
          setIsLoaded(true);
        } catch {
          // Invalid data, clear it
          localStorage.removeItem(DEMO_STORAGE_KEY);
          localStorage.removeItem(DEMO_LOADED_KEY);
        }
      }
    }
  }, []);

  // Load demo data
  const handleLoadDemo = useCallback(async () => {
    setIsLoading(true);
    setMessage(null);

    try {
      // Simulate loading delay for UX
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const demoSessions = generateDemoSessions();

      // Store in localStorage
      localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(demoSessions));
      localStorage.setItem(DEMO_LOADED_KEY, 'true');

      setSessions(demoSessions);
      setIsLoaded(true);
      setShowConfirm(null);
      setMessage({ type: 'success', text: 'Demo dataset loaded successfully! 3 sessions with 30 events total.' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to load demo dataset. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Reset demo data
  const handleResetDemo = useCallback(async () => {
    setIsLoading(true);
    setMessage(null);

    try {
      await new Promise((resolve) => setTimeout(resolve, 800));

      localStorage.removeItem(DEMO_STORAGE_KEY);
      localStorage.removeItem(DEMO_LOADED_KEY);

      setSessions([]);
      setIsLoaded(false);
      setShowConfirm(null);
      setMessage({ type: 'success', text: 'Demo dataset cleared. All demo data has been removed.' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to reset demo dataset.' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Get session type badge color
  const getTypeColor = (type: DemoSession['type']) => {
    switch (type) {
      case 'medical':
        return 'bg-red-500/20 text-red-300 border-red-500/30';
      case 'legal':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'code':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      default:
        return 'bg-slate-500/20 fi-text border-slate-500/30';
    }
  };

  return (
    <AppTemplate
      headerConfig={{
        title: 'Demo Dataset',
        subtitle: 'Load sample data to explore all features',
        icon: 'database',
        iconColor: 'fi-text-purple',
        showBackButton: true,
      }}
      maxWidth="5xl"
      padding="0"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="px-4 sm:px-6 lg:px-8 py-8">
        {/* Info Banner */}
        <div className="mb-8 p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 fi-text-purple flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-purple-300">
                Demo Mode
              </p>
              <p className="text-sm fi-text-purple/80 mt-1">
                Load a sample dataset to explore the application without affecting production data.
                Demo data includes 3 sessions (medical, legal, code) with 8-12 events each.
              </p>
            </div>
          </div>
        </div>

        {/* Status Message */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-xl flex items-center gap-3 ${
              message.type === 'success'
                ? 'bg-emerald-500/10 border border-emerald-500/30'
                : 'bg-red-500/10 border border-red-500/30'
            }`}
          >
            {message.type === 'success' ? (
              <CheckCircle className="w-5 h-5 fi-text-success flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 fi-text-error flex-shrink-0" />
            )}
            <p className={`text-sm ${message.type === 'success' ? 'text-emerald-300' : 'text-red-300'}`}>
              {message.text}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mb-8 flex flex-wrap gap-4">
          {!isLoaded ? (
            <Button
              onClick={() => setShowConfirm('load')}
              disabled={isLoading}
              loading={isLoading}
              variant="purple"
              size="lg"
              icon={Database}
            >
              Load Demo Dataset
            </Button>
          ) : (
            <>
              <Button
                onClick={() => setShowConfirm('load')}
                disabled={isLoading}
                loading={isLoading}
                variant="purple"
                size="lg"
                icon={RefreshCw}
              >
                Reload Dataset
              </Button>
              <Button
                onClick={() => setShowConfirm('reset')}
                disabled={isLoading}
                variant="secondary"
                size="lg"
                icon={Trash2}
              >
                Reset Demo
              </Button>
            </>
          )}
        </div>

        {/* Confirmation Dialog */}
        {showConfirm && (
          <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-xl">
            <p className="text-sm fi-text mb-4">
              {showConfirm === 'load'
                ? 'This will load 3 demo sessions with sample events. Continue?'
                : 'This will remove all demo data. Continue?'}
            </p>
            <div className="flex gap-3">
              <Button
                onClick={showConfirm === 'load' ? handleLoadDemo : handleResetDemo}
                disabled={isLoading}
                loading={isLoading}
                variant={showConfirm === 'load' ? 'purple' : 'danger'}
              >
                Confirm
              </Button>
              <Button
                onClick={() => setShowConfirm(null)}
                disabled={isLoading}
                variant="secondary"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Demo Sessions List */}
        {isLoaded && sessions.length > 0 && (
          <section className="mb-8">
            <h2 className="fi-title mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 fi-text-purple" />
              Loaded Sessions ({sessions.length})
            </h2>
            <div className="space-y-4">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl hover:border-slate-600 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span
                          className={`px-2 py-0.5 fi-text-xs-medium rounded border ${getTypeColor(
                            session.type
                          )}`}
                        >
                          {session.type.toUpperCase()}
                        </span>
                        <h3 className="text-base font-medium text-white">
                          {session.title}
                        </h3>
                      </div>
                      <p className="fi-subtitle mb-2">
                        {session.description}
                      </p>
                      <div className="flex items-center gap-4 fi-text-xs-muted">
                        <span>{session.eventCount} events</span>
                        <span>ID: {session.id}</span>
                        <span>Created: {new Date(session.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                    <Link
                      href={`/viewer/${session.id}?index=0`}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm fi-text-purple hover:text-purple-300 transition-colors"
                    >
                      View
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Deep Links */}
        <section>
          <h2 className="fi-title mb-4 flex items-center gap-2">
            <Play className="w-5 h-5 fi-text-success" />
            Explore Features
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {DEEP_LINKS.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`p-4 ${link.bgColor} border ${link.borderColor} rounded-xl hover:scale-[1.02] transition-transform`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${link.bgColor}`}>
                      <Icon className={`w-5 h-5 ${link.color}`} />
                    </div>
                    <div>
                      <h3 className={`font-medium ${link.color}`}>{link.label}</h3>
                      <p className="fi-subtitle">{link.description}</p>
                    </div>
                    <ArrowRight className={`w-5 h-5 ${link.color} ml-auto`} />
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

        {/* Quick Start Guide */}
        <section className="mt-8 p-6 bg-slate-800/30 border border-slate-700 rounded-xl">
          <h2 className="fi-title mb-4">Quick Start Guide</h2>
          <ol className="space-y-3 fi-subtitle">
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 bg-purple-500/20 fi-text-purple rounded-full text-xs font-bold flex-shrink-0">
                1
              </span>
              <span>Click &quot;Load Demo Dataset&quot; to populate the application with sample data</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 bg-purple-500/20 fi-text-purple rounded-full text-xs font-bold flex-shrink-0">
                2
              </span>
              <span>Explore sessions using the deep links above (Dashboard, Sessions, Timeline, Audit)</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 bg-purple-500/20 fi-text-purple rounded-full text-xs font-bold flex-shrink-0">
                3
              </span>
              <span>Click on any session to view its interactions in the Viewer</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 bg-purple-500/20 fi-text-purple rounded-full text-xs font-bold flex-shrink-0">
                4
              </span>
              <span>Use &quot;Reset Demo&quot; when done to clear all sample data</span>
            </li>
          </ol>
        </section>
      </div>
    </AppTemplate>
  );
}
