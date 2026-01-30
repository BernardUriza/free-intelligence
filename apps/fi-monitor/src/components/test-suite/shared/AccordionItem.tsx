import { ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface AccordionItemProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  badge?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function AccordionItem({
  title,
  isExpanded,
  onToggle,
  badge,
  children,
  className = '',
}: AccordionItemProps) {
  return (
    <div className={`accordion-item border rounded-lg mb-2 ${className}`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <span className="font-medium">{title}</span>
          {badge}
        </div>
      </button>
      {isExpanded && (
        <div className="p-3 border-t bg-gray-50">{children}</div>
      )}
    </div>
  );
}
