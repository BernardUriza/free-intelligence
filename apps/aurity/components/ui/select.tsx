/**
 * Select Component
 * Card: FI-INFRA-STR-014
 *
 * Fully functional select dropdown with controlled/uncontrolled state
 * Supports rich items with icons, badges, descriptions, and portal rendering
 */

"use client";

import React, { createContext, useContext, useState, useRef, useEffect, useLayoutEffect, useId, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { LucideIcon } from 'lucide-react';
import { BADGE_STYLES, type BadgeVariant } from '@/types/select-configs';

interface SelectContextValue {
  value: string;
  // eslint-disable-next-line no-unused-vars
  onValueChange: (newValue: string) => void;
  isOpen: boolean;
  // eslint-disable-next-line no-unused-vars
  setIsOpen: (isOpen: boolean) => void;
  triggerId: string;
  richItems?: Map<string, RichItemData>;
  // eslint-disable-next-line no-unused-vars
  registerRichItem: (itemValue: string, data: RichItemData) => void;
}

export interface RichItemData {
  label: string;
  icon?: LucideIcon;
  description?: string;
  badge?: {
    text: string;
    variant: BadgeVariant;
  };
  metadata?: Record<string, string | number>;
}

const SelectContext = createContext<SelectContextValue | undefined>(undefined);

function useSelectContext() {
  const context = useContext(SelectContext);
  if (!context) {
    throw new Error('Select components must be used within a Select provider');
  }
  return context;
}

export interface SelectProps {
  value?: string;
  // eslint-disable-next-line no-unused-vars
  onValueChange?: (newValue: string) => void;
  defaultValue?: string;
  disabled?: boolean;
  items?: Map<string, RichItemData> | Record<string, RichItemData>;
  children: React.ReactNode;
}

export function Select({
  value: controlledValue,
  onValueChange: controlledOnValueChange,
  defaultValue = '',
  disabled = false,
  items,
  children
}: SelectProps) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const [isOpen, setIsOpen] = useState(false);
  const [richItems, setRichItems] = useState<Map<string, RichItemData>>(() => {
    if (!items) return new Map();
    if (items instanceof Map) return new Map(items);
    return new Map(Object.entries(items));
  });
  const triggerId = `select-trigger-${useId()}`;
  const contentId = `select-content-${useId()}`;

  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;
  const onValueChange = isControlled ? controlledOnValueChange! : setInternalValue;

  const shallowEqualRich = (a: RichItemData | undefined, b: RichItemData) => {
    if (!a) return false;
    if (a.label !== b.label) return false;
    if (a.description !== b.description) return false;
    if (a.badge?.text !== b.badge?.text) return false;
    if (a.badge?.variant !== b.badge?.variant) return false;
    // compare metadata keys/values shallowly
    const aMeta = a.metadata || {};
    const bMeta = b.metadata || {};
    const aKeys = Object.keys(aMeta);
    const bKeys = Object.keys(bMeta);
    if (aKeys.length !== bKeys.length) return false;
    for (const k of aKeys) {
      if (String(aMeta[k]) !== String(bMeta[k])) return false;
    }
    return true;
  };

  const registerRichItem = useCallback((itemValue: string, data: RichItemData) => {
    setRichItems((prev) => {
      const existing = prev.get(itemValue);
      if (shallowEqualRich(existing, data)) return prev;
      const next = new Map(prev);
      next.set(itemValue, data);
      return next;
    });
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest(`[data-select-trigger="${triggerId}"]`) &&
          !target.closest('[data-select-content]')) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, triggerId]);

  if (disabled) {
    return <div className="relative opacity-50 cursor-not-allowed">{children}</div>;
  }

  return (
    <SelectContext.Provider value={{ value, onValueChange, isOpen, setIsOpen, triggerId, richItems, registerRichItem }}>
      <div className="relative" data-select-root data-select-content-id={contentId}>{children}</div>
    </SelectContext.Provider>
  );
}

export interface SelectTriggerProps {
  id?: string;
  className?: string;
  children: React.ReactNode;
}

export function SelectTrigger({ id, children, className = '' }: SelectTriggerProps) {
  const { isOpen, setIsOpen, triggerId } = useSelectContext();

  return (
    <Button
      id={id}
      type="button"
      data-select-trigger={triggerId}
      onClick={() => setIsOpen(!isOpen)}
      aria-haspopup="listbox"
      aria-expanded={isOpen}
      aria-controls={document ? (`select-content-${triggerId.split('-').pop()}`) : undefined}
      className={`flex w-full items-center justify-between rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700/50 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-slate-900 transition-colors ${className}`}
      variant="ghost"
      size="sm"
    >
      {children}
      <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
    </Button>
  );
}

export interface SelectValueProps {
  placeholder?: string;
  showIcon?: boolean;
  showBadge?: boolean;
  showDescription?: boolean;
  /** Icon-only mode: hide label and badge, show only icon */
  compact?: boolean;
  /** Custom class for label (useful for responsive hiding) */
  labelClassName?: string;
  /** Custom class for badge (useful for responsive hiding) */
  badgeClassName?: string;
}

export function SelectValue({
  placeholder = 'Select...',
  showIcon = true,
  showBadge = true,
  showDescription = false,
  compact = false,
  labelClassName = '',
  badgeClassName = '',
}: SelectValueProps) {
  const { value, richItems } = useSelectContext();

  if (!value) {
    return <span className="text-slate-400">{placeholder}</span>;
  }

  const itemData = richItems?.get(value);
  if (!itemData) {
    return <span className="text-slate-200">{value}</span>;
  }

  const Icon = itemData.icon;
  const badgeStyles = itemData.badge ? BADGE_STYLES[itemData.badge.variant] : null;

  // Compact mode: only show icon
  if (compact) {
    return (
      <div className="fi-flex-center">
        {Icon && <Icon className="w-4 h-4 text-slate-400" />}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-1 min-w-0">
      {showIcon && Icon && <Icon className="w-4 h-4 text-slate-400 flex-shrink-0" />}
      <div className={`flex flex-col min-w-0 flex-1 ${labelClassName}`}>
        <span className="text-slate-200 truncate">{itemData.label}</span>
        {showDescription && itemData.description && (
          <span className="text-[11px] text-slate-400 truncate">{itemData.description}</span>
        )}
      </div>
      {showBadge && itemData.badge && badgeStyles && (
        <span
          className={`px-1.5 py-0.5 text-[10px] font-mono rounded flex-shrink-0 border ${badgeStyles.bg} ${badgeStyles.text} ${badgeStyles.border} ${badgeClassName}`}
        >
          {itemData.badge.text}
        </span>
      )}
    </div>
  );
}

export interface SelectContentProps {
  className?: string;
  portal?: boolean;
  children: React.ReactNode;
}

export function SelectContent({ children, className = '', portal = false }: SelectContentProps) {
  const { isOpen, triggerId } = useSelectContext();
  // compute contentId from triggerId to keep IDs stable
  const contentId = `select-content-${triggerId}`;
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen || !portal) return;

    const trigger = document.querySelector(`[data-select-trigger="${triggerId}"]`);
    if (!trigger) return;

    const rect = trigger.getBoundingClientRect();
    const baseTop = rect.bottom + window.scrollY + 4;
    const left = rect.left + window.scrollX;
    const width = rect.width;

    // set tentative position below, then adjust after measuring content height
    setPosition({ top: baseTop, left, width });

    // adjust if not enough space below: measure content after it mounts
    const raf = requestAnimationFrame(() => {
      const el = contentRef.current;
      if (!el) return;
      const height = el.offsetHeight;
      const spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow < height && rect.top > height) {
        // open upwards
        const top = rect.top + window.scrollY - height - 4;
        setPosition({ top, left, width });
      }
    });

    return () => cancelAnimationFrame(raf);

  }, [isOpen, portal, triggerId]);

  useEffect(() => {
    if (!isOpen) return;
    // when opened, focus selected option or first option for keyboard users
    const raf = requestAnimationFrame(() => {
      const root = portal ? document.body : document.querySelector(`[data-select-root]`);
      if (!root) return;
      const content = portal ? document.querySelector(`[data-select-content]`) : root.querySelector(`[data-select-content]`);
      if (!content) return;
      const selected = content.querySelector('[role="option"][aria-selected="true"]') as HTMLElement | null;
      const first = content.querySelector('[role="option"]') as HTMLElement | null;
      (selected || first)?.focus();
    });
    return () => cancelAnimationFrame(raf);
  }, [isOpen, portal]);

  if (!isOpen) return null;

  const content = (
    <div
      ref={contentRef}
      id={contentId}
      role="listbox"
      aria-labelledby={triggerId}
      tabIndex={-1}
      data-select-content
      style={portal ? { 
        position: 'fixed', 
        top: `${position.top}px`, 
        left: `${position.left}px`,
        minWidth: `${position.width}px`,
        zIndex: 9999 
      } : undefined}
      className={`${portal ? '' : 'absolute z-50 mt-1 w-full'} rounded-md border border-slate-700 bg-slate-800 p-1 shadow-lg ${className}`}
    >
      {children}
    </div>
  );

  return portal ? createPortal(content, document.body) : content;
}

export interface SelectGroupProps {
  label?: string;
  children: React.ReactNode;
}

export function SelectGroup({ label, children }: SelectGroupProps) {
  return (
    <div className="py-1">
      {label && (
        <div className="px-2 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {label}
        </div>
      )}
      {children}
    </div>
  );
}

export interface SelectItemProps {
  value: string;
  className?: string;
  children?: React.ReactNode;
  // Rich item props
  icon?: LucideIcon;
  label?: string;
  description?: string;
  badge?: {
    text: string;
    variant: BadgeVariant;
  };
  metadata?: Record<string, string | number>;
  disabled?: boolean;
}

export function SelectItem({ 
  value, 
  children, 
  className = '',
  icon,
  label,
  description,
  badge,
  metadata,
  disabled = false
}: SelectItemProps) {
  const { value: selectedValue, onValueChange, setIsOpen, registerRichItem } = useSelectContext();
  const isSelected = value === selectedValue;

  // Register rich item data synchronously before paint to avoid initial blank value
  useLayoutEffect(() => {
    if (icon || description || badge || label) {
      registerRichItem(value, {
        label: label || (typeof children === 'string' ? children : value),
        icon,
        description,
        badge,
        metadata,
      });
    }
  }, [value, icon, label, description, badge, metadata, children, registerRichItem]);

  const handleClick = () => {
    if (disabled) return;
    onValueChange(value);
    setIsOpen(false);
  };

  const handleKeyDownItem = (e: React.KeyboardEvent) => {
    if (disabled) return;
    const key = e.key;
    if (key === 'Enter' || key === ' ') {
      e.preventDefault();
      handleClick();
      return;
    }
    if (key === 'ArrowDown' || key === 'ArrowUp') {
      e.preventDefault();
      const root = (e.currentTarget as HTMLElement).closest('[data-select-content]') as HTMLElement | null;
      const options = root ? Array.from(root.querySelectorAll('[role="option"]')) as HTMLElement[] : [];
      if (!options.length) return;
      const idx = options.indexOf(e.currentTarget as HTMLElement);
      let nextIdx = idx;
      if (key === 'ArrowDown') nextIdx = (idx + 1) % options.length;
      if (key === 'ArrowUp') nextIdx = (idx - 1 + options.length) % options.length;
      const next = options[nextIdx];
      next?.focus();
    }
  };

  const Icon = icon;
  const badgeStyles = badge ? BADGE_STYLES[badge.variant] : null;

  // Simple mode: just children
  if (!icon && !description && !badge && children) {
    return (
      <div
        role="option"
        aria-selected={isSelected}
        aria-disabled={disabled}
        onClick={handleClick}
        tabIndex={disabled ? -1 : 0}
        onKeyDown={handleKeyDownItem}
        className={`cursor-pointer rounded-sm px-2 py-1.5 text-sm transition-colors ${
          disabled 
            ? 'opacity-50 cursor-not-allowed' 
            : 'hover:bg-slate-700'
        } ${
          isSelected ? 'bg-emerald-500/20 fi-text-success' : 'fi-text'
        } ${className}`}
      >
        {children}
      </div>
    );
  }

  // Rich mode: icon, label, description, badge, metadata
  return (
    <div
      role="option"
      aria-selected={isSelected}
      aria-disabled={disabled}
      onClick={handleClick}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={handleKeyDownItem}
      className={`cursor-pointer rounded-lg px-3 py-2 text-left transition-all ${
        disabled 
          ? 'opacity-50 cursor-not-allowed' 
          : 'hover:bg-slate-700/60'
      } ${
        isSelected 
          ? 'bg-purple-500/20 border-purple-500/50 border' 
          : 'bg-slate-700/30 border border-transparent'
      } ${className}`}
    >
      {/* Top row: Icon, Label, Check */}
      <div className="flex items-center gap-2 mb-1">
        {Icon && (
          <Icon className={`w-4 h-4 ${isSelected ? 'fi-text-purple' : 'text-slate-400'}`} />
        )}
        <span className={`font-medium text-sm ${isSelected ? 'text-purple-200' : 'text-slate-200'}`}>
          {label || children || value}
        </span>
        {isSelected && <Check className="w-4 h-4 fi-text-purple ml-auto" />}
      </div>

      {/* Description */}
      {description && (
        <p className="fi-text-xs mb-2 line-clamp-2">{description}</p>
      )}

      {/* Metadata row: Badge + metadata */}
      {(badge || metadata) && (
        <div className="flex items-center gap-2 flex-wrap">
          {badge && badgeStyles && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono rounded-md border ${badgeStyles.bg} ${badgeStyles.text} ${badgeStyles.border}`}
            >
              {badge.text}
            </span>
          )}
          {metadata && Object.entries(metadata).map(([key, val]) => (
            <span
              key={key}
              className="ui-select-meta-chip"
            >
              {key}: {val}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
