import { useState, useEffect } from 'react';
import { Play, Plus, Copy, Trash2, X } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';

interface Test {
  id: string;
  question: string;
  expectedAnswer?: string;
  category: 'math' | 'medical' | 'general' | 'custom';
  difficulty: 'easy' | 'medium' | 'hard';
  tags: string[];
  createdAt: string;
}

interface TestResult {
  testId: string;
  answer: string;
  elapsed_ms: number;
  timestamp: string;
  passed?: boolean;
  score?: number;
}

const CATEGORY_ICONS = {
  math: '🔢',
  medical: '🏥',
  general: '💬',
  custom: '⚙️',
};

const CATEGORY_COLORS = {
  math: '#2196f3',
  medical: '#f44336',
  general: '#4caf50',
  custom: '#ff9800',
};

const DIFFICULTY_COLORS = {
  easy: '#4caf50',
  medium: '#ff9800',
  hard: '#f44336',
};

export function LLMTestingPanel() {
  const [tests, setTests] = useState<Test[]>([]);
  const [results, setResults] = useState<Map<string, TestResult>>(new Map());
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showAddForm, setShowAddForm] = useState(false);
  const [runningTests, setRunningTests] = useState<Set<string>>(new Set());
  const [bulkRunning, setBulkRunning] = useState(false);

  // Form state
  const [newTest, setNewTest] = useState<Partial<Test>>({
    question: '',
    expectedAnswer: '',
    category: 'general',
    difficulty: 'medium',
    tags: [],
  });

  useEffect(() => {
    loadTests();
  }, []);

  /**
   * Load all tests from backend
   */
  const loadTests = async () => {
    try {
      const loadedTests = await invoke<Test[]>('load_tests');
      setTests(loadedTests);
    } catch (err) {
      console.error('[LLMTestingPanel] Failed to load tests:', err);
    }
  };

  /**
   * Add a new test to the suite
   */
  const addTest = async () => {
    if (!newTest.question?.trim()) {
      alert('Question is required');
      return;
    }

    try {
      const test: Test = {
        id: `test_${Date.now()}`,
        question: newTest.question,
        expectedAnswer: newTest.expectedAnswer || '',
        category: newTest.category || 'general',
        difficulty: newTest.difficulty || 'medium',
        tags: newTest.tags || [],
        createdAt: new Date().toISOString(),
      };

      await invoke('add_test', { test });
      setTests([...tests, test]);
      setNewTest({
        question: '',
        expectedAnswer: '',
        category: 'general',
        difficulty: 'medium',
        tags: [],
      });
      setShowAddForm(false);
    } catch (err) {
      console.error('[LLMTestingPanel] Failed to add test:', err);
    }
  };

  /**
   * Run a single test
   */
  const runTest = async (test: Test) => {
    setRunningTests((prev) => new Set(prev).add(test.id));

    try {
      const start = Date.now();
      const answer = await invoke<string>('test_ollama', {
        question: test.question,
        expectedAnswer: test.expectedAnswer || null,
      });
      const elapsed = Date.now() - start;

      // Calculate score if expected answer provided
      let passed: boolean | undefined;
      let score: number | undefined;

      if (test.expectedAnswer) {
        score = calculateScore(answer, test.expectedAnswer);
        passed = score >= 70;
      }

      const testResult: TestResult = {
        testId: test.id,
        answer,
        elapsed_ms: elapsed,
        timestamp: new Date().toISOString(),
        passed,
        score,
      };

      setResults((prev) => new Map(prev).set(test.id, testResult));
    } catch (err) {
      console.error('[LLMTestingPanel] Test failed:', err);
    } finally {
      setRunningTests((prev) => {
        const next = new Set(prev);
        next.delete(test.id);
        return next;
      });
    }
  };

  /**
   * Run all tests in current category
   */
  const runAllInCategory = async () => {
    setBulkRunning(true);
    const testsToRun = filteredTests;

    for (const test of testsToRun) {
      await runTest(test);
    }

    setBulkRunning(false);
  };

  /**
   * Delete a test
   */
  const deleteTest = async (testId: string) => {
    if (!confirm('Delete this test?')) return;

    try {
      await invoke('delete_test', { testId });
      setTests(tests.filter((t) => t.id !== testId));
      setResults((prev) => {
        const next = new Map(prev);
        next.delete(testId);
        return next;
      });
    } catch (err) {
      console.error('[LLMTestingPanel] Failed to delete test:', err);
    }
  };

  /**
   * Duplicate a test (opens form with pre-filled data)
   */
  const duplicateTest = (test: Test) => {
    setNewTest({
      question: test.question + ' (copy)',
      expectedAnswer: test.expectedAnswer,
      category: test.category,
      difficulty: test.difficulty,
      tags: [...test.tags],
    });
    setShowAddForm(true);
  };

  /**
   * Calculate similarity score between answer and expected answer
   */
  const calculateScore = (answer: string, expected: string): number => {
    const answerLower = answer.toLowerCase();
    const expectedLower = expected.toLowerCase();

    if (answerLower.includes(expectedLower)) return 100;

    // Simple word overlap score
    const answerWords = answerLower.split(/\s+/);
    const expectedWords = expectedLower.split(/\s+/);
    const overlap = expectedWords.filter((w) => answerWords.includes(w)).length;

    return Math.round((overlap / expectedWords.length) * 100);
  };

  const filteredTests =
    selectedCategory === 'all'
      ? tests
      : tests.filter((t) => t.category === selectedCategory);

  return (
    <div className="llm-testing-panel space-y-6 p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-2xl font-bold">🤖 LLM Testing</h2>
          <p className="text-sm text-gray-600">
            Test Ollama with custom questions and automated scoring
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
          >
            {showAddForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showAddForm ? 'Cancel' : 'Add Test'}
          </button>

          {filteredTests.length > 0 && (
            <button
              onClick={runAllInCategory}
              disabled={bulkRunning}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              {bulkRunning ? 'Running...' : `Run All (${filteredTests.length})`}
            </button>
          )}
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {['all', 'math', 'medical', 'general', 'custom'].map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-4 py-2 rounded-md whitespace-nowrap transition-colors ${
              selectedCategory === cat
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {cat === 'all'
              ? '📚 All'
              : `${CATEGORY_ICONS[cat as keyof typeof CATEGORY_ICONS]} ${cat.charAt(0).toUpperCase() + cat.slice(1)}`}
            <span className="ml-2 text-xs">
              ({cat === 'all' ? tests.length : tests.filter((t) => t.category === cat).length})
            </span>
          </button>
        ))}
      </div>

      {/* Add Test Form */}
      {showAddForm && (
        <div className="border dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-900 space-y-4">
          <h3 className="text-lg font-semibold">New Test</h3>

          <div>
            <label className="block text-sm font-medium mb-1">Question *</label>
            <textarea
              value={newTest.question}
              onChange={(e) => setNewTest({ ...newTest, question: e.target.value })}
              placeholder="Enter test question..."
              rows={3}
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Expected Answer (optional)
            </label>
            <input
              type="text"
              value={newTest.expectedAnswer}
              onChange={(e) => setNewTest({ ...newTest, expectedAnswer: e.target.value })}
              placeholder="Expected answer for automated scoring..."
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select
                value={newTest.category}
                onChange={(e) =>
                  setNewTest({ ...newTest, category: e.target.value as any })
                }
                className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="general">General</option>
                <option value="math">Math</option>
                <option value="medical">Medical</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Difficulty</label>
              <select
                value={newTest.difficulty}
                onChange={(e) =>
                  setNewTest({ ...newTest, difficulty: e.target.value as any })
                }
                className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={newTest.tags?.join(', ')}
              onChange={(e) =>
                setNewTest({
                  ...newTest,
                  tags: e.target.value
                    .split(',')
                    .map((t) => t.trim())
                    .filter(Boolean),
                })
              }
              placeholder="spanish, reasoning, factual..."
              className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={addTest}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              💾 Save Test
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-400 dark:hover:bg-gray-500"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Test Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredTests.length === 0 ? (
          <div className="col-span-full text-center py-12 text-gray-500">
            <p>No tests in this category yet.</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              + Add First Test
            </button>
          </div>
        ) : (
          filteredTests.map((test) => {
            const result = results.get(test.id);
            const isRunning = runningTests.has(test.id);

            return (
              <div
                key={test.id}
                className="border dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-shadow"
                style={{ borderLeftWidth: '4px', borderLeftColor: CATEGORY_COLORS[test.category] }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-600">
                    {CATEGORY_ICONS[test.category]} {test.category}
                  </span>
                  <span
                    className="text-xs font-medium"
                    style={{ color: DIFFICULTY_COLORS[test.difficulty] }}
                  >
                    {test.difficulty}
                  </span>
                </div>

                <p className="text-sm font-medium text-gray-800 mb-3">{test.question}</p>

                {test.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {test.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                {result && (
                  <div className="border-t pt-3 mb-3">
                    <div className="flex items-center justify-between mb-2">
                      {result.passed !== undefined && (
                        <span
                          className={`text-xs font-medium ${
                            result.passed ? 'text-green-600' : 'text-red-600'
                          }`}
                        >
                          {result.passed ? '✓ PASSED' : '✗ FAILED'}
                          {result.score !== undefined && ` (${result.score}%)`}
                        </span>
                      )}
                      <span className="text-xs text-gray-500">{result.elapsed_ms}ms</span>
                    </div>
                    <p className="text-xs text-gray-700 line-clamp-3">{result.answer}</p>
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => runTest(test)}
                    disabled={isRunning || bulkRunning}
                    className="flex-1 px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center gap-1 text-sm"
                  >
                    {isRunning ? '⏳' : <Play className="w-3 h-3" />}
                    {isRunning ? 'Running...' : 'Run'}
                  </button>
                  <button
                    onClick={() => duplicateTest(test)}
                    className="px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
                    title="Duplicate"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteTest(test.id)}
                    className="px-3 py-2 bg-red-100 text-red-600 rounded-md hover:bg-red-200"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
