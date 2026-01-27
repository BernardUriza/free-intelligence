'use client';

import { memo, type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

interface SectionHeaderProps {
  icon: LucideIcon;
  title: string;
  action?: ReactNode;
  iconColor?: string;
}

export const SectionHeader = memo(function SectionHeader({
  icon: Icon,
  title,
  action,
  iconColor = 'text-slate-400',
}: SectionHeaderProps) {
  return (
    <div className="fi-flex-between mb-4">
      <div className="fi-flex-gap-md">
        <Icon className={`w-6 h-6 ${iconColor}`} strokeWidth={1.5} aria-hidden="true" />
        <h3 className="fi-title-xl">{title}</h3>
      </div>
      {action}
    </div>
  );
});
