'use client';

import type { SourceFilter, FilterTab, CatalogSource } from '../types';
import { Button } from '@/components/ui/button';
import { ProviderLogo } from '@/components/ui/ProviderLogo';

interface FilterTabsProps {
  tabs: FilterTab[];
  activeFilter: SourceFilter;
  onFilterChange: (filter: SourceFilter) => void;
}

export function FilterTabs({ tabs, activeFilter, onFilterChange }: FilterTabsProps) {
  return (
    <div className="flex gap-1.5 mt-4 overflow-x-auto pb-1">
      {tabs.map((tab) => {
        // Render icon based on type
        const renderIcon = () => {
          if (tab.icon === 'provider') {
            // Use ProviderLogo for catalog sources
            return <ProviderLogo provider={tab.key as CatalogSource} size={16} />;
          }
          // Use Lucide icon component
          const IconComponent = tab.icon;
          return <IconComponent className="w-4 h-4" />;
        };

        return (
          <Button
            key={tab.key}
            onClick={() => onFilterChange(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              activeFilter === tab.key
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800 fi-text hover:bg-slate-700'
            }`}
            variant={activeFilter === tab.key ? 'primary' : 'ghost'}
            size="sm"
            type="button"
          >
            {renderIcon()}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span className="px-1.5 py-0.5 text-xs bg-black/20 rounded">
                {tab.count}
              </span>
            )}
          </Button>
        );
      })}
    </div>
  );
}
