import { ProgressBar } from '../shared/ProgressBar';

interface RAGChunk {
  text: string;
  similarity: number;
  metadata?: {
    page?: number;
    source?: string;
  };
}

interface RAGResultsViewProps {
  results: RAGChunk[];
  isSearching: boolean;
}

export function RAGResultsView({ results, isSearching }: RAGResultsViewProps) {
  if (isSearching) {
    return (
      <div className="rag-results-loading text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
        <p className="mt-4 text-gray-600 dark:text-gray-400">Searching RAG...</p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="rag-results-empty text-center py-8 text-gray-500">
        No results yet. Enter a question and click "Search RAG" to retrieve relevant chunks.
      </div>
    );
  }

  return (
    <div className="rag-results-view space-y-4">
      <h3 className="text-lg font-semibold">
        Retrieved Chunks ({results.length})
      </h3>
      <div className="space-y-3">
        {results.map((chunk, idx) => {
          // Determine color based on similarity score
          const getColor = (score: number): 'green' | 'yellow' | 'red' => {
            if (score > 0.7) return 'green';
            if (score > 0.5) return 'yellow';
            return 'red';
          };

          return (
            <div
              key={idx}
              className="border dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-medium text-gray-500">
                  Chunk #{idx + 1}
                  {chunk.metadata?.page && ` (Page ${chunk.metadata.page})`}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600">
                    Relevance:
                  </span>
                  <ProgressBar
                    value={chunk.similarity}
                    color={getColor(chunk.similarity)}
                    height="6px"
                    showLabel={true}
                    className="w-24"
                  />
                </div>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {chunk.text}
              </p>
              {chunk.metadata?.source && (
                <p className="text-xs text-gray-500 mt-2">
                  Source: {chunk.metadata.source}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
