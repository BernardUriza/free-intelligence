'use client';

export function ModelRowSkeleton() {
  return (
    <div className="relative flex items-center gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 overflow-hidden">
      {/* Wave animation overlay */}
      <div className="fi-shimmer" />

      {/* Source Icon Skeleton */}
      <div className="flex-shrink-0 w-8 h-8 bg-slate-700 rounded-lg animate-pulse" />

      {/* Content Skeleton */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="fi-flex-gap">
          <div className="h-4 w-32 bg-slate-700 rounded animate-pulse" />
          <div className="h-4 w-12 bg-slate-700/50 rounded animate-pulse" />
        </div>
        <div className="fi-flex-gap-md">
          <div className="h-3 w-16 bg-slate-700/70 rounded animate-pulse" />
          <div className="h-3 w-14 bg-slate-700/70 rounded animate-pulse" />
          <div className="h-3 w-10 bg-slate-700/70 rounded animate-pulse" />
        </div>
      </div>

      {/* Action Button Skeleton */}
      <div className="flex-shrink-0 w-20 h-8 bg-slate-700 rounded-lg animate-pulse" />
    </div>
  );
}
