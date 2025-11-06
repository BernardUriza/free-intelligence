import React from 'react';

/**
 * T21Pack - UI Components specifically designed for athletes with Down Syndrome (Trisomy 21)
 *
 * Design principles:
 * - Large, clear UI elements (minimum 48px tap targets)
 * - High contrast colors (blue, orange, green - easily distinguishable)
 * - Simple, single-action buttons (avoid multi-step workflows)
 * - Emoji/visual indicators alongside text
 * - Short, simple sentences (easy reading)
 * - Progress visualization (visual feedback)
 */

interface T21ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  emoji?: string;
  label: string;
  variant?: 'primary' | 'success' | 'warning' | 'danger';
}

export function T21Button({
  emoji = '✓',
  label,
  variant = 'primary',
  className,
  ...props
}: T21ButtonProps) {
  const variantClasses = {
    primary: 'bg-blue-500 hover:bg-blue-600 focus:ring-blue-400',
    success: 'bg-green-500 hover:bg-green-600 focus:ring-green-400',
    warning: 'bg-orange-500 hover:bg-orange-600 focus:ring-orange-400',
    danger: 'bg-red-500 hover:bg-red-600 focus:ring-red-400',
  };

  return (
    <button
      {...props}
      className={`w-full p-6 rounded-xl text-white text-2xl font-bold
        flex items-center justify-center gap-4
        focus:outline-none focus:ring-4
        transition-all active:scale-95
        min-h-24
        ${variantClasses[variant]}
        ${className || ''}`}
    >
      <span className="text-4xl">{emoji}</span>
      <span>{label}</span>
    </button>
  );
}

interface T21CardProps {
  emoji?: string;
  title: string;
  description: string;
  onClick?: () => void;
  selected?: boolean;
}

export function T21Card({
  emoji = '📍',
  title,
  description,
  onClick,
  selected = false,
}: T21CardProps) {
  return (
    <div
      onClick={onClick}
      className={`p-6 rounded-xl border-4 cursor-pointer transition-all ${
        selected ? 'border-blue-500 bg-blue-900 scale-105' : 'border-slate-600 bg-slate-800 hover:border-slate-500'
      }`}
    >
      <div className="text-5xl mb-3">{emoji}</div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-slate-300">{description}</p>
    </div>
  );
}

interface T21ProgressProps {
  current: number;
  total: number;
}

export function T21Progress({ current, total }: T21ProgressProps) {
  const percentage = (current / total) * 100;

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-2">
        <span className="text-lg font-bold">{current}</span>
        <span className="text-xl">de</span>
        <span className="text-lg font-bold">{total}</span>
      </div>
      <div className="w-full bg-slate-700 rounded-full h-4 overflow-hidden">
        <div
          className="bg-blue-500 h-full transition-all rounded-full"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

interface T21StatusProps {
  emoji: string;
  status: string;
  description?: string;
}

export function T21Status({ emoji, status, description }: T21StatusProps) {
  return (
    <div className="text-center py-8">
      <div className="text-6xl mb-4">{emoji}</div>
      <h2 className="text-3xl font-bold mb-2">{status}</h2>
      {description && <p className="text-lg text-slate-300">{description}</p>}
    </div>
  );
}

interface T21PanelProps {
  title: string;
  children: React.ReactNode;
}

export function T21Panel({ title, children }: T21PanelProps) {
  return (
    <div className="bg-slate-800 rounded-xl border-2 border-slate-700 p-6">
      <h2 className="text-2xl font-bold mb-6">{title}</h2>
      <div className="space-y-4">{children}</div>
    </div>
  );
}
