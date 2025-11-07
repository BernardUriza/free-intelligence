/**
 * T21Button - Accessible button component for Down Syndrome athletes
 * AC: Botones XL (min 44px), verbos simples, alto contraste ≥7:1, sin penalidades
 */

import React from 'react';

interface T21ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'success' | 'warning' | 'info';
  size?: 'lg' | 'xl' | '2xl';
  icon?: React.ReactNode;
  ariaLabel: string;
}

export const T21Button: React.FC<T21ButtonProps> = ({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'xl',
  icon,
  ariaLabel,
}) => {
  const sizeClasses = {
    lg: 'px-6 py-4 text-lg',
    xl: 'px-8 py-6 text-2xl',
    '2xl': 'px-10 py-8 text-3xl',
  };

  const variantClasses = {
    primary: 'bg-blue-700 hover:bg-blue-800 text-white border-4 border-blue-900',
    success: 'bg-green-700 hover:bg-green-800 text-white border-4 border-green-900',
    warning: 'bg-yellow-600 hover:bg-yellow-700 text-black border-4 border-yellow-800',
    info: 'bg-purple-700 hover:bg-purple-800 text-white border-4 border-purple-900',
  };

  const disabledClasses = disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer active:scale-95 transition-transform';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className={`
        rounded-lg font-bold uppercase tracking-wider
        focus:outline-2 focus:outline-offset-2 focus:outline-white
        transition-all duration-200 ease-in-out
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${disabledClasses}
      `}
    >
      <div className="flex items-center justify-center gap-3">
        {icon && <span className="text-3xl">{icon}</span>}
        <span>{children}</span>
      </div>
    </button>
  );
};
