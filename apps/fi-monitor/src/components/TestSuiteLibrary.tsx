// Test Suite Library for comprehensive testing
import { useState, useEffect } from 'react'
import { invoke } from '../lib/tauri-adapter'

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

  const loadTests = async () => {
    try {
      const loadedTests = await invoke<Test[]>('get_test_suite')
      setTests(loadedTests)
    } catch (err) {
      console.error('[TestSuiteLibrary] Failed to load tests:', err)
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
    </div>
  )
}
