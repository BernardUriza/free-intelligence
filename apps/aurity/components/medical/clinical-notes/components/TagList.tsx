'use client';

import { memo } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface TagListProps {
  items: string[];
  onRemove: (index: number) => void;
  colorClass?: string;
}

export const TagList = memo(function TagList({
  items,
  onRemove,
  colorClass = 'bg-red-500/20 text-red-400',
}: TagListProps) {
  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-2" role="list">
      {items.map((item, idx) => (
        <span
          key={`${item}-${idx}`}
          className={`px-3 py-1 ${colorClass} rounded-full text-sm flex items-center gap-2`}
          role="listitem"
        >
          {item}
          <Button
            onClick={() => onRemove(idx)}
            variant="ghost"
            size="sm"
            icon={X}
            className="p-0 h-auto hover:bg-transparent hover:opacity-70"
            aria-label={`Eliminar ${item}`}
          />
        </span>
      ))}
    </div>
  );
});
