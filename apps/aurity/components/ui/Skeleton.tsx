'use client';

import { cn } from '@/lib/utils';

type SkeletonVariant = 'text' | 'circular' | 'rectangular';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: SkeletonVariant;
  className?: string;
  animate?: boolean;
}

const variantStyles: Record<SkeletonVariant, string> = {
  text: 'h-4 w-full rounded',
  circular: 'rounded-full',
  rectangular: 'rounded-lg',
};

export function Skeleton({
  width,
  height,
  variant = 'rectangular',
  className,
  animate = true,
}: SkeletonProps) {
  return (
    <div
      className={cn(
        'bg-slate-700',
        variantStyles[variant],
        animate && 'animate-pulse',
        className
      )}
      style={{
        width: width ?? (variant === 'circular' ? 40 : '100%'),
        height: height ?? (variant === 'circular' ? 40 : variant === 'text' ? 16 : 32),
      }}
    />
  );
}

export default Skeleton;
