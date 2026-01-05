import React from 'react';
import { twMerge } from 'tailwind-merge';

type SkeletonProps = {
  width?: string;
  height?: string;
  variant: 'text' | 'circular' | 'rectangular';
  className?: string;
  animate?: boolean;
};

const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height,
  variant,
  className,
  animate,
}) => {
  const styles = twMerge(
    `bg-gray-200 rounded-lg`,
    variant === 'text' && `h-4 w-full`,
    variant === 'circular' && `h-16 w-16 rounded-full`,
    variant === 'rectangular' && `h-8 w-full`,
    animate && `animate-pulse`
  );

  return (
    <div className={twMerge(styles, className)} style={{ width, height }} />
  );
};

export default Skeleton;
export { Skeleton };
