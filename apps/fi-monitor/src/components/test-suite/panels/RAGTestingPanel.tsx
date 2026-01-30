import { useState } from 'react';
import { Upload, Power, PowerOff } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';

// Hooks
import { useRAGService } from '../hooks/useRAGService';
import { useRAGEvaluation } from '../hooks/useRAGEvaluation';

// Sections
import { RAGQuerySection } from '../sections/RAGQuerySection';
import { RAGResultsView } from '../sections/RAGResultsView';
import { RAGMetricsEvaluation } from '../sections/RAGMetricsEvaluation';
import { SamplePDFsSection } from '../sections/SamplePDFsSection';

interface RAGChunk {
  text: string;
  similarity: number;
  metadata?: {
    page?: number;
    source?: string;
  };
}

export function RAGTestingPanel() {
  // Service lifecycle management
  const {
    status,
    isStarting,
    selectedPDF,
    isPdfProcessing,
    checkStatus,
    startService,
    stopService,
    handlePDFSelect,
    loadSamplePDF,
  } = useRAGService();

  // RAG query and results
  const [question, setQuestion] = useState('');
  const [ragResults, setRagResults] = useState<RAGChunk[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // RAG evaluation
  const {
    results: evalResults,
    isRunning: isEvaluating,
    expandedQueries,
    runEvaluation,
    toggleQueryExpansion,
  } = useRAGEvaluation();

  // UI state
  const [activeTab, setActiveTab] = useState<'query' | 'evaluate'>('query');

  /**
   * Handle RAG search query
   */
  const handleSearch = async () => {
    if (!question.trim()) return;

    setIsSearching(true);
    try {
      const response = await invoke<RAGChunk[]>('query_rag', { question });
      setRagResults(response);
    } catch (error) {
      console.error('Failed to query RAG:', error);
      alert(`Failed to query RAG: ${error}`);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="rag-testing-panel space-y-6 p-6 bg-white rounded-lg shadow">
      {/* Service Status Header */}
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-2xl font-bold">📚 RAG Testing</h2>
          <p className="text-sm text-gray-600">
            Test retrieval-augmented generation with PDF documents
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Service Status:</span>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${
                status === 'running'
                  ? 'bg-green-100 text-green-800'
                  : status === 'checking'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {status === 'running' ? '● Running' : status === 'checking' ? '◐ Checking' : '○ Stopped'}
            </span>
          </div>
          {status === 'stopped' && (
            <button
              onClick={startService}
              disabled={isStarting}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Power className="w-4 h-4" />
              {isStarting ? 'Starting...' : 'Start Service'}
            </button>
          )}
          {status === 'running' && (
            <button
              onClick={stopService}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center gap-2"
            >
              <PowerOff className="w-4 h-4" />
              Stop Service
            </button>
          )}
          <button
            onClick={checkStatus}
            className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
          >
            Refresh
          </button>
        </div>
      </div>

      {status !== 'running' && (
        <div className="text-center py-8 text-gray-500">
          Service is not running. Start the service to upload PDFs and test RAG.
        </div>
      )}

      {status === 'running' && (
        <>
          {/* PDF Upload Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">1. Upload or Select a PDF</h3>
            <div className="flex items-center gap-4">
              <label className="flex-1">
                <div className="flex items-center gap-2 px-4 py-2 border-2 border-dashed rounded-lg cursor-pointer hover:bg-gray-50">
                  <Upload className="w-5 h-5 text-gray-600" />
                  <span className="text-sm text-gray-700">
                    {isPdfProcessing ? 'Processing...' : 'Upload Custom PDF'}
                  </span>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handlePDFSelect}
                    disabled={isPdfProcessing}
                    className="hidden"
                  />
                </div>
              </label>
              {selectedPDF && (
                <div className="px-4 py-2 bg-blue-50 text-blue-800 rounded-md text-sm">
                  ✓ Loaded: {selectedPDF}
                </div>
              )}
            </div>
            <SamplePDFsSection
              onLoadSample={loadSamplePDF}
              isProcessing={isPdfProcessing}
            />
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('query')}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === 'query'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              2. Query RAG
            </button>
            <button
              onClick={() => setActiveTab('evaluate')}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === 'evaluate'
                  ? 'text-purple-600 border-b-2 border-purple-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              3. Evaluate Quality
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'query' && (
            <div className="space-y-4">
              <RAGQuerySection
                question={question}
                onQuestionChange={setQuestion}
                onSearch={handleSearch}
                isSearching={isSearching}
                isDisabled={!selectedPDF || isPdfProcessing}
              />
              <RAGResultsView results={ragResults} isSearching={isSearching} />
            </div>
          )}

          {activeTab === 'evaluate' && (
            <RAGMetricsEvaluation
              results={evalResults}
              isRunning={isEvaluating}
              expandedQueries={expandedQueries}
              onToggleQuery={toggleQueryExpansion}
              onRunEvaluation={runEvaluation}
            />
          )}
        </>
      )}
    </div>
  );
}
