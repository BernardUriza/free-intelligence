interface ProgressBarProps {
  value: number; // 0.0 to 1.0
  color?: 'green' | 'yellow' | 'orange' | 'red';
  height?: string;
  showLabel?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  color = 'green',
  height = '8px',
  showLabel = true,
  className = '',
}: ProgressBarProps) {
  const percentage = Math.round(value * 100);

  const colorClasses = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    orange: 'bg-orange-500',
    red: 'bg-red-500',
  };

  return (
    <div className={`progress-bar-container ${className}`}>
      <div
        className="w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
        style={{ height }}
      >
        <div
          className={`h-full transition-all duration-300 ${colorClasses[color]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-gray-600 dark:text-gray-400 mt-1">
          {percentage}%
        </span>
      )}
    </div>
  );
}
