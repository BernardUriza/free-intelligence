/**
 * Accordion Component
 * Card: FI-INFRA-STR-014
 *
 * Fully functional accordion with single/multiple expansion modes
 */

"use client";

import React, { createContext, useContext, useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface AccordionContextValue {
  type: 'single' | 'multiple';
  expandedItems: string[];
  toggleItem: (value: string) => void;
}

const AccordionContext = createContext<AccordionContextValue | undefined>(undefined);

function useAccordionContext() {
  const context = useContext(AccordionContext);
  if (!context) {
    throw new Error('Accordion components must be used within an Accordion provider');
  }
  return context;
}

export interface AccordionProps {
  type?: 'single' | 'multiple';
  collapsible?: boolean;
  defaultValue?: string | string[];
  className?: string;
  children: React.ReactNode;
}

export function Accordion({
  type = 'single',
  collapsible = false,
  defaultValue,
  className = '',
  children
}: AccordionProps) {
  const [expandedItems, setExpandedItems] = useState<string[]>(() => {
    if (defaultValue) {
      return Array.isArray(defaultValue) ? defaultValue : [defaultValue];
    }
    return [];
  });

  const toggleItem = (value: string) => {
    setExpandedItems(prev => {
      if (type === 'single') {
        // Single mode: only one item can be open at a time
        if (prev.includes(value)) {
          // If clicking the already-open item and collapsible is true, close it
          return collapsible ? [] : prev;
        }
        return [value];
      } else {
        // Multiple mode: any number of items can be open
        if (prev.includes(value)) {
          return prev.filter(item => item !== value);
        }
        return [...prev, value];
      }
    });
  };

  return (
    <AccordionContext.Provider value={{ type, expandedItems, toggleItem }}>
      <div className={className}>{children}</div>
    </AccordionContext.Provider>
  );
}

interface AccordionItemContextValue {
  value: string;
  isExpanded: boolean;
}

const AccordionItemContext = createContext<AccordionItemContextValue | undefined>(undefined);

function useAccordionItemContext() {
  const context = useContext(AccordionItemContext);
  if (!context) {
    throw new Error('AccordionTrigger/AccordionContent must be used within an AccordionItem');
  }
  return context;
}

export interface AccordionItemProps {
  value: string;
  className?: string;
  children: React.ReactNode;
}

export function AccordionItem({ value, children, className = '' }: AccordionItemProps) {
  const { expandedItems } = useAccordionContext();
  const isExpanded = expandedItems.includes(value);

  return (
    <AccordionItemContext.Provider value={{ value, isExpanded }}>
      <div className={`border-b ${className}`}>{children}</div>
    </AccordionItemContext.Provider>
  );
}

export interface AccordionTriggerProps {
  className?: string;
  children: React.ReactNode;
}

export function AccordionTrigger({ children, className = '' }: AccordionTriggerProps) {
  const { toggleItem } = useAccordionContext();
  const { value, isExpanded } = useAccordionItemContext();

  return (
    <button
      type="button"
      onClick={() => toggleItem(value)}
      className={`flex w-full items-center justify-between py-4 text-left transition-all hover:underline ${className}`}
    >
      {children}
      <ChevronDown
        className={`h-4 w-4 transition-transform duration-200 ${
          isExpanded ? 'rotate-180' : ''
        }`}
      />
    </button>
  );
}

export interface AccordionContentProps {
  className?: string;
  children: React.ReactNode;
}

export function AccordionContent({ children, className = '' }: AccordionContentProps) {
  const { isExpanded } = useAccordionItemContext();

  if (!isExpanded) return null;

  return (
    <div className={`overflow-hidden pb-4 transition-all ${className}`}>
      {children}
    </div>
  );
}
