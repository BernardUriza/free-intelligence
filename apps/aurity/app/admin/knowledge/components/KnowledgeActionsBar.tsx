/**
 * KnowledgeActionsBar - Search, filter, view toggle, and action buttons
 *
 * Single responsibility: user controls for searching, filtering,
 * switching view mode, refreshing, and triggering upload.
 */

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { Search, RefreshCw, LayoutGrid, List, Plus } from 'lucide-react';
import type { ViewMode } from '../hooks/useDocumentFilters';
import type { DocumentStatus } from '@aurity-standalone/types/knowledge';

interface KnowledgeActionsBarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: DocumentStatus | 'all';
  onStatusFilterChange: (status: DocumentStatus | 'all') => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  loading: boolean;
  onRefresh: () => void;
  onUpload: () => void;
}

export function KnowledgeActionsBar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  viewMode,
  onViewModeChange,
  loading,
  onRefresh,
  onUpload,
}: KnowledgeActionsBarProps) {
  return (
    <div className="kno-actions-bar">
      {/* Search & Filter Row */}
      <div className="kno-search-filter-row">
        <div className="kno-search-wrap">
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search documents..."
            variant="default"
            icon={Search}
            className="kno-input-dark"
          />
        </div>

        <div className="kno-filter-wrap">
          <Select
            value={statusFilter}
            onValueChange={(value) => onStatusFilterChange(value as DocumentStatus | 'all')}
          >
            <SelectTrigger className="kno-input-dark">
              <SelectValue placeholder="All Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="indexed">Indexed</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* View Toggle & Actions Row */}
      <div className="kno-actions-right">
        <ViewModeToggle viewMode={viewMode} onChange={onViewModeChange} />

        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          disabled={loading}
          aria-label="Refresh documents"
          className="kno-refresh-btn"
        >
          <RefreshCw className={loading ? 'kno-refresh-icon-spin' : 'kno-refresh-icon'} />
        </Button>

        <Button
          variant="success"
          size="md"
          icon={Plus}
          onClick={onUpload}
          className="kno-upload-btn"
        >
          <span className="kno-upload-label-desktop">Upload Document</span>
          <span className="kno-upload-label-mobile">Upload</span>
        </Button>
      </div>
    </div>
  );
}

// ── View Mode Toggle (private) ──────────────────────────────────────

interface ViewModeToggleProps {
  viewMode: ViewMode;
  onChange: (mode: ViewMode) => void;
}

function ViewModeToggle({ viewMode, onChange }: ViewModeToggleProps) {
  return (
    <div className="kno-view-toggle">
      <button
        onClick={() => onChange('grid')}
        aria-label="Grid view"
        aria-pressed={viewMode === 'grid'}
        className={viewMode === 'grid' ? 'kno-view-btn-active' : 'kno-view-btn-inactive'}
      >
        <LayoutGrid className="kno-view-icon" />
      </button>
      <button
        onClick={() => onChange('list')}
        aria-label="List view"
        aria-pressed={viewMode === 'list'}
        className={viewMode === 'list' ? 'kno-view-btn-active' : 'kno-view-btn-inactive'}
      >
        <List className="kno-view-icon" />
      </button>
    </div>
  );
}
