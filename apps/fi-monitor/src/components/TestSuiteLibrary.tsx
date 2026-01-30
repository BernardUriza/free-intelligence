// Test Suite Library for comprehensive testing
import { useState, useEffect } from 'react'
import { invoke, isTauriContext } from '../lib/tauri-adapter'

interface Test {
  id: string
  question: string
  expectedAnswer?: string
  category: 'math' | 'medical' | 'general' | 'custom'
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  createdAt: string
}

interface TestResult {
  testId: string
  answer: string
  elapsed_ms: number
  timestamp: string
  passed?: boolean
  score?: number
}

export function TestSuiteLibrary() {
  const [testMode, setTestMode] = useState<'llm' | 'rag'>('llm')
  const [ragQuestion, setRagQuestion] = useState('')
  const [ragResult, setRagResult] = useState<any>(null)
  const [ragRunning, setRagRunning] = useState(false)
  const [ragServiceStatus, setRagServiceStatus] = useState<'checking' | 'running' | 'stopped'>('checking')
  const [ragServiceStarting, setRagServiceStarting] = useState(false)
  const [selectedPDF, setSelectedPDF] = useState<File | null>(null)
  const [pdfProcessing, setPdfProcessing] = useState(false)
  const [pdfProcessed, setPdfProcessed] = useState(false)

  const [tests, setTests] = useState<Test[]>([])
  const [results, setResults] = useState<Map<string, TestResult>>(new Map())
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [showAddForm, setShowAddForm] = useState(false)
  const [runningTests, setRunningTests] = useState<Set<string>>(new Set())
  const [bulkRunning, setBulkRunning] = useState(false)

  // Form state
  const [newTest, setNewTest] = useState<Partial<Test>>({
    question: '',
    expectedAnswer: '',
    category: 'general',
    difficulty: 'medium',
    tags: []
  })

  useEffect(() => {
    loadTests()
  }, [])

  // Check RAG Service status when switching to RAG mode
  useEffect(() => {
    if (testMode === 'rag') {
      checkRagServiceStatus()
    }
  }, [testMode])

  const checkRagServiceStatus = async () => {
    setRagServiceStatus('checking')
    try {
      if (isTauriContext()) {
        // Native mode: use Tauri command
        await invoke('get_rag_stats')
        setRagServiceStatus('running')
      } else {
        // Browser mode: HTTP fallback
        const response = await fetch('http://localhost:11435/rag/health', {
          signal: AbortSignal.timeout(2000)
        })
        if (response.ok) {
          setRagServiceStatus('running')
        } else {
          setRagServiceStatus('stopped')
        }
      }
    } catch (err) {
      console.error('[RAG] Service not running:', err)
      setRagServiceStatus('stopped')
    }
  }

  const startRagServiceManually = async () => {
    setRagServiceStarting(true)
    try {
      await invoke('start_rag_service')
      setRagServiceStatus('running')
    } catch (err) {
      console.error('[RAG] Failed to start service:', err)
      alert(`Failed to start RAG Service: ${err}`)
    } finally {
      setRagServiceStarting(false)
    }
  }

  const handlePDFUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file && file.type === 'application/pdf') {
      setSelectedPDF(file)
      setPdfProcessed(false)
    } else if (file) {
      alert('Please select a PDF file')
    }
  }

  const loadSamplePDF = async (filename: string, displayName: string) => {
    try {
      // Fetch the sample PDF from public folder
      const response = await fetch(`/test-pdfs/${filename}`)
      if (!response.ok) {
        throw new Error(`Failed to load ${displayName}: ${response.statusText}`)
      }

      // Convert to Blob
      const blob = await response.blob()

      // Create File object (browsers need File, not just Blob)
      const file = new File([blob], displayName, { type: 'application/pdf' })

      // Set as selected PDF (ready to process)
      setSelectedPDF(file)
      setPdfProcessed(false)

      console.log(`[RAG] ✅ Loaded sample PDF: ${displayName} (${(blob.size / 1024).toFixed(1)} KB)`)

    } catch (err) {
      console.error('[RAG] Failed to load sample PDF:', err)
      alert(`Failed to load sample PDF: ${err}`)
    }
  }

  const processPDF = async () => {
    if (!selectedPDF) return

    setPdfProcessing(true)
    try {
      // Phase 3: Clear old documents before processing new one
      try {
        await fetch('http://localhost:11435/rag/documents', {
          method: 'DELETE',
          headers: {
            'X-API-Key': 'change-me-in-production'
          }
        })
        console.log('[RAG] Cleared old documents from store')
      } catch (err) {
        // Ignore errors - document store might be empty
        console.log('[RAG] No old documents to clear:', err)
      }

      // Read PDF file as base64
      const reader = new FileReader()

      reader.onload = async () => {
        try {
          const base64Content = reader.result as string

          // Call RAG service to process PDF
          const response = await fetch('http://localhost:11435/rag/upload', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': 'change-me-in-production'  // Default RAG Service API key
            },
            body: JSON.stringify({
              filename: selectedPDF.name,
              content: base64Content.split(',')[1] // Remove data:application/pdf;base64, prefix
            })
          })

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`)
          }

          const result = await response.json()
          console.log('[RAG] PDF processed:', result)
          setPdfProcessed(true)
        } catch (err) {
          console.error('[RAG] Failed to process PDF:', err)
          alert(`Failed to process PDF: ${err}`)
        } finally {
          setPdfProcessing(false)
        }
      }

      reader.onerror = () => {
        alert('Failed to read PDF file')
        setPdfProcessing(false)
      }

      reader.readAsDataURL(selectedPDF)
    } catch (err) {
      console.error('[RAG] PDF processing error:', err)
      alert(`Error: ${err}`)
      setPdfProcessing(false)
    }
  }

  const loadTests = async () => {
    // 🛡️ GUARD: Solo ejecutar en contexto Tauri
    if (!isTauriContext()) {
      console.warn('[TestSuiteLibrary] Not in Tauri context, using empty test list')
      setTests([])
      return
    }

    try {
      const loadedTests = await invoke<Test[]>('get_test_suite')
      setTests(loadedTests)
    } catch (err) {
      const errorStr = String(err)

      // 🛡️ Handle gracefully si command no existe
      if (errorStr.includes('not found') || errorStr.includes('Command get_test_suite')) {
        console.warn('[TestSuiteLibrary] get_test_suite command not implemented yet, using empty list')
        setTests([])  // Empty state, NO crash
      } else {
        console.error('[TestSuiteLibrary] Failed to load tests:', err)
      }
    }
  }

  const addTest = async () => {
    if (!newTest.question?.trim()) return

    try {
      const test: Test = {
        id: Date.now().toString(),
        question: newTest.question,
        expectedAnswer: newTest.expectedAnswer,
        category: newTest.category || 'general',
        difficulty: newTest.difficulty || 'medium',
        tags: newTest.tags || [],
        createdAt: new Date().toISOString()
      }

      await invoke('save_test', { test })
      setTests([...tests, test])
      setNewTest({
        question: '',
        expectedAnswer: '',
        category: 'general',
        difficulty: 'medium',
        tags: []
      })
      setShowAddForm(false)
    } catch (err) {
      console.error('[TestSuiteLibrary] Failed to add test:', err)
    }
  }

  const runTest = async (test: Test) => {
    setRunningTests(prev => new Set(prev).add(test.id))

    try {
      const result = await invoke<any>('test_ollama', {
        category: test.category,
        question: test.question
      })

      const testResult: TestResult = {
        testId: test.id,
        answer: result.answer,
        elapsed_ms: result.elapsed_ms,
        timestamp: result.timestamp,
        passed: test.expectedAnswer
          ? result.answer.toLowerCase().includes(test.expectedAnswer.toLowerCase())
          : undefined,
        score: test.expectedAnswer ? calculateScore(result.answer, test.expectedAnswer) : undefined
      }

      setResults(prev => new Map(prev).set(test.id, testResult))
    } catch (err) {
      console.error('[TestSuiteLibrary] Test failed:', err)
    } finally {
      setRunningTests(prev => {
        const next = new Set(prev)
        next.delete(test.id)
        return next
      })
    }
  }

  const runAllInCategory = async () => {
    setBulkRunning(true)
    const testsToRun = filteredTests

    for (const test of testsToRun) {
      await runTest(test)
    }

    setBulkRunning(false)
  }

  const deleteTest = async (testId: string) => {
    if (!confirm('Delete this test?')) return

    try {
      await invoke('delete_test', { testId })
      setTests(tests.filter(t => t.id !== testId))
      setResults(prev => {
        const next = new Map(prev)
        next.delete(testId)
        return next
      })
    } catch (err) {
      console.error('[TestSuiteLibrary] Failed to delete test:', err)
    }
  }

  const duplicateTest = (test: Test) => {
    setNewTest({
      question: test.question + ' (copy)',
      expectedAnswer: test.expectedAnswer,
      category: test.category,
      difficulty: test.difficulty,
      tags: [...test.tags]
    })
    setShowAddForm(true)
  }

  const calculateScore = (answer: string, expected: string): number => {
    const answerLower = answer.toLowerCase()
    const expectedLower = expected.toLowerCase()

    if (answerLower.includes(expectedLower)) return 100

    // Simple word overlap score
    const answerWords = answerLower.split(/\s+/)
    const expectedWords = expectedLower.split(/\s+/)
    const overlap = expectedWords.filter(w => answerWords.includes(w)).length

    return Math.round((overlap / expectedWords.length) * 100)
  }

  const filteredTests = selectedCategory === 'all'
    ? tests
    : tests.filter(t => t.category === selectedCategory)

  const categoryIcons = {
    math: '🔢',
    medical: '🏥',
    general: '💬',
    custom: '⚙️'
  }

  const categoryColors = {
    math: '#2196f3',
    medical: '#f44336',
    general: '#4caf50',
    custom: '#ff9800'
  }

  const difficultyColors = {
    easy: '#4caf50',
    medium: '#ff9800',
    hard: '#f44336'
  }

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

      {testMode === 'llm' ? (
        <>
      {/* Header */}
      <div className="test-suite-header">
        <h3>Test Suite Library</h3>
        <div className="test-suite-actions">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="add-test-btn"
          >
            {showAddForm ? '✕ Cancel' : '+ Add Test'}
          </button>

          {filteredTests.length > 0 && (
            <button
              onClick={runAllInCategory}
              disabled={bulkRunning}
              className="bulk-run-btn"
            >
              {bulkRunning ? '⏳ Running...' : `▶ Run All (${filteredTests.length})`}
            </button>
          )}
        </div>
      </div>

      {/* Category Filter */}
      <div className="category-filter">
        {['all', 'math', 'medical', 'general', 'custom'].map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={selectedCategory === cat ? 'active' : ''}
          >
            {cat === 'all' ? '📚 All' : `${categoryIcons[cat as keyof typeof categoryIcons]} ${cat.charAt(0).toUpperCase() + cat.slice(1)}`}
            <span className="count">
              ({cat === 'all' ? tests.length : tests.filter(t => t.category === cat).length})
            </span>
          </button>
        ))}
      </div>

      {/* Add Test Form */}
      {showAddForm && (
        <div className="add-test-form">
          <h4>New Test</h4>

          <label>Question *</label>
          <textarea
            value={newTest.question}
            onChange={(e) => setNewTest({ ...newTest, question: e.target.value })}
            placeholder="Enter test question..."
            rows={3}
          />

          <label>Expected Answer (optional)</label>
          <input
            type="text"
            value={newTest.expectedAnswer}
            onChange={(e) => setNewTest({ ...newTest, expectedAnswer: e.target.value })}
            placeholder="Expected answer for automated scoring..."
          />

          <div className="form-row">
            <div>
              <label>Category</label>
              <select
                value={newTest.category}
                onChange={(e) => setNewTest({ ...newTest, category: e.target.value as any })}
              >
                <option value="general">General</option>
                <option value="math">Math</option>
                <option value="medical">Medical</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            <div>
              <label>Difficulty</label>
              <select
                value={newTest.difficulty}
                onChange={(e) => setNewTest({ ...newTest, difficulty: e.target.value as any })}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <label>Tags (comma-separated)</label>
          <input
            type="text"
            value={newTest.tags?.join(', ')}
            onChange={(e) => setNewTest({
              ...newTest,
              tags: e.target.value.split(',').map(t => t.trim()).filter(Boolean)
            })}
            placeholder="spanish, reasoning, factual..."
          />

          <div className="form-actions">
            <button onClick={addTest} className="save-btn">
              💾 Save Test
            </button>
            <button onClick={() => setShowAddForm(false)} className="cancel-btn">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Test Grid */}
      <div className="test-grid">
        {filteredTests.length === 0 ? (
          <div className="empty-state">
            <p>No tests in this category yet.</p>
            <button onClick={() => setShowAddForm(true)}>+ Add First Test</button>
          </div>
        ) : (
          filteredTests.map(test => {
            const result = results.get(test.id)
            const isRunning = runningTests.has(test.id)

            return (
              <div
                key={test.id}
                className="test-card"
                style={{ borderLeftColor: categoryColors[test.category] }}
              >
                <div className="test-card-header">
                  <span className="test-category">
                    {categoryIcons[test.category]} {test.category}
                  </span>
                  <span
                    className="test-difficulty"
                    style={{ color: difficultyColors[test.difficulty] }}
                  >
                    {test.difficulty}
                  </span>
                </div>

                <div className="test-question">{test.question}</div>

                {test.tags.length > 0 && (
                  <div className="test-tags">
                    {test.tags.map(tag => (
                      <span key={tag} className="tag">{tag}</span>
                    ))}
                  </div>
                )}

                {result && (
                  <div className="test-result">
                    <div className="result-header">
                      {result.passed !== undefined && (
                        <span className={result.passed ? 'passed' : 'failed'}>
                          {result.passed ? '✓ PASSED' : '✗ FAILED'}
                          {result.score !== undefined && ` (${result.score}%)`}
                        </span>
                      )}
                      <span className="result-time">{result.elapsed_ms}ms</span>
                    </div>
                    <div className="result-answer">{result.answer}</div>
                  </div>
                )}

                <div className="test-actions">
                  <button
                    onClick={() => runTest(test)}
                    disabled={isRunning || bulkRunning}
                    className="run-btn"
                  >
                    {isRunning ? '⏳' : '▶'} Run
                  </button>
                  <button
                    onClick={() => duplicateTest(test)}
                    className="action-btn"
                    title="Duplicate"
                  >
                    📋
                  </button>
                  <button
                    onClick={() => deleteTest(test.id)}
                    className="action-btn danger"
                    title="Delete"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
        </>
      ) : (
        /* RAG Testing UI */
        <div className="rag-testing-container">
          <div className="rag-header">
            <h3>📚 RAG Testing</h3>
            <p className="rag-subtitle">Ask questions about pre-loaded medical documents</p>
          </div>

          {/* Service Status Banner */}
          <div className={`rag-service-status ${ragServiceStatus}`}>
            {ragServiceStatus === 'checking' && (
              <span>🔍 Checking RAG Service...</span>
            )}
            {ragServiceStatus === 'running' && (
              <span>✅ RAG Service running on port 11435</span>
            )}
            {ragServiceStatus === 'stopped' && (
              <>
                <span>⚠️ RAG Service not running</span>
                <button
                  onClick={startRagServiceManually}
                  disabled={ragServiceStarting}
                  className="rag-start-btn"
                >
                  {ragServiceStarting ? '⏳ Starting...' : '▶ Start Service'}
                </button>
              </>
            )}
          </div>

          {/* Sample PDFs Section */}
          {ragServiceStatus === 'running' && !selectedPDF && (
            <div className="rag-sample-pdfs-section">
              <h3>📚 Sample Medical Documents</h3>
              <p className="sample-hint">Click to load a pre-loaded medical guideline for testing</p>
              <div className="sample-pdfs-grid">
                <button
                  onClick={() => loadSamplePDF('01-hypertension-guide.pdf', 'Hypertension Quick Guide')}
                  className="sample-pdf-btn"
                  disabled={pdfProcessing}
                >
                  <span className="sample-icon">💊</span>
                  <span className="sample-name">Hypertension Guide</span>
                  <span className="sample-size">223 KB</span>
                </button>
                <button
                  onClick={() => loadSamplePDF('02-diabetes-guidelines.pdf', 'Diabetes Guidelines')}
                  className="sample-pdf-btn"
                  disabled={pdfProcessing}
                >
                  <span className="sample-icon">🩸</span>
                  <span className="sample-name">Diabetes Guidelines</span>
                  <span className="sample-size">20 KB</span>
                </button>
                <button
                  onClick={() => loadSamplePDF('03-covid-treatment-cdc.pdf', 'COVID-19 Treatment (CDC)')}
                  className="sample-pdf-btn"
                  disabled={pdfProcessing}
                >
                  <span className="sample-icon">🦠</span>
                  <span className="sample-name">COVID Treatment</span>
                  <span className="sample-size">670 KB</span>
                </button>
                <button
                  onClick={() => loadSamplePDF('04-asthma-guidelines-nih.pdf', 'Asthma Guidelines (NIH)')}
                  className="sample-pdf-btn"
                  disabled={pdfProcessing}
                >
                  <span className="sample-icon">🫁</span>
                  <span className="sample-name">Asthma Guidelines</span>
                  <span className="sample-size">2.2 MB</span>
                </button>
              </div>
            </div>
          )}

          {/* PDF Upload Section */}
          {ragServiceStatus === 'running' && (
            <div className="rag-pdf-section">
              <h3>📄 {selectedPDF ? 'Current Document' : 'Upload Custom PDF'}</h3>

              {!selectedPDF ? (
                <div className="pdf-upload-area">
                  <input
                    type="file"
                    id="pdf-upload"
                    accept="application/pdf"
                    onChange={handlePDFUpload}
                    style={{ display: 'none' }}
                  />
                  <label htmlFor="pdf-upload" className="pdf-upload-btn">
                    📁 Select PDF
                  </label>
                  <p className="pdf-hint">Or upload your own medical document</p>
                </div>
              ) : (
                <div className="pdf-selected">
                  <div className="pdf-info">
                    <span className="pdf-icon">📄</span>
                    <div className="pdf-details">
                      <span className="pdf-name">{selectedPDF.name}</span>
                      <span className="pdf-size">{(selectedPDF.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <button
                      onClick={() => setSelectedPDF(null)}
                      className="pdf-remove-btn"
                      title="Remove PDF"
                    >
                      ✕
                    </button>
                  </div>

                  {!pdfProcessed ? (
                    <button
                      onClick={processPDF}
                      disabled={pdfProcessing}
                      className="pdf-process-btn"
                    >
                      {pdfProcessing ? '⏳ Processing...' : '🚀 Process PDF'}
                    </button>
                  ) : (
                    <div className="pdf-processed-badge">
                      ✅ Ready for queries
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Question Input */}
          <div className="rag-query-section">
            <label>Ask a question:</label>
            <textarea
              value={ragQuestion}
              onChange={(e) => setRagQuestion(e.target.value)}
              placeholder="¿Cuál fue el diagnóstico del paciente?"
              className="rag-question-input"
              rows={3}
            />
            <button
              onClick={async () => {
                if (!ragQuestion.trim()) return

                // Phase 2: Validate PDF is loaded
                if (!selectedPDF) {
                  setRagResult({
                    error: 'No PDF loaded. Upload a PDF first.',
                    query: ragQuestion,
                    results: []
                  })
                  return
                }

                setRagRunning(true)
                try {
                  const response = await fetch('http://localhost:11435/rag/query', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'X-API-Key': 'change-me-in-production'
                    },
                    body: JSON.stringify({
                      query: ragQuestion,
                      top_k: 3,
                      filename: selectedPDF.name  // Phase 1: Send filename to backend
                    })
                  })

                  if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
                  }

                  const result = await response.json()

                  // 🛡️ Validar similarity threshold - no mostrar basura irrelevante
                  const MIN_SIMILARITY = 0.5; // 50% mínimo para considerar relevante

                  if (result.results.length === 0) {
                    setRagResult({
                      query: ragQuestion,
                      results: [],
                      device: result.device,
                      error: 'No documents uploaded yet. Upload a PDF first.'
                    })
                  } else if (result.results[0].similarity < MIN_SIMILARITY) {
                    // NO mostrar chunks cuando similarity es muy baja - solo warning
                    setRagResult({
                      query: ragQuestion,
                      results: [], // ← VACÍO - no mostrar basura irrelevante
                      device: result.device,
                      warning: `Low relevance detected. Best match is only ${(result.results[0].similarity * 100).toFixed(1)}% similar. The uploaded document "${result.results[0].filename}" does not contain relevant information about "${ragQuestion}". Upload a document related to your question.`,
                      lowSimilarityResults: result.results // Guardar para debug si querés
                    })
                  } else {
                    setRagResult(result)
                  }
                } catch (err) {
                  console.error('[RAG] Query failed:', err)
                  alert(`RAG Service error: ${err}`)
                } finally {
                  setRagRunning(false)
                }
              }}
              disabled={ragRunning || !ragQuestion.trim() || !selectedPDF || !pdfProcessed}
              className="rag-query-btn"
            >
              {ragRunning ? '🔍 Searching...' : '🔍 Search'}
            </button>
          </div>

          {/* Results */}
          {ragResult && (
            <div className="rag-result-card">
              <div className="rag-result-header">
                <span className="rag-result-label">Query: {ragResult.query}</span>
                <span className="rag-result-timing">Device: {ragResult.device}</span>
              </div>

              {/* Error/Warning Messages */}
              {ragResult.error && (
                <div className="rag-error-banner">
                  ❌ <strong>No Results:</strong> {ragResult.error}
                </div>
              )}

              {ragResult.warning && (
                <div className="rag-warning-banner">
                  ⚠️ <strong>Low Relevance:</strong> {ragResult.warning}
                </div>
              )}

              {ragResult.results && ragResult.results.length > 0 ? (
                <div className="rag-results-list">
                  {ragResult.results.map((result: any, idx: number) => (
                    <div key={idx} className="rag-chunk-result">
                      <div className="rag-chunk-header">
                        <span className="rag-chunk-index">#{idx + 1}</span>
                        <span className="rag-chunk-filename">{result.filename}</span>
                        <span className="rag-chunk-similarity">
                          Similarity: {(result.similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="rag-chunk-content">
                        {result.chunk}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rag-result-content">
                  No results found
                </div>
              )}

              {ragResult.results && ragResult.results.length > 0 && (
                <div className="rag-metadata">
                  <p className="rag-metadata-title">📊 Metadata:</p>
                  <ul>
                    <li>Results returned: {ragResult.results.length}</li>
                    <li>Device: {ragResult.device}</li>
                    <li>Average similarity: {(ragResult.results.reduce((sum: number, r: any) => sum + r.similarity, 0) / ragResult.results.length * 100).toFixed(1)}%</li>
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Sample Questions */}
          <div className="rag-samples">
            <p className="rag-samples-title">💡 Sample questions:</p>
            <div className="rag-samples-grid">
              {[
                '¿Cuál fue el diagnóstico?',
                '¿Qué medicamentos se prescribieron?',
                '¿Cuál fue el motivo de consulta?',
                '¿Qué estudios se ordenaron?',
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => setRagQuestion(q)}
                  className="rag-sample-btn"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
