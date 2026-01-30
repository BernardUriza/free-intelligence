import { Search } from 'lucide-react';

interface RAGQuerySectionProps {
  question: string;
  onQuestionChange: (value: string) => void;
  onSearch: () => void;
  isSearching: boolean;
  isDisabled: boolean;
}

export function RAGQuerySection({
  question,
  onQuestionChange,
  onSearch,
  isSearching,
  isDisabled,
}: RAGQuerySectionProps) {
  return (
    <div className="rag-query-section space-y-3">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Ask a question about the uploaded document:
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          placeholder="e.g., What are the recommended treatments for hypertension?"
          className="flex-1 px-3 py-2 border dark:border-gray-700 rounded-md focus:ring-2 focus:ring-blue-500"
          disabled={isDisabled}
        />
        <button
          onClick={onSearch}
          disabled={isDisabled || isSearching || !question.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Search className="w-4 h-4" />
          {isSearching ? 'Searching...' : 'Search RAG'}
        </button>
      </div>
    </div>
  );
}
