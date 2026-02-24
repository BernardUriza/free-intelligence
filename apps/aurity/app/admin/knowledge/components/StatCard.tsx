/**
 * StatCard - Single metric display card
 *
 * Reusable card showing an icon, numeric value, and label
 * with color-coded theming.
 */

import type { ReactNode } from 'react';

type StatColor = 'blue' | 'emerald' | 'yellow' | 'red';

interface StatCardProps {
  label: string;
  value: number;
  icon: ReactNode;
  color: StatColor;
}

const COLOR_CLASSES: Record<StatColor, string> = {
  blue: 'kno-stat-color-blue',
  emerald: 'kno-stat-color-emerald',
  yellow: 'kno-stat-color-yellow',
  red: 'kno-stat-color-red',
} as const;

export function StatCard({ label, value, icon, color }: StatCardProps) {
  return (
    <div className={`kno-stat-card ${COLOR_CLASSES[color]}`}>
      <div className="kno-stat-inner">
        <div className="kno-stat-icon-box">{icon}</div>
        <div className="kno-stat-text-wrap">
          <p className="kno-stat-value">{value}</p>
          <p className="kno-stat-label">{label}</p>
        </div>
      </div>
    </div>
  );
}
