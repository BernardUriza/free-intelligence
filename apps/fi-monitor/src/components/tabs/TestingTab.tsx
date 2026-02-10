import { TestSuiteLibrary } from '../TestSuiteLibrary'
import type { TestResult } from '../../types/monitor'

interface TestingTabProps {
  ollamaOn: boolean
  testResult: TestResult | null
  actionLoading: string | null
  autoTest: boolean
  setAutoTest: (v: boolean) => void
  nextTestIn: number
  handleTestOllama: () => void
  handleTestLLMHealth: () => void
}

export function TestingTab({
  ollamaOn,
  testResult,
  actionLoading,
  autoTest,
  setAutoTest,
  nextTestIn,
  handleTestOllama,
  handleTestLLMHealth,
}: TestingTabProps) {
  return (
    <div className="p-4">
      <div className="test-section">
        <div className="test-header">
          <div className="test-title">
            <span className="icon">{'\u{1F9EA}'}</span>
            <span>Test LLM</span>
          </div>
          <div className="test-controls">
            <label className="auto-toggle" title="Auto-test cada 60s">
              <input type="checkbox" checked={autoTest} onChange={() => setAutoTest(!autoTest)} disabled={!ollamaOn} />
              <span className="timer">{autoTest ? `${nextTestIn}s` : 'Auto'}</span>
            </label>
            <button className="test-btn" onClick={handleTestOllama} disabled={actionLoading === 'test' || !ollamaOn}>
              {actionLoading === 'test' ? '\u23F3' : '\u25B6'}
            </button>
          </div>
        </div>

        {testResult ? (
          <div className="test-result">
            <div className="result-header">
              <span className={`cat ${testResult.category}`}>{testResult.category === 'math' ? '\u{1F522}' : '\u{1FAC0}'}</span>
              <span className="time">{testResult.elapsed_ms}ms</span>
            </div>
            <div className="result-q">{testResult.question}</div>
            <div className="result-a">{testResult.answer}</div>
          </div>
        ) : (
          <div className="test-placeholder">{ollamaOn ? 'Presiona \u25B6 para probar' : 'Inicia Ollama primero'}</div>
        )}
      </div>

      {/* Smoke Test (Quick Health Check) */}
      <div className="test-section mt-4">
        <div className="test-header">
          <div className="test-title">
            <span className="icon">{'\u{1F52C}'}</span>
            <span>Smoke Test (Health Check)</span>
          </div>
          <button
            className="test-btn"
            onClick={handleTestLLMHealth}
            disabled={actionLoading === 'smoke-test' || !ollamaOn}
            title="Quick 2+2 test to verify LLM is responding (works in browser mode)"
          >
            {actionLoading === 'smoke-test' ? '\u23F3' : '\u25B6'}
          </button>
        </div>
        <div className="test-placeholder text-sm text-gray-400">
          {ollamaOn ? 'Quick sanity check: asks LLM "What is 2+2?" (HTTP direct, works everywhere)' : 'Start Ollama first'}
        </div>
      </div>

      {/* Test Suite Library */}
      <TestSuiteLibrary />
    </div>
  )
}
