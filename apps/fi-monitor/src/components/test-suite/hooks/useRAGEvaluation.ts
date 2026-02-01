import { useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';

export interface QueryEvaluation {
  query: string;
  recall: number;
  precision: number;
  mrr: number;
  ndcg: number;
  retrieved_count: number;
}

interface UseRAGEvaluationReturn {
  results: QueryEvaluation[];
  isRunning: boolean;
  expandedQueries: Set<number>;
  runEvaluation: () => Promise<void>;
  toggleQueryExpansion: (index: number) => void;
}

/**
 * Custom hook for RAG batch evaluation and metrics calculation
 *
 * Handles:
 * - Running batch evaluation of multiple queries
 * - Calculating aggregate metrics (avg Recall, Precision, MRR, NDCG)
 * - Managing UI state (expanded accordions)
 */
export function useRAGEvaluation(): UseRAGEvaluationReturn {
  const [results, setResults] = useState<QueryEvaluation[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [expandedQueries, setExpandedQueries] = useState<Set<number>>(new Set());

  /**
   * Run batch evaluation of pre-defined queries
   */
  const runEvaluation = useCallback(async () => {
    setIsRunning(true);
    try {
      const response = await invoke<QueryEvaluation[]>('run_rag_evaluation');
      setResults(response);
    } catch (error) {
      console.error('Failed to run RAG evaluation:', error);
      alert(`Failed to run RAG evaluation: ${error}`);
    } finally {
      setIsRunning(false);
    }
  }, []);

  /**
   * Toggle accordion expansion for a specific query result
   */
  const toggleQueryExpansion = useCallback((index: number) => {
    setExpandedQueries(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  return {
    results,
    isRunning,
    expandedQueries,
    runEvaluation,
    toggleQueryExpansion,
  };
}

/**
 * Calculate aggregate metrics from evaluation results
 */
export function calculateAggregateMetrics(results: QueryEvaluation[]) {
  if (results.length === 0) {
    return { avgRecall: 0, avgPrecision: 0, avgMRR: 0, avgNDCG: 0 };
  }

  const sum = results.reduce(
    (acc, r) => ({
      recall: acc.recall + r.recall,
      precision: acc.precision + r.precision,
      mrr: acc.mrr + r.mrr,
      ndcg: acc.ndcg + r.ndcg,
    }),
    { recall: 0, precision: 0, mrr: 0, ndcg: 0 }
  );

  const count = results.length;

  return {
    avgRecall: sum.recall / count,
    avgPrecision: sum.precision / count,
    avgMRR: sum.mrr / count,
    avgNDCG: sum.ndcg / count,
  };
}
