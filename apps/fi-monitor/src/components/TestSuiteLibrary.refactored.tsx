// Test Suite Library - Refactored Orchestrator
import { useState } from 'react'
import { LLMTestingPanel } from './test-suite/panels/LLMTestingPanel'
import { RAGTestingPanel } from './test-suite/panels/RAGTestingPanel'

export function TestSuiteLibrary() {
  const [testMode, setTestMode] = useState<'llm' | 'rag'>('llm')

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

      {/* Render selected panel */}
      {testMode === 'llm' ? <LLMTestingPanel /> : <RAGTestingPanel />}
    </div>
  )
}
