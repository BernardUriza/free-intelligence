/**
 * Tabs Component
 * Card: FI-INFRA-STR-014
 *
 * Fully functional tabs component with controlled/uncontrolled state management
 */

"use client";

import React, { createContext, useContext, useState } from 'react';

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined);

function useTabsContext() {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs components must be used within a Tabs provider');
  }
  return context;
}

export interface TabsProps {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
  children: React.ReactNode;
}

export function Tabs({
  defaultValue,
  value: controlledValue,
  onValueChange: controlledOnValueChange,
  className = '',
  children
}: TabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue || '');

  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;
  const onValueChange = isControlled ? controlledOnValueChange! : setInternalValue;

  return (
    <TabsContext.Provider value={{ value, onValueChange }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

export interface TabsListProps {
  className?: string;
  children: React.ReactNode;
}

export function TabsList({ children, className = '' }: TabsListProps) {
  return (
    <div
      role="tablist"
      className={`inline-flex items-center justify-center rounded-md ${className}`}
    >
      {children}
    </div>
  );
}

export interface TabsTriggerProps {
  value: string;
  className?: string;
  children: React.ReactNode;
  disabled?: boolean;
}

export function TabsTrigger({ value, children, className = '', disabled = false }: TabsTriggerProps) {
  const { value: selectedValue, onValueChange } = useTabsContext();
  const isActive = value === selectedValue;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      aria-disabled={disabled}
      disabled={disabled}
      data-state={isActive ? 'active' : 'inactive'}
      onClick={() => onValueChange(value)}
      className={`inline-flex items-center justify-center whitespace-nowrap px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  );
}

export interface TabsContentProps {
  value: string;
  className?: string;
  children: React.ReactNode;
}

export function TabsContent({ value, children, className = '' }: TabsContentProps) {
  const { value: selectedValue } = useTabsContext();
  const isActive = value === selectedValue;

  if (!isActive) return null;

  return (
    <div
      role="tabpanel"
      data-state={isActive ? 'active' : 'inactive'}
      className={className}
    >
      {children}
    </div>
  );
}
