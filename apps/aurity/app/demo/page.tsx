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
        return 'demo-badge-medical';
      case 'legal':
        return 'demo-badge-legal';
      case 'code':
        return 'demo-badge-code';
      default:
        return 'demo-badge-default';
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
      <div className="demo-page">
        {/* Info Banner */}
        <div className="demo-info-banner">
          <div className="demo-info-banner-row">
            <Info className="demo-info-banner-icon" />
            <div>
              <p className="demo-info-banner-title">
                Demo Mode
              </p>
              <p className="demo-info-banner-text">
                Load a sample dataset to explore the application without affecting production data.
                Demo data includes 3 sessions (medical, legal, code) with 8-12 events each.
              </p>
            </div>
          </div>
        </div>

        {/* Status Message */}
        {message && (
          <div
            className={message.type === 'success'
              ? 'demo-status-msg-success'
              : 'demo-status-msg-error'}
          >
            {message.type === 'success' ? (
              <CheckCircle className="demo-status-icon fi-text-success" />
            ) : (
              <AlertCircle className="demo-status-icon fi-text-error" />
            )}
            <p className={message.type === 'success' ? 'demo-status-text-success' : 'demo-status-text-error'}>
              {message.text}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="demo-actions">
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
          <div className="demo-confirm">
            <p className="demo-confirm-text">
              {showConfirm === 'load'
                ? 'This will load 3 demo sessions with sample events. Continue?'
                : 'This will remove all demo data. Continue?'}
            </p>
            <div className="demo-confirm-actions">
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
          <section className="demo-sessions">
            <h2 className="demo-sessions-title">
              <Database className="demo-icon-sm fi-text-purple" />
              Loaded Sessions ({sessions.length})
            </h2>
            <div className="demo-sessions-list">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="demo-session-card"
                >
                  <div className="demo-session-row">
                    <div className="demo-session-body">
                      <div className="demo-session-header">
                        <span
                          className={`demo-session-badge ${getTypeColor(
                            session.type
                          )}`}
                        >
                          {session.type.toUpperCase()}
                        </span>
                        <h3 className="demo-session-name">
                          {session.title}
                        </h3>
                      </div>
                      <p className="demo-session-desc">
                        {session.description}
                      </p>
                      <div className="demo-session-meta">
                        <span>{session.eventCount} events</span>
                        <span>ID: {session.id}</span>
                        <span>Created: {new Date(session.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                    <Link
                      href={`/viewer/${session.id}?index=0`}
                      className="demo-session-view-link"
                    >
                      View
                      <ArrowRight className="demo-icon-xs" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Deep Links */}
        <section>
          <h2 className="demo-features-title">
            <Play className="demo-icon-sm fi-text-success" />
            Explore Features
          </h2>
          <div className="demo-features-grid">
            {DEEP_LINKS.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`demo-feature-card ${link.cardClass}`}
                >
                  <div className="demo-feature-row">
                    <div className={`demo-feature-icon-wrap ${link.cardClass}`}>
                      <Icon className={`demo-icon-sm ${link.color}`} />
                    </div>
                    <div>
                      <h3 className={`demo-feature-label ${link.color}`}>{link.label}</h3>
                      <p className="fi-subtitle">{link.description}</p>
                    </div>
                    <ArrowRight className={`demo-feature-arrow ${link.color}`} />
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

        {/* Quick Start Guide */}
        <section className="demo-guide">
          <h2 className="demo-guide-title">Quick Start Guide</h2>
          <ol className="demo-guide-steps">
            <li className="demo-guide-step">
              <span className="demo-step-number">
                1
              </span>
              <span>Click &quot;Load Demo Dataset&quot; to populate the application with sample data</span>
            </li>
            <li className="demo-guide-step">
              <span className="demo-step-number">
                2
              </span>
              <span>Explore sessions using the deep links above (Dashboard, Sessions, Timeline, Audit)</span>
            </li>
            <li className="demo-guide-step">
              <span className="demo-step-number">
                3
              </span>
              <span>Click on any session to view its interactions in the Viewer</span>
            </li>
            <li className="demo-guide-step">
              <span className="demo-step-number">
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
