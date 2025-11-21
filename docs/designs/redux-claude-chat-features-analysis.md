# Redux Claude Chat Features - Análisis Completo

Análisis exhaustivo de las funcionalidades del chat de `redux-claude` que deberíamos considerar integrar o preservar en `free-intelligence/aurity`.

**Fuente:** https://github.com/BernardUriza/redux-claude
**Archivo Principal:** `src/presentation/features/chat/chat-interface.tsx` (527 lines)

---

## 🎯 Funcionalidades Core del Chat

### 1. **ChatGPT-Style Input Interface**

**Ubicación:** Lines 344-412 (chat-interface.tsx)

```tsx
{/* ChatGPT-Style Input Form */}
<form onSubmit={e => { e.preventDefault(); sendMessage(); }}>
  <div className="relative flex items-end bg-gray-800 rounded-2xl">
    <textarea
      value={input}
      onChange={e => {
        setInput(e.target.value)
        // Auto-resize textarea
        e.target.style.height = 'auto'
        e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
      }}
      onKeyDown={e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault()
          sendMessage()
        }
      }}
      placeholder="Message Medical Assistant..."
      className="flex-1 bg-transparent px-4 py-3 resize-none"
      rows={1}
      style={{ height: 'auto' }}
    />
    <button type="submit" disabled={isLoading || !input.trim()}>
      {/* Send icon */}
    </button>
  </div>
</form>
```

**Features:**
- ✅ Auto-resize textarea (max 200px)
- ✅ Enter to send, Shift+Enter for new line
- ✅ Disabled state durante loading
- ✅ Rounded corners (rounded-2xl) - estilo ChatGPT
- ✅ Icon animation (spin during loading, send icon otherwise)

**Beneficio:** UX familiar para usuarios de ChatGPT - menos fricción de adopción.

---

### 2. **Client-Side Session Persistence (localStorage)**

**Ubicación:** `src/services/redux-brain/ClientSessionManager.ts` (253 lines)

```typescript
export class ClientSessionManager {
  private readonly SESSION_PREFIX = 'redux-brain-session-'
  private readonly TTL_MS = 3600000 // 1 hour

  saveSession(sessionId: string, data: Partial<SessionData>): void {
    const sessionData: StoredSessionData = {
      ...data,
      sessionId,
      lastAccess: Date.now(),
      createdAt: data.createdAt || Date.now(),
    }
    localStorage.setItem(key, JSON.stringify(sessionData))
  }

  getSession(sessionId: string): StoredSessionData | null {
    const session = JSON.parse(data) as StoredSessionData
    // Check if session is expired (1 hour)
    if (Date.now() - session.lastAccess > this.TTL_MS) {
      this.deleteSession(sessionId)
      return null
    }
    return session
  }

  cleanupExpiredSessions(): number {
    // Auto-cleanup on page load
  }
}
```

**Features:**
- ✅ Persistencia automática en localStorage
- ✅ TTL de 1 hora (auto-expire)
- ✅ Auto-cleanup de sesiones expiradas al cargar página
- ✅ Métodos especializados: `updatePatientInfo()`, `updateSOAPState()`, `addMessage()`
- ✅ Estadísticas de uso: `getStats()` → total, active, idle, storageUsed

**Beneficio:** **Stateless serverless architecture** - El servidor API no necesita mantener sesiones en memoria (ideal para Netlify Functions, Vercel Edge).

**⚠️ IMPORTANTE PARA AURITY:**
Actualmente en `free-intelligence` usamos **HDF5 server-side storage** (append-only). Esto es más robusto pero requiere servidor persistente. **Considerar híbrido:**
- **Client-side:** localStorage para draft states, UI preferences
- **Server-side:** HDF5 para PHI compliance, audit trail, encryption

---

### 3. **Urgency Level Classification & Visual Indicators**

**Ubicación:** Lines 177-206 (chat-interface.tsx)

```typescript
interface Message {
  urgencyLevel?: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW'
}

interface ApiResponse {
  urgencyAssessment?: {
    level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW'
    protocol?: string
    actions: string[]
    pediatricFlag?: boolean
    reasoning?: string
  }
}

const getUrgencyColor = (level?: string) => {
  switch (level) {
    case 'CRITICAL': return 'border-red-500 bg-red-900/20'
    case 'HIGH': return 'border-orange-500 bg-orange-900/20'
    case 'MODERATE': return 'border-yellow-500 bg-yellow-900/20'
    case 'LOW': return 'border-green-500 bg-green-900/20'
  }
}

const getUrgencyBadge = (level?: string) => {
  const colors = {
    CRITICAL: 'bg-red-600 text-white',
    HIGH: 'bg-orange-600 text-white',
    MODERATE: 'bg-yellow-600 text-black',
    LOW: 'bg-green-600 text-white',
  }
  return <span className={`px-2 py-1 rounded text-xs font-bold ${colors[level]}`}>{level}</span>
}
```

**Features:**
- ✅ Color coding por urgencia (rojo → verde)
- ✅ Badge visual en cada mensaje
- ✅ Border-left coloreado en mensajes del assistant
- ✅ Protocolo médico sugerido (ej: "PROTOCOLO EMERGENCIA")
- ✅ Pediatric flag especial
- ✅ Lista de acciones recomendadas

**UI Display:**
```
┌─────────────────────────────────────────┐
│ Assistant               [🔴 CRITICAL]   │
│ ────────────────────────────────────────│
│ Paciente con dolor torácico...         │
│                                         │
│ Protocolo: EMERGENCIA                  │
│ • Llamar ambulancia inmediatamente     │
│ • Aspirina 300mg masticable            │
│ • Posición semi-incorporado            │
└─────────────────────────────────────────┘
```

**Beneficio:** **Medicina defensiva visual** - El doctor identifica instantáneamente casos críticos.

**🔗 INTEGRACIÓN CON AURITY:**
Ya tenemos `complexity_analyzer.py` que clasifica en SIMPLE/MODERATE/COMPLEX/CRITICAL. Podríamos:
1. Extender `ComplexityMetrics` para incluir `urgency_level`
2. Agregar `urgency_protocol` (ej: "CÓDIGO INFARTO", "TRIAGE PEDIÁTRICO")
3. Renderizar badges en mensajes de chat

---

### 4. **SOAP Progress Bar & Inline Display**

**Ubicación:** Lines 261-321 (chat-interface.tsx)

```tsx
{/* SOAP Progress Bar en cada mensaje */}
{msg.soapProgress !== undefined && (
  <div className="flex items-center gap-2">
    <span className="text-xs text-gray-400">SOAP:</span>
    <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-500"
        style={{ width: `${msg.soapProgress}%` }}
      />
    </div>
    <span className="text-xs text-gray-400">{msg.soapProgress}%</span>
  </div>
)}

{/* SOAP Display cuando llega a 100% */}
{msg.role === 'assistant' && msg.soapProgress === 100 && msg.soapState && (
  <div className="mt-4 p-3 bg-gray-800 rounded-lg border border-gray-700">
    <h4 className="text-xs font-bold text-green-400 mb-2">
      📋 SOAP NOTES COMPLETE
    </h4>

    {msg.soapState.subjetivo && (
      <div className="mb-2">
        <span className="text-yellow-400 font-bold text-xs">S (Subjetivo):</span>
        <p className="text-xs text-gray-300 ml-4 mt-1">{msg.soapState.subjetivo}</p>
      </div>
    )}

    {/* Similar para O, A, P */}
  </div>
)}
```

**Features:**
- ✅ Progress bar visual (0% → 100%) con gradient blue→green
- ✅ Animación smooth (transition-all duration-500)
- ✅ Expansión automática al llegar a 100%
- ✅ Color coding: S=yellow, O=blue, A=purple, P=orange
- ✅ Formato colapsado/expandido

**Beneficio:** **Transparencia del proceso** - El doctor ve cómo se construye el SOAP en tiempo real.

**🔗 INTEGRACIÓN CON AURITY:**
Actualmente en `apps/aurity/app/chats/page.tsx` solo mostramos mensajes planos. Podríamos:
1. Agregar `soapProgress` a `Message` interface
2. Actualizar progress durante orchestration (10% → 30% → 50% → 80% → 100%)
3. Mostrar SOAP expandido al finalizar
4. Sincronizar con `OrchestrationStep` del timeline design

---

### 5. **Debug Panel (Redux Actions Inspector)**

**Ubicación:** Lines 415-521 (chat-interface.tsx)

```tsx
{/* Mobile-Optimized Debug Panel */}
{showDebug && lastResponse && (
  <div className="absolute sm:relative top-0 right-0 w-full sm:w-80 md:w-96 h-full">
    <h3>Debug Info</h3>

    {/* Urgency Assessment */}
    {lastResponse.urgencyAssessment && (
      <div>
        <p>Level: {lastResponse.urgencyAssessment.level}</p>
        <p>Protocol: {lastResponse.urgencyAssessment.protocol}</p>
        <p>Pediatric: {lastResponse.urgencyAssessment.pediatricFlag ? 'Yes' : 'No'}</p>
        <ul>
          {lastResponse.urgencyAssessment.actions.map(action => (
            <li>• {action}</li>
          ))}
        </ul>
      </div>
    )}

    {/* SOAP State */}
    {lastResponse.soapState && (
      <div>
        <span className="text-yellow-400">S:</span>
        <p>{lastResponse.soapState.subjetivo}</p>
        {/* O, A, P similar */}
      </div>
    )}

    {/* Redux Actions */}
    {lastResponse.reduxFlow && (
      <div>
        <h4>Redux Actions ({lastResponse.reduxFlow.totalActions} total)</h4>
        {lastResponse.reduxFlow.recentActions.map(action => (
          <div>
            <p className="text-blue-400">{action.type}</p>
            <p className="text-xs">Phase: {action.phase} | Progress: {action.soapProgress}%</p>
          </div>
        ))}
      </div>
    )}
  </div>
)}
```

**Features:**
- ✅ Toggle button "Show/Hide Debug" en header
- ✅ Panel lateral responsive (absolute en mobile, relative en desktop)
- ✅ Secciones: Urgency Assessment, SOAP State, Redux Actions
- ✅ Redux DevTools-style inspector
- ✅ Scroll independiente (overflow-y-auto)

**Beneficio:** **Debugging médico en producción** - Permite al doctor/dev ver el razonamiento interno del sistema.

**🔗 INTEGRACIÓN CON AURITY:**
Ya tenemos `docs/designs/orchestration-timeline-design.md` que muestra orchestration steps. Podríamos:
1. Crear un panel similar en `/chats` route
2. Mostrar `intermediate_outputs` del DecisionalMiddleware
3. Incluir métricas: complexity_score, confidence_score, personas_invoked
4. Botón toggle "Debug Mode" solo para admin/dev

---

### 6. **Mobile-First Responsive Design**

**Ubicación:** Lines 210-342 (chat-interface.tsx)

```tsx
{/* Mobile-Optimized Header */}
<div className="bg-gray-900 px-3 py-2 sm:p-4">
  <h2 className="text-base sm:text-lg md:text-xl">Medical Assistant</h2>
  <p className="text-xs text-gray-400 mt-1 hidden sm:block">
    Session: {sessionId.slice(0, 16)}...
  </p>
</div>

{/* Messages with Mobile Padding */}
<div className="px-3 py-4 sm:p-4 space-y-3 sm:space-y-4">
  {messages.map(msg => (
    <div className={`p-3 sm:p-4 max-w-full sm:max-w-[90%]`}>
      {/* Content */}
    </div>
  ))}
</div>

{/* Mobile Helper Text */}
<p className="text-xs text-gray-500 mt-2 text-center sm:hidden">
  Press Enter to send • Shift+Enter for new line
</p>

{/* Debug Panel Overlay on Mobile */}
<div className="absolute sm:relative w-full sm:w-80 z-10 shadow-xl sm:shadow-none">
  {/* Close button solo visible en mobile */}
  <button onClick={() => setShowDebug(false)} className="sm:hidden">
    <X />
  </button>
</div>
```

**Features:**
- ✅ Breakpoints Tailwind: `sm:` (640px+), `md:` (768px+)
- ✅ Padding adaptivo: `px-3` mobile → `sm:p-4` desktop
- ✅ Font sizes escalables: `text-base sm:text-lg md:text-xl`
- ✅ Elementos ocultos en mobile: `hidden sm:block`
- ✅ Debug panel overlay en mobile (absolute → relative en desktop)
- ✅ Helper text contextual solo en mobile

**Beneficio:** **Usable en dispositivos médicos** - Tablets, smartphones en consultorios.

**🔗 INTEGRACIÓN CON AURITY:**
Actualmente `apps/aurity` usa breakpoints pero no tan exhaustivamente. Podríamos:
1. Aplicar mismo patrón de padding adaptivo
2. Agregar helper text para gestos táctiles
3. Considerar panel debug como overlay en mobile

---

### 7. **Empty State & Loading States**

**Ubicación:** Lines 236-243, 330-340 (chat-interface.tsx)

```tsx
{/* Empty State */}
{messages.length === 0 ? (
  <div className="text-gray-500 text-center mt-8 sm:mt-16 px-4">
    <div className="text-5xl sm:text-6xl mb-4">🧠</div>
    <p className="text-base sm:text-lg">Redux Brain Medical AI</p>
    <p className="text-xs sm:text-sm mt-2">
      Describe your symptoms or medical condition...
    </p>
  </div>
) : (
  {/* Messages */}
)}

{/* Loading Animation */}
{isLoading && (
  <div className="bg-gray-800/50 p-3 sm:p-4 rounded-lg border-l-4 border-yellow-400 animate-pulse">
    <div className="flex items-center space-x-2 sm:space-x-3">
      <div className="text-yellow-400 text-xl sm:text-2xl animate-spin">⚕️</div>
      <div>
        <p className="text-sm sm:text-base font-semibold">Processing...</p>
        <p className="text-xs text-gray-400 mt-1 hidden sm:block">Analyzing symptoms</p>
      </div>
    </div>
  </div>
)}
```

**Features:**
- ✅ Empty state con branding (🧠 emoji + título)
- ✅ Hint text para primeros usuarios
- ✅ Loading state con spinner médico (⚕️)
- ✅ Animación: `animate-pulse` + `animate-spin`
- ✅ Border amarillo para loading (señal visual de procesamiento)
- ✅ Texto descriptivo: "Processing... Analyzing symptoms"

**Beneficio:** **Feedback visual continuo** - Usuario nunca se pregunta "¿está funcionando?"

**🔗 INTEGRACIÓN CON AURITY:**
Ya tenemos loading states básicos. Podríamos mejorar:
1. Empty state más atractivo en `/chats`
2. Spinner médico (⚕️ o 🩺) en lugar de spinner genérico
3. Mensajes descriptivos: "Analyzing complexity...", "Orchestrating personas..."

---

### 8. **Auto-Scroll to Latest Message**

**Ubicación:** Lines 93-97 (chat-interface.tsx)

```tsx
const messagesEndRef = useRef<HTMLDivElement>(null)

useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
}, [messages])

// En el JSX:
<div ref={messagesEndRef} />
```

**Features:**
- ✅ Ref al final del container de mensajes
- ✅ useEffect escucha cambios en `messages` array
- ✅ Scroll suave (`behavior: 'smooth'`)
- ✅ No interfiere con scroll manual del usuario

**Beneficio:** **UX automático** - Siempre ve el mensaje más reciente sin scroll manual.

**🔗 INTEGRACIÓN CON AURITY:**
Sencillo de implementar en `/chats/page.tsx`. Agregar:
```tsx
const messagesEndRef = useRef<HTMLDivElement>(null)
useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
}, [messages])
```

---

### 9. **Session ID Display & Tracking**

**Ubicación:** Lines 87, 219 (chat-interface.tsx)

```tsx
const [sessionId] = useState(() => `session-${generateId()}`)

// Simple UUID generator
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`
}

// Display truncado en header
<p className="text-xs text-gray-400 mt-1 hidden sm:block">
  Session: {sessionId.slice(0, 16)}...
</p>
```

**Features:**
- ✅ UUID único por sesión (timestamp + random)
- ✅ Generación client-side (no depende de servidor)
- ✅ Display truncado (primeros 16 caracteres)
- ✅ Visible solo en desktop (`hidden sm:block`)

**Beneficio:** **Trazabilidad médica** - Cada conversación tiene ID único para audit trail.

**🔗 INTEGRACIÓN CON AURITY:**
Ya usamos `session_YYYYMMDD_HHMMSS` en backend. Podríamos:
1. Mostrar session ID en header de `/chats`
2. Botón "Copy Session ID" para soporte técnico
3. Link directo a `/timeline?session={id}`

---

### 10. **Gradient Background & Professional Theme**

**Ubicación:** Lines 210, 235 (chat-interface.tsx)

```tsx
<div className="flex flex-col h-full bg-gray-950">
  {/* Messages Container */}
  <div className="flex-1 overflow-y-auto bg-gradient-to-b from-gray-950 to-gray-900">
    {/* Messages */}
  </div>
</div>
```

**Features:**
- ✅ Gradient background (`from-gray-950 to-gray-900`)
- ✅ Dark theme médico profesional
- ✅ Contraste alto para legibilidad
- ✅ Colores consistentes: gray-950, gray-900, gray-800

**Beneficio:** **Estética médica corporativa 2025** - Profesional, moderno, no cansa la vista.

**🔗 INTEGRACIÓN CON AURITY:**
Ya usamos dark theme. Considerar:
1. Gradient sutil en background de `/chats`
2. Mantener paleta de grises consistente

---

## ✅ Contexto de Aurity (Actualizado 2025-11-20)

**Ya resuelto en `free-intelligence`:**
- ✅ `/medical-ai` route para SOAP display completo
- ✅ `/chats` route neutral (conversacional general)
- ✅ Separación clara: chat neutral vs medical workflow

**Conclusión:** La mayoría de funcionalidades de `redux-claude` ya están mejor implementadas en `medical-ai`. El chat de redux-claude es útil principalmente para **features complementarias futuras**.

---

## 🔥 Funcionalidades Complementarias (Post-MVP)

### Features útiles para copiar (baja prioridad):

1. **SOAP Display Component (Inline en chat)**
   **Use Case:** Buscar sesión → Abrir en modo SOAP → Copiar SOAP display
   **Prioridad:** 🟡 MEDIA
   **Esfuerzo:** 🟢 Bajo (2-3 horas)
   **Beneficio:** Quick preview de SOAP sin ir a `/medical-ai`

2. **ChatGPT-Style Input (Auto-resize textarea)**
   **Use Case:** Mejorar UX en `/chats` actual
   **Prioridad:** 🟢 BAJA
   **Esfuerzo:** 🟢 Bajo (1-2 horas)
   **Beneficio:** UX más familiar

3. **Session Search & Quick Open**
   **Use Case:** Buscar `session_20251120_143000` → Abrir en modal con SOAP
   **Prioridad:** 🟡 MEDIA
   **Esfuerzo:** 🟡 Medio (4-6 horas)
   **Beneficio:** Acceso rápido a sesiones pasadas

4. **Auto-Scroll to Latest Message**
   **Use Case:** Scroll automático en `/chats`
   **Prioridad:** 🟢 BAJA
   **Esfuerzo:** 🟢 Bajo (30 min)
   **Beneficio:** Pequeña mejora UX

5. **Debug Panel (Orchestration Inspector)**
   **Use Case:** Ya cubierto por `/timeline` route
   **Prioridad:** ❌ NO NECESARIO
   **Esfuerzo:** N/A
   **Beneficio:** Timeline ya muestra orchestration steps

---

## 📋 Funcionalidades NO Aplicables a Aurity

### ❌ Client-Side Session Persistence (localStorage)

**Razón:**
- Aurity usa **HDF5 server-side storage** para PHI compliance
- HIPAA/NOM-004 requieren audit trail inmutable
- localStorage no es seguro para PHI (Protected Health Information)

**Alternativa:**
- Mantener HDF5 como fuente de verdad
- Usar localStorage solo para UI preferences (theme, sidebar collapsed, etc.)

---

## 🎨 Diseño Sugerido: Chat Mejorado para Aurity

### Wireframe Propuesto:

```
┌────────────────────────────────────────────────────────────────────┐
│ 🩺 Aurity Chat              Session: session_20251120_...  [Debug] │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │ You                                          14:30:25    │     │
│  │ Paciente con dolor torácico de 2 horas...                │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │ Assistant                [🔴 CRITICAL]     SOAP: █████░ 80% │  │
│  │ ────────────────────────────────────────────────────────  │     │
│  │ Caso crítico detectado. Activando protocolo...           │     │
│  │                                                           │     │
│  │ 💊 Processing...                              ⚕️ 14:30:28 │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │ Assistant                [🔴 CRITICAL]     SOAP: ██████ 100%│  │
│  │ ────────────────────────────────────────────────────────  │     │
│  │ Análisis completo:                                        │     │
│  │                                                           │     │
│  │ 📋 SOAP NOTES COMPLETE                                    │     │
│  │ ┌─────────────────────────────────────────────────────┐  │     │
│  │ │ S (Subjetivo): Dolor torácico opresivo...          │  │     │
│  │ │ O (Objetivo): PA: 160/95, FC: 110 lpm...            │  │     │
│  │ │ A (Assessment): Infarto agudo de miocardio...       │  │     │
│  │ │ P (Plan): Código infarto, aspirina, cateterismo...  │  │     │
│  │ └─────────────────────────────────────────────────────┘  │     │
│  │                                              ⚕️ 14:30:45  │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────┐ [↑]   │
│ │ Message Medical Assistant...                           │       │
│ └────────────────────────────────────────────────────────┘       │
│ Press Enter to send • Shift+Enter for new line (mobile only)     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Implementación Sugerida (Post-MVP)

### Feature: Session Search & SOAP Quick Preview

**Use Case:** Doctor quiere revisar SOAP de sesión anterior sin navegar a `/medical-ai`

```tsx
// apps/aurity/components/SessionSearchModal.tsx
function SessionSearchModal({ isOpen, onClose }: Props) {
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState<Session[]>([])
  const [selectedSession, setSelectedSession] = useState<Session | null>(null)

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      {/* Search Input */}
      <input
        placeholder="Buscar sesión (ID o fecha)..."
        value={searchQuery}
        onChange={(e) => searchSessions(e.target.value)}
      />

      {/* Results List */}
      <div className="space-y-2">
        {results.map(session => (
          <div
            key={session.id}
            onClick={() => setSelectedSession(session)}
            className="p-3 bg-slate-800 rounded cursor-pointer"
          >
            <div className="text-sm font-mono">{session.id}</div>
            <div className="text-xs text-slate-400">{session.date}</div>
          </div>
        ))}
      </div>

      {/* SOAP Display (copiado de redux-claude) */}
      {selectedSession?.soapState && (
        <div className="mt-4 p-3 bg-gray-800 rounded-lg">
          <h4 className="text-xs font-bold text-green-400 mb-2">
            📋 SOAP NOTES
          </h4>
          <SOAPDisplay soap={selectedSession.soapState} />
          <button onClick={() => copyToClipboard(selectedSession.soapState)}>
            📋 Copy SOAP
          </button>
        </div>
      )}
    </Modal>
  )
}
```

**Componente reutilizable de redux-claude:**
```tsx
// Copiado de: src/presentation/features/chat/chat-interface.tsx (lines 278-321)
function SOAPDisplay({ soap }: { soap: SOAPState }) {
  return (
    <div className="space-y-2">
      {soap.subjetivo && (
        <div>
          <span className="text-yellow-400 font-bold text-xs">S (Subjetivo):</span>
          <p className="text-xs text-gray-300 ml-4">{soap.subjetivo}</p>
        </div>
      )}
      {soap.objetivo && (
        <div>
          <span className="text-blue-400 font-bold text-xs">O (Objetivo):</span>
          <p className="text-xs text-gray-300 ml-4">{soap.objetivo}</p>
        </div>
      )}
      {/* Similar para A, P */}
    </div>
  )
}
```

---

## 🔮 Otras Features Futuras (Baja Prioridad)

- **Voice Input**: Botón de micrófono en textarea (Web Speech API)
- **Auto-resize Textarea**: Copiar implementación de redux-claude (lines 354-374)
- **Auto-Scroll**: Copiar implementación de redux-claude (lines 93-97)
- **Message Reactions**: Doctor marca mensajes como "Útil" / "Revisar"
- **Diff View**: Comparar SOAP v1 vs v2 (antes/después de refinement)

---

**Status:** Análisis Completo ✅
**Next Step:** Implementar Session Search & SOAP Quick Preview (si se necesita)
