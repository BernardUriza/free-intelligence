'use client';

/**
 * Disk usage display with progress bar.
 */

import type { DiskUsage } from '../types';

interface DiskUsageSectionProps {
  diskUsage: DiskUsage | null;
}

function getProgressClass(percent: number): string {
  if (percent > 80) return 'layout-progress-critical';
  if (percent > 60) return 'layout-progress-warning';
  return 'layout-progress-healthy';
}

export function DiskUsageSection({ diskUsage }: DiskUsageSectionProps) {
  return (
    <div className="prof-section">
      <h3 className="fi-title prof-section-title">Estado del Almacenamiento</h3>
      {diskUsage ? (
        <div className="fi-stack-md">
          <div className="prof-disk-row">
            <span className="prof-disk-label">Usado</span>
            <span className="prof-disk-value">{diskUsage.used}</span>
          </div>
          <div className="prof-disk-track">
            <div
              className={getProgressClass(diskUsage.percent)}
              style={{ width: `${Math.min(diskUsage.percent, 100)}%` }}
            />
          </div>
          <div className="prof-disk-row">
            <span className="prof-disk-label">Total disponible</span>
            <span className="prof-disk-value">{diskUsage.total}</span>
          </div>
        </div>
      ) : (
        <p className="prof-disk-loading">Cargando información del disco...</p>
      )}
    </div>
  );
}
