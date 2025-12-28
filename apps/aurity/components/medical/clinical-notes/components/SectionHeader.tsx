'use client';

import { memo, type ReactNode } from 'react';

interface SectionHeaderProps {
  emoji: string;
  title: string;
  action?: ReactNode;
}

export const SectionHeader = memo(function SectionHeader({
  emoji,
  title,
  action,
}: SectionHeaderProps) {
  return (
    <div className="fi-flex-between mb-4">
      <div className="fi-flex-gap-md">
        <span className="text-2xl" role="img" aria-hidden="true">
          {emoji}
        </span>
        <h3 className="fi-title-xl">{title}</h3>
      </div>
      {action}
    </div>
  );
});
