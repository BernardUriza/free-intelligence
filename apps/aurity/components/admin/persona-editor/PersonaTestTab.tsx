/**
 * PersonaTestTab - Persona Testing Interface
 *
 * Test persona with sample inputs and view results
 */

import { useState } from 'react';
import type { PersonaTestResponse } from '@aurity-standalone/types/persona';
import { testPersona } from '@aurity-standalone/api-client/personas';
import { Zap } from 'lucide-react';
import { toastError } from '@/lib/swal';
import { Button } from '@/components/ui/button';

interface PersonaTestTabProps {
  personaId: string;
}

export function PersonaTestTab({ personaId }: PersonaTestTabProps) {
  const [testInput, setTestInput] = useState('');
  const [testResult, setTestResult] = useState<PersonaTestResponse | null>(null);
  const [testing, setTesting] = useState(false);

  const handleTest = async () => {
    if (!testInput.trim()) return;

    try {
      setTesting(true);
      const result = await testPersona(personaId, { input: testInput });
      setTestResult(result);
    } catch (error) {
      console.error('Failed to test persona:', error);
      toastError('Error al probar la persona');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="mb-4">
        <h3 className="fi-title mb-2">Probar Persona</h3>
        <p className="fi-subtitle">
          Prueba la persona con un input de ejemplo para ver cómo responde
        </p>
      </div>

      <div>
        <label className="fi-label">
          Input de Prueba
        </label>
        <textarea
          className="w-full p-4 fi-panel text-white focus:border-purple-500 focus:outline-none"
          rows={6}
          value={testInput}
          onChange={(e) => setTestInput(e.target.value)}
          placeholder="Ingresa un caso de prueba..."
        />
      </div>

      <Button
        onClick={handleTest}
        disabled={testing || !testInput.trim()}
        variant="purple"
        size="lg"
        fullWidth
        icon={Zap}
        loading={testing}
      >
        {testing ? 'Probando...' : 'Probar Persona'}
      </Button>

      {testResult && (
        <div className="mt-6 p-4 fi-panel">
          <h4 className="fi-title-sm mb-3">Resultado</h4>
          <pre className="admin-code-preview">
            {JSON.stringify(testResult.output, null, 2)}
          </pre>
          <div className="mt-4 fi-grid-3 text-sm">
            <div>
              <span className="text-slate-500">Latencia:</span>{' '}
              <span className="text-white font-semibold">
                {testResult.latency_ms.toFixed(0)}ms
              </span>
            </div>
            <div>
              <span className="text-slate-500">Tokens:</span>{' '}
              <span className="text-white font-semibold">
                {testResult.tokens_used}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Costo:</span>{' '}
              <span className="text-white font-semibold">
                ${testResult.cost_usd.toFixed(4)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
