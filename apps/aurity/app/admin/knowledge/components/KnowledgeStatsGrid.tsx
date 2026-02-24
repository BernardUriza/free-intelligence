/**
 * KnowledgeStatsGrid - Document statistics overview
 *
 * Renders a responsive grid of StatCards showing
 * total, indexed, processing, and error counts.
 */

import { FileText, Search, RefreshCw, AlertCircle } from 'lucide-react';
import { StatCard } from './StatCard';
import type { DocumentStats } from '../hooks/useDocumentFilters';

interface KnowledgeStatsGridProps {
  stats: DocumentStats;
}

export function KnowledgeStatsGrid({ stats }: KnowledgeStatsGridProps) {
  return (
    <div className="kno-stats-grid">
      <StatCard
        label="Total Documents"
        value={stats.total}
        icon={<FileText className="kno-stat-icon" />}
        color="blue"
      />
      <StatCard
        label="Indexed"
        value={stats.indexed}
        icon={<Search className="kno-stat-icon" />}
        color="emerald"
      />
      <StatCard
        label="Processing"
        value={stats.processing}
        icon={
          <RefreshCw
            className={stats.processing > 0 ? 'kno-stat-icon-spin' : 'kno-stat-icon'}
          />
        }
        color="yellow"
      />
      <StatCard
        label="Errors"
        value={stats.errors}
        icon={<AlertCircle className="kno-stat-icon" />}
        color="red"
      />
    </div>
  );
}
