import { useState } from 'react';
import { LLMTestingPanel } from './test-suite/panels/LLMTestingPanel';
import { RAGTestingPanel } from './test-suite/panels/RAGTestingPanel';

/**
 * TestSuiteLibrary - Orchestrator Component
 *
 * Single responsibility: Switch between LLM and RAG testing modes.
 * All testing logic delegated to specialized panels.
 */
export function TestSuiteLibrary() {
  const [testMode, setTestMode] = useState<'llm' | 'rag'>('llm');

  return (
    <div className="test-suite-library">
      {/* Mode Switch */}
      <div className="test-mode-switch">
        <button
          className={testMode === 'llm' ? 'active' : ''}
          onClick={() => setTestMode('llm')}
        >
          🤖 Test LLM
        </button>
        <button
          className={testMode === 'rag' ? 'active' : ''}
          onClick={() => setTestMode('rag')}
        >
          📚 Test RAG
        </button>
      </div>

      {/* Panel Rendering */}
      {testMode === 'llm' ? <LLMTestingPanel /> : <RAGTestingPanel />}
    </div>
  );
}
