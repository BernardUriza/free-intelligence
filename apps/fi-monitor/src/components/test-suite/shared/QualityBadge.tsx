interface QualityBadgeProps {
  value: number; // 0.0 to 1.0
  className?: string;
}

export function QualityBadge({ value, className = '' }: QualityBadgeProps) {
  const getQuality = (val: number): { label: string; color: string } => {
    if (val > 0.8) return { label: 'Excellent', color: 'bg-green-100 text-green-800' };
    if (val > 0.6) return { label: 'Good', color: 'bg-yellow-100 text-yellow-800' };
    if (val > 0.4) return { label: 'Fair', color: 'bg-orange-100 text-orange-800' };
    return { label: 'Poor', color: 'bg-red-100 text-red-800' };
  };

  const quality = getQuality(value);

  return (
    <span
      className={`quality-badge px-2 py-1 rounded-full text-xs font-medium ${quality.color} ${className}`}
    >
      {quality.label}
    </span>
  );
}
