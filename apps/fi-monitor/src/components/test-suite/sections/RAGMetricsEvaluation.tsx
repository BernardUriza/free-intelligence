import { ProgressBar } from '../shared/ProgressBar';
import { QualityBadge } from '../shared/QualityBadge';
import { AccordionItem } from '../shared/AccordionItem';
import type { QueryEvaluation } from '../hooks/useRAGEvaluation';
import { calculateAggregateMetrics } from '../hooks/useRAGEvaluation';

interface RAGMetricsEvaluationProps {
  results: QueryEvaluation[];
  isRunning: boolean;
  expandedQueries: Set<number>;
  onToggleQuery: (index: number) => void;
  onRunEvaluation: () => void;
}

export function RAGMetricsEvaluation({
  results,
  isRunning,
  expandedQueries,
  onToggleQuery,
  onRunEvaluation,
}: RAGMetricsEvaluationProps) {
  const aggregateMetrics = calculateAggregateMetrics(results);

  return (
    <div className="rag-metrics-evaluation space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">RAG Quality Metrics</h3>
        <button
          onClick={onRunEvaluation}
          disabled={isRunning}
          className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed"
        >
          {isRunning ? 'Running Evaluation...' : 'Run Batch Evaluation'}
        </button>
      </div>

      {isRunning && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Evaluating queries...</p>
        </div>
      )}

      {!isRunning && results.length > 0 && (
        <>
          {/* Aggregate Metrics Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <div>
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg Recall</p>
              <ProgressBar
                value={aggregateMetrics.avgRecall}
                color="green"
                showLabel={true}
              />
            </div>
            <div>
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg Precision</p>
              <ProgressBar
                value={aggregateMetrics.avgPrecision}
                color="green"
                showLabel={true}
              />
            </div>
            <div>
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg MRR</p>
              <ProgressBar
                value={aggregateMetrics.avgMRR}
                color="yellow"
                showLabel={true}
              />
            </div>
            <div>
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg NDCG</p>
              <ProgressBar
                value={aggregateMetrics.avgNDCG}
                color="yellow"
                showLabel={true}
              />
            </div>
          </div>

          {/* Individual Query Results */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Query Results ({results.length})
            </h4>
            {results.map((result, idx) => (
              <AccordionItem
                key={idx}
                title={result.query}
                isExpanded={expandedQueries.has(idx)}
                onToggle={() => onToggleQuery(idx)}
                badge={<QualityBadge value={(result.recall + result.precision) / 2} />}
              >
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Recall</p>
                    <ProgressBar value={result.recall} color="green" showLabel={true} />
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Precision</p>
                    <ProgressBar value={result.precision} color="green" showLabel={true} />
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">MRR</p>
                    <ProgressBar value={result.mrr} color="yellow" showLabel={true} />
                  </div>
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">NDCG</p>
                    <ProgressBar value={result.ndcg} color="yellow" showLabel={true} />
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      Retrieved: {result.retrieved_count} chunks
                    </p>
                  </div>
                </div>
              </AccordionItem>
            ))}
          </div>
        </>
      )}

      {!isRunning && results.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No evaluation results yet. Click "Run Batch Evaluation" to test RAG quality metrics.
        </div>
      )}
    </div>
  );
}
