# Persona Editor Route Design

Diseño de interfaz CRUD para gestionar AI personas - permite configurar, editar y testear los diferentes "agentes médicos" del sistema.

## 📍 Ubicación

**Route:** `/admin/personas` (nueva route)
**Component:** `apps/aurity/app/admin/personas/page.tsx`
**Purpose:** Admin panel para gestionar AI personas (SOAP Editor, Clinical Advisor, etc.)

---

## 🎯 Objetivo

Permitir configurar y administrar:
1. **System Prompts**: Instrucciones base de cada persona
2. **Model Parameters**: Temperature, max_tokens, top_p
3. **Examples**: Few-shot examples para cada persona
4. **Testing**: Probar persona antes de deployar
5. **Versioning**: Historial de cambios en prompts

---

## 📊 Datos Disponibles

### Current Personas (backend/services/llm/persona_manager.py)

```python
PERSONAS = {
    "soap_editor": {
        "name": "SOAP Editor",
        "description": "Especialista en extraer notas SOAP de transcripciones médicas",
        "system_prompt": "Eres un médico experto en documentación clínica...",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 2000,
        "examples": [
            {
                "input": "Paciente con fiebre...",
                "output": {"subjective": "...", "objective": "...", ...}
            }
        ]
    },
    "clinical_advisor": {
        "name": "Clinical Advisor",
        "description": "Valida precisión médica y sugiere mejoras",
        "system_prompt": "Eres un médico senior que revisa notas SOAP...",
        "model": "gpt-4o",
        "temperature": 0.1,
        "max_tokens": 1500,
        "examples": [...]
    },
    "general_assistant": {
        "name": "General Assistant",
        "description": "Asistente conversacional para preguntas generales",
        "system_prompt": "Eres un asistente médico que responde preguntas...",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000,
        "examples": [...]
    }
}
```

### API Schema

**GET /api/admin/personas**
```json
{
  "personas": [
    {
      "id": "soap_editor",
      "name": "SOAP Editor",
      "description": "Especialista en extraer notas SOAP de transcripciones médicas",
      "system_prompt": "...",
      "model": "gpt-4o-mini",
      "temperature": 0.2,
      "max_tokens": 2000,
      "examples": [...],
      "usage_stats": {
        "total_invocations": 145,
        "avg_latency_ms": 3200,
        "avg_cost_usd": 0.015
      },
      "version": 3,
      "last_updated": "2025-11-18T10:30:00Z",
      "updated_by": "Dr. Uriza"
    }
  ]
}
```

**PUT /api/admin/personas/{persona_id}**
```json
{
  "system_prompt": "Updated prompt...",
  "temperature": 0.3,
  "max_tokens": 2500,
  "examples": [...]
}
```

**POST /api/admin/personas/{persona_id}/test**
```json
{
  "input": "Test transcript...",
  "compare_with_version": 2  // Optional: compare with previous version
}
```

---

## 🎨 Diseño Visual

### 1. Personas List View

```tsx
// apps/aurity/app/admin/personas/page.tsx

export default function PersonasAdminPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Brain className="w-8 h-8 text-purple-400" />
            Gestión de AI Personas
          </h1>
          <p className="text-slate-400 mt-2">
            Configura y optimiza las personas médicas del sistema
          </p>
        </div>
        <Button variant="primary" onClick={() => setIsEditing(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nueva Persona
        </Button>
      </div>

      {/* Personas Grid */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        {personas.map((persona) => (
          <PersonaCard
            key={persona.id}
            persona={persona}
            isSelected={selectedPersona === persona.id}
            onClick={() => setSelectedPersona(persona.id)}
            onEdit={() => {
              setSelectedPersona(persona.id);
              setIsEditing(true);
            }}
          />
        ))}
      </div>

      {/* Editor Panel (Slide-over) */}
      {selectedPersona && isEditing && (
        <PersonaEditor
          personaId={selectedPersona}
          onClose={() => setIsEditing(false)}
          onSave={(updated) => {
            savePersona(updated);
            setIsEditing(false);
          }}
        />
      )}
    </div>
  );
}
```

### 2. Persona Card Component

```tsx
interface PersonaCardProps {
  persona: Persona;
  isSelected: boolean;
  onClick: () => void;
  onEdit: () => void;
}

function PersonaCard({ persona, isSelected, onClick, onEdit }: PersonaCardProps) {
  const colorByPersona = {
    soap_editor: 'emerald',
    clinical_advisor: 'blue',
    general_assistant: 'purple',
  };

  const color = colorByPersona[persona.id as keyof typeof colorByPersona] || 'slate';

  return (
    <div
      className={`p-6 rounded-xl border-2 cursor-pointer transition-all ${
        isSelected
          ? `border-${color}-500 bg-${color}-950/30`
          : `border-${color}-700/30 bg-${color}-950/10 hover:border-${color}-600`
      }`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-${color}-900 border border-${color}-700`}>
            <Brain className={`w-6 h-6 text-${color}-400`} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">{persona.name}</h3>
            <p className="text-xs text-slate-400">v{persona.version}</p>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="p-2 rounded hover:bg-slate-700 transition-colors"
        >
          <Edit className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-300 mb-4 line-clamp-2">
        {persona.description}
      </p>

      {/* Config Summary */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="p-2 bg-slate-800/50 rounded border border-slate-700">
          <div className="text-xs text-slate-500">Model</div>
          <div className="text-sm font-mono text-white">{persona.model}</div>
        </div>
        <div className="p-2 bg-slate-800/50 rounded border border-slate-700">
          <div className="text-xs text-slate-500">Temperature</div>
          <div className="text-sm font-mono text-white">{persona.temperature}</div>
        </div>
      </div>

      {/* Usage Stats */}
      <div className="pt-4 border-t border-slate-700">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Invocaciones</span>
          <span className="font-semibold text-white">
            {persona.usage_stats.total_invocations}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs mt-1">
          <span className="text-slate-500">Latencia Promedio</span>
          <span className="font-semibold text-white">
            {persona.usage_stats.avg_latency_ms}ms
          </span>
        </div>
        <div className="flex items-center justify-between text-xs mt-1">
          <span className="text-slate-500">Costo Promedio</span>
          <span className="font-semibold text-white">
            ${persona.usage_stats.avg_cost_usd.toFixed(4)}
          </span>
        </div>
      </div>

      {/* Last Updated */}
      <div className="mt-3 pt-3 border-t border-slate-700 text-xs text-slate-500">
        Actualizado: {formatDate(persona.last_updated)} por {persona.updated_by}
      </div>
    </div>
  );
}
```

### 3. Persona Editor (Slide-over Panel)

```tsx
interface PersonaEditorProps {
  personaId: string;
  onClose: () => void;
  onSave: (persona: Persona) => void;
}

function PersonaEditor({ personaId, onClose, onSave }: PersonaEditorProps) {
  const [persona, setPersona] = useState<Persona | null>(null);
  const [testInput, setTestInput] = useState('');
  const [testResult, setTestResult] = useState<any>(null);
  const [isTesting, setIsTesting] = useState(false);

  return (
    <SlideOver isOpen={true} onClose={onClose} width="extra-wide">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Brain className="w-7 h-7 text-purple-400" />
              Editar Persona: {persona?.name}
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Versión {persona?.version} · Última actualización: {formatDate(persona?.last_updated)}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button variant="primary" onClick={() => onSave(persona!)}>
              <Save className="w-4 h-4 mr-2" />
              Guardar Cambios
            </Button>
          </div>
        </div>

        {/* Form Sections */}
        <Tabs defaultValue="config">
          <TabsList>
            <TabsTrigger value="config">
              <Settings className="w-4 h-4 mr-2" />
              Configuración
            </TabsTrigger>
            <TabsTrigger value="prompt">
              <FileText className="w-4 h-4 mr-2" />
              System Prompt
            </TabsTrigger>
            <TabsTrigger value="examples">
              <List className="w-4 h-4 mr-2" />
              Examples
            </TabsTrigger>
            <TabsTrigger value="test">
              <Zap className="w-4 h-4 mr-2" />
              Probar
            </TabsTrigger>
          </TabsList>

          {/* Config Tab */}
          <TabsContent value="config">
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Nombre de Persona
                  </label>
                  <input
                    type="text"
                    className="w-full p-3 bg-slate-800 border border-slate-700 rounded-lg text-white"
                    value={persona?.name || ''}
                    onChange={(e) => setPersona({ ...persona!, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    ID Interno
                  </label>
                  <input
                    type="text"
                    className="w-full p-3 bg-slate-800 border border-slate-700 rounded-lg text-slate-500 font-mono"
                    value={persona?.id || ''}
                    disabled
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Descripción
                </label>
                <textarea
                  className="w-full p-3 bg-slate-800 border border-slate-700 rounded-lg text-white"
                  rows={3}
                  value={persona?.description || ''}
                  onChange={(e) => setPersona({ ...persona!, description: e.target.value })}
                  placeholder="Describe el propósito y especialización de esta persona..."
                />
              </div>

              {/* Model Selection */}
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Modelo LLM
                  </label>
                  <select
                    className="w-full p-3 bg-slate-800 border border-slate-700 rounded-lg text-white"
                    value={persona?.model || ''}
                    onChange={(e) => setPersona({ ...persona!, model: e.target.value })}
                  >
                    <option value="gpt-4o">GPT-4o (Más preciso, $$$)</option>
                    <option value="gpt-4o-mini">GPT-4o-mini (Balance, $$)</option>
                    <option value="claude-3-5-sonnet">Claude 3.5 Sonnet ($$$)</option>
                    <option value="claude-3-haiku">Claude 3 Haiku ($)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    className="w-full p-3 bg-slate-800 border border-slate-700 rounded-lg text-white font-mono"
                    value={persona?.max_tokens || 0}
                    onChange={(e) => setPersona({ ...persona!, max_tokens: parseInt(e.target.value) })}
                  />
                </div>
              </div>

              {/* Temperature Slider */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Temperature: {persona?.temperature?.toFixed(2)}
                  <span className="text-xs text-slate-500 ml-2">
                    ({persona?.temperature < 0.3 ? 'Determinístico' : persona?.temperature < 0.7 ? 'Balanceado' : 'Creativo'})
                  </span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  className="w-full"
                  value={persona?.temperature || 0}
                  onChange={(e) => setPersona({ ...persona!, temperature: parseFloat(e.target.value) })}
                />
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>0.0 (Preciso)</span>
                  <span>0.5 (Balance)</span>
                  <span>1.0 (Creativo)</span>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Prompt Tab */}
          <TabsContent value="prompt">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-300">
                  System Prompt
                </label>
                <div className="flex gap-2">
                  <Badge variant="blue">
                    {persona?.system_prompt?.length || 0} caracteres
                  </Badge>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      // Load template
                      const template = getPersonaTemplate(persona?.id);
                      setPersona({ ...persona!, system_prompt: template });
                    }}
                  >
                    <RefreshCw className="w-3 h-3 mr-1" />
                    Cargar Template
                  </Button>
                </div>
              </div>

              {/* Prompt Editor with Syntax Highlighting */}
              <div className="relative">
                <textarea
                  className="w-full p-4 bg-slate-900 border border-slate-700 rounded-lg text-white font-mono text-sm leading-relaxed"
                  rows={20}
                  value={persona?.system_prompt || ''}
                  onChange={(e) => setPersona({ ...persona!, system_prompt: e.target.value })}
                  placeholder="Eres un médico experto en..."
                  spellCheck={false}
                />

                {/* Helper Buttons */}
                <div className="absolute top-2 right-2 flex gap-2">
                  <button
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400"
                    title="Copiar"
                    onClick={() => navigator.clipboard.writeText(persona?.system_prompt || '')}
                  >
                    <Copy className="w-3 h-3" />
                  </button>
                  <button
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400"
                    title="Formatear"
                    onClick={() => {
                      // Auto-format prompt
                      const formatted = formatPrompt(persona?.system_prompt || '');
                      setPersona({ ...persona!, system_prompt: formatted });
                    }}
                  >
                    <Code className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Prompt Guidelines */}
              <div className="p-4 bg-blue-950/20 border border-blue-900 rounded-lg">
                <h4 className="text-sm font-semibold text-blue-400 mb-2">
                  📝 Mejores Prácticas para System Prompts
                </h4>
                <ul className="text-xs text-slate-300 space-y-1">
                  <li>• Especifica el rol claramente ("Eres un médico experto en...")</li>
                  <li>• Define el formato de salida esperado (JSON, texto, estructura)</li>
                  <li>• Incluye restricciones ("No diagnostiques sin datos objetivos")</li>
                  <li>• Usa ejemplos en el prompt para claridad (few-shot learning)</li>
                  <li>• Mantén el prompt {"<"} 1000 caracteres para latencia óptima</li>
                </ul>
              </div>
            </div>
          </TabsContent>

          {/* Examples Tab */}
          <TabsContent value="examples">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-300">
                  Few-Shot Examples ({persona?.examples?.length || 0})
                </label>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    const newExample = { input: '', output: '' };
                    setPersona({
                      ...persona!,
                      examples: [...(persona?.examples || []), newExample],
                    });
                  }}
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Agregar Example
                </Button>
              </div>

              {/* Examples List */}
              <div className="space-y-4">
                {persona?.examples?.map((example, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-semibold text-slate-300">
                        Example {idx + 1}
                      </span>
                      <button
                        onClick={() => {
                          const updated = persona.examples.filter((_, i) => i !== idx);
                          setPersona({ ...persona, examples: updated });
                        }}
                        className="p-1 rounded hover:bg-red-900 text-red-400"
                      >
                        <Trash className="w-3 h-3" />
                      </button>
                    </div>

                    {/* Input */}
                    <div className="mb-3">
                      <label className="block text-xs text-slate-500 mb-1">
                        Input (Usuario)
                      </label>
                      <textarea
                        className="w-full p-2 bg-slate-900 border border-slate-600 rounded text-white font-mono text-xs"
                        rows={3}
                        value={example.input}
                        onChange={(e) => {
                          const updated = [...persona.examples];
                          updated[idx].input = e.target.value;
                          setPersona({ ...persona, examples: updated });
                        }}
                        placeholder="Ej: Paciente con fiebre de 3 días..."
                      />
                    </div>

                    {/* Output */}
                    <div>
                      <label className="block text-xs text-slate-500 mb-1">
                        Output (Persona)
                      </label>
                      <textarea
                        className="w-full p-2 bg-slate-900 border border-slate-600 rounded text-white font-mono text-xs"
                        rows={5}
                        value={typeof example.output === 'string' ? example.output : JSON.stringify(example.output, null, 2)}
                        onChange={(e) => {
                          const updated = [...persona.examples];
                          try {
                            updated[idx].output = JSON.parse(e.target.value);
                          } catch {
                            updated[idx].output = e.target.value;
                          }
                          setPersona({ ...persona, examples: updated });
                        }}
                        placeholder='{"subjective": "...", "objective": "..."}'
                      />
                    </div>
                  </div>
                ))}
              </div>

              {persona?.examples?.length === 0 && (
                <div className="p-8 text-center text-slate-500">
                  <List className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No hay examples configurados.</p>
                  <p className="text-sm">Los examples mejoran la precisión de la persona (few-shot learning).</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Test Tab */}
          <TabsContent value="test">
            <div className="space-y-6">
              {/* Test Input */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Test Input
                </label>
                <textarea
                  className="w-full p-4 bg-slate-900 border border-slate-700 rounded-lg text-white font-mono text-sm"
                  rows={8}
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  placeholder="Ingresa un input de prueba (ej: transcripción médica)..."
                />
              </div>

              {/* Test Button */}
              <div className="flex items-center gap-3">
                <Button
                  variant="primary"
                  onClick={async () => {
                    setIsTesting(true);
                    const result = await testPersona(persona!.id, testInput);
                    setTestResult(result);
                    setIsTesting(false);
                  }}
                  disabled={!testInput || isTesting}
                >
                  {isTesting ? (
                    <>
                      <Loader className="w-4 h-4 mr-2 animate-spin" />
                      Probando...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 mr-2" />
                      Probar Persona
                    </>
                  )}
                </Button>

                {persona?.version > 1 && (
                  <Button
                    variant="secondary"
                    onClick={async () => {
                      setIsTesting(true);
                      const result = await testPersona(persona.id, testInput, persona.version - 1);
                      setTestResult(result);
                      setIsTesting(false);
                    }}
                    disabled={!testInput || isTesting}
                  >
                    <GitCompare className="w-4 h-4 mr-2" />
                    Comparar con v{persona.version - 1}
                  </Button>
                )}
              </div>

              {/* Test Result */}
              {testResult && (
                <div className="p-6 bg-slate-900 border-2 border-green-700 rounded-xl">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-green-400">
                      ✓ Resultado del Test
                    </h3>
                    <div className="flex gap-4 text-xs text-slate-400">
                      <span>Latencia: {testResult.latency_ms}ms</span>
                      <span>Tokens: {testResult.tokens_used}</span>
                      <span>Costo: ${testResult.cost_usd.toFixed(4)}</span>
                    </div>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-700">
                    <pre className="text-sm text-white whitespace-pre-wrap font-mono">
                      {typeof testResult.output === 'string'
                        ? testResult.output
                        : JSON.stringify(testResult.output, null, 2)}
                    </pre>
                  </div>

                  {/* Comparison (if testing previous version) */}
                  {testResult.comparison && (
                    <div className="mt-4 p-4 bg-blue-950/20 border border-blue-900 rounded-lg">
                      <h4 className="text-sm font-semibold text-blue-400 mb-2">
                        Comparación con v{persona.version - 1}
                      </h4>
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <div className="text-slate-500 mb-1">Versión Anterior</div>
                          <div className="text-slate-300">{testResult.comparison.diff_summary}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 mb-1">Versión Actual</div>
                          <div className="text-slate-300">{testResult.comparison.improvement_score}% mejor</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Version History */}
        <div className="pt-6 border-t border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            Historial de Versiones
          </h3>
          <div className="space-y-2">
            {persona?.version_history?.map((version, idx) => (
              <div
                key={idx}
                className="p-3 bg-slate-800 rounded-lg border border-slate-700 flex items-center justify-between"
              >
                <div>
                  <span className="text-sm font-mono text-white">v{version.number}</span>
                  <span className="text-xs text-slate-500 ml-3">
                    {formatDate(version.created_at)} por {version.updated_by}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-white"
                    onClick={() => {
                      // Rollback to this version
                      rollbackToVersion(persona.id, version.number);
                    }}
                  >
                    Restaurar
                  </button>
                  <button
                    className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-white"
                    onClick={() => {
                      // View diff
                      showVersionDiff(persona.id, version.number);
                    }}
                  >
                    Ver Cambios
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SlideOver>
  );
}
```

---

## 📡 API Endpoints (Backend)

### 1. List Personas
`GET /api/admin/personas`

```python
@router.get("/admin/personas")
async def list_personas() -> dict:
    """Get all available personas with usage stats."""
    from backend.services.llm.persona_manager import get_persona_manager

    persona_mgr = get_persona_manager()
    personas = persona_mgr.get_all_personas()

    # Enrich with usage stats from HDF5
    for persona_id, persona_data in personas.items():
        stats = get_persona_usage_stats(persona_id)
        persona_data["usage_stats"] = stats

    return {"personas": list(personas.values())}
```

### 2. Get Single Persona
`GET /api/admin/personas/{persona_id}`

```python
@router.get("/admin/personas/{persona_id}")
async def get_persona(persona_id: str) -> dict:
    """Get single persona with full details."""
    persona_mgr = get_persona_manager()
    persona = persona_mgr.get_persona(persona_id)

    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")

    # Get version history
    version_history = get_persona_version_history(persona_id)

    return {
        **persona,
        "version_history": version_history,
    }
```

### 3. Update Persona
`PUT /api/admin/personas/{persona_id}`

```python
class UpdatePersonaRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    examples: list[dict] | None = None

@router.put("/admin/personas/{persona_id}")
async def update_persona(
    persona_id: str,
    request: UpdatePersonaRequest,
    updated_by: str = "Dr. Uriza",  # From auth context
) -> dict:
    """Update persona configuration and increment version."""
    persona_mgr = get_persona_manager()

    # Get current persona
    current = persona_mgr.get_persona(persona_id)
    if not current:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")

    # Create new version
    new_version = current.get("version", 1) + 1

    # Merge updates
    updated = {
        **current,
        **request.dict(exclude_none=True),
        "version": new_version,
        "last_updated": datetime.now(UTC).isoformat(),
        "updated_by": updated_by,
    }

    # Save to HDF5 (versioned)
    save_persona_version(persona_id, updated)

    # Reload persona manager cache
    persona_mgr.reload()

    logger.info(
        "PERSONA_UPDATED",
        persona_id=persona_id,
        version=new_version,
        updated_by=updated_by,
    )

    return updated
```

### 4. Test Persona
`POST /api/admin/personas/{persona_id}/test`

```python
class TestPersonaRequest(BaseModel):
    input: str
    compare_with_version: int | None = None

@router.post("/admin/personas/{persona_id}/test")
async def test_persona(
    persona_id: str,
    request: TestPersonaRequest,
) -> dict:
    """Test persona with sample input."""
    from backend.services.llm.llm_client import LLMClient
    import time

    persona_mgr = get_persona_manager()
    persona = persona_mgr.get_persona(persona_id)

    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")

    # Run test
    start_time = time.time()
    client = LLMClient(provider=persona["model"].split("-")[0])  # Extract provider
    result = client.chat(
        messages=[{"role": "user", "content": request.input}],
        system_prompt=persona["system_prompt"],
        temperature=persona["temperature"],
        max_tokens=persona["max_tokens"],
    )
    latency_ms = int((time.time() - start_time) * 1000)

    # Calculate cost (simplified)
    tokens_used = len(request.input.split()) + len(str(result).split())
    cost_usd = calculate_cost(persona["model"], tokens_used)

    response = {
        "persona_id": persona_id,
        "version": persona["version"],
        "output": result,
        "latency_ms": latency_ms,
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
    }

    # Comparison with previous version (if requested)
    if request.compare_with_version:
        old_persona = get_persona_version(persona_id, request.compare_with_version)
        old_result = client.chat(
            messages=[{"role": "user", "content": request.input}],
            system_prompt=old_persona["system_prompt"],
            temperature=old_persona["temperature"],
            max_tokens=old_persona["max_tokens"],
        )

        # Diff comparison
        diff_summary = compare_outputs(old_result, result)
        improvement_score = calculate_improvement_score(old_result, result)

        response["comparison"] = {
            "diff_summary": diff_summary,
            "improvement_score": improvement_score,
        }

    return response
```

---

## 🎯 Resultado Visual (Mockup)

### Personas Admin Page:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🧠 Gestión de AI Personas                         [+ Nueva Persona] │
│ Configura y optimiza las personas médicas del sistema               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐        │
│ │ 🧠 SOAP Editor   │ │ 🧠 Clinical     │ │ 🧠 General      │        │
│ │ v3              │ │    Advisor v2   │ │    Assistant v1 │        │
│ │                 │ │                 │ │                 │        │
│ │ Extrae notas... │ │ Valida preci... │ │ Asistente con...│        │
│ │                 │ │                 │ │                 │        │
│ │ Model: gpt-4o-  │ │ Model: gpt-4o   │ │ Model: gpt-4o-  │        │
│ │ Temp: 0.2       │ │ Temp: 0.1       │ │ Temp: 0.7       │        │
│ │                 │ │                 │ │                 │        │
│ │ Invocaciones:145│ │ Invocaciones:67 │ │ Invocaciones:234│        │
│ │ Latencia: 3200ms│ │ Latencia: 4500ms│ │ Latencia: 1200ms│        │
│ │ Costo: $0.015   │ │ Costo: $0.032   │ │ Costo: $0.008   │        │
│ │                 │ │                 │ │                 │        │
│ │ 2025-11-18 Dr.U │ │ 2025-11-15 Dr.U │ │ 2025-11-10 Dr.U │        │
│ │            [✏️]  │ │            [✏️]  │ │            [✏️]  │        │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘

[Click SOAP Editor] → Opens Editor Panel:

┌─────────────────────────────────────────────────────────────────────┐
│ 🧠 Editar Persona: SOAP Editor                    [Cancelar] [Guardar]│
│ Versión 3 · Última actualización: 2025-11-18 10:30                  │
├─────────────────────────────────────────────────────────────────────┤
│ [Configuración] [System Prompt] [Examples] [Probar]                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ System Prompt                              3456 caracteres [Template]│
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Eres un médico experto en documentación clínica.               │ │
│ │                                                                 │ │
│ │ Tu tarea es extraer notas SOAP de transcripciones médicas...   │ │
│ │                                                                 │ │
│ │ Formato de salida:                                              │ │
│ │ {                                                               │ │
│ │   "subjective": "...",                                          │ │
│ │   "objective": "...",                                           │ │
│ │   ...                                                           │ │
│ │ }                                                               │ │
│ │                                                           [📋][⚡]│ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ 📝 Mejores Prácticas para System Prompts                            │
│  • Especifica el rol claramente                                     │
│  • Define el formato de salida esperado                             │
│  • Incluye restricciones                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📝 Beneficios

1. **Prompt Engineering UI**: No más edits manuales en código
2. **A/B Testing**: Comparar versiones de prompts fácilmente
3. **Version Control**: Rollback a versiones anteriores si algo falla
4. **Usage Analytics**: Ver qué personas son más usadas/costosas
5. **Rapid Iteration**: Probar cambios sin redeploy

---

## 🔮 Futuras Mejoras

- **Prompt Templates Library**: Templates pre-built para casos comunes
- **Auto-Optimization**: ML que sugiere mejoras al prompt basado en feedback
- **Cost Alerts**: Notificar si una persona está consumiendo mucho $$
- **Playground Mode**: Test interactivo tipo OpenAI Playground
- **Export/Import**: Compartir personas entre instancias de FI

---

**Status:** Design Complete ✅
**Next Step:** Implement backend endpoints + frontend components
