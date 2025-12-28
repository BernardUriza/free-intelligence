/**
 * TimelineSearch Component
 *
 * Search bar for longitudinal memory with debouncing
 * and keyboard shortcuts.
 *
 * Features:
 * - Debounced search (300ms)
 * - Keyboard shortcut: / to focus
 * - Clear button
 * - Loading state
 *
 * Created: 2025-12-08
 */

'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface TimelineSearchProps {
  onSearch: (query: string) => void;
  isSearching?: boolean;
  placeholder?: string;
  className?: string;
}

export function TimelineSearch({
  onSearch,
  isSearching = false,
  placeholder = 'Buscar en la conversación infinita... (presiona / para enfocar)',
  className = '',
}: TimelineSearchProps) {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Trigger search when debounced query changes
  useEffect(() => {
    onSearch(debouncedQuery);
  }, [debouncedQuery, onSearch]);

  // Keyboard shortcut: / to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement;
        // Don't trigger if already in an input
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault();
          inputRef.current?.focus();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleClear = useCallback(() => {
    setQuery('');
    inputRef.current?.focus();
  }, []);

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        <Input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          variant="ghost"
          icon={Search}
          className="py-2.5 text-sm"
        />

        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {isSearching && (
            <Loader2 className="h-4 w-4 fi-text-success animate-spin" />
          )}
          
          {query && !isSearching && (
            <Button
              onClick={handleClear}
              variant="ghost"
              size="sm"
              icon={X}
              className="p-1"
              title="Limpiar búsqueda"
              aria-label="Limpiar búsqueda"
            />
          )}
        </div>
      </div>

      {query && (
        <div className="absolute top-full mt-1 left-0 right-0">
          <div className="fi-text-xs-muted px-3">
            {debouncedQuery !== query ? (
              <span>Buscando...</span>
            ) : (
              <span>Presiona Esc para limpiar</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
