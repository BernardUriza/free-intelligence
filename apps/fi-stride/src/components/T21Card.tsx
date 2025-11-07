/**
 * T21Card - Accessible card component with large text and high contrast
 * AC: Paleta limitada (3-4 colores), animaciones suaves (<300ms), verbos simples
 */

import React from 'react';

interface T21CardProps {
  title: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
  color?: 'blue' | 'green' | 'yellow' | 'purple';
  onClick?: () => void;
}

export const T21Card: React.FC<T21CardProps> = ({
  title,
  children,
  icon,
  color = 'blue',
  onClick,
}) => {
  const colorClasses = {
    blue: 'border-blue-700 bg-blue-50 shadow-lg hover:shadow-xl',
    green: 'border-green-700 bg-green-50 shadow-lg hover:shadow-xl',
    yellow: 'border-yellow-700 bg-yellow-50 shadow-lg hover:shadow-xl',
    purple: 'border-purple-700 bg-purple-50 shadow-lg hover:shadow-xl',
  };

  return (
    <div
      onClick={onClick}
      className={`
        border-4 rounded-lg p-6
        transition-all duration-200 ease-out
        ${colorClasses[color]}
        ${onClick ? 'cursor-pointer active:scale-98' : ''}
      `}
    >
      <div className="flex items-center gap-4 mb-4">
        {icon && <span className="text-5xl">{icon}</span>}
        <h3 className="text-3xl font-bold text-gray-900 uppercase">{title}</h3>
      </div>
      <div className="text-xl text-gray-800 leading-relaxed">{children}</div>
    </div>
  );
};
