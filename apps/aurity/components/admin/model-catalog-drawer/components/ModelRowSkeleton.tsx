'use client';

export function ModelRowSkeleton() {
  return (
    <div className="mdl-skel-row">
      {/* Wave animation overlay */}
      <div className="fi-shimmer" />

      {/* Source Icon Skeleton */}
      <div className="mdl-skel-icon" />

      {/* Content Skeleton */}
      <div className="mdl-skel-content">
        <div className="fi-flex-gap">
          <div className="mdl-skel-name" />
          <div className="mdl-skel-version" />
        </div>
        <div className="fi-flex-gap-md">
          <div className="mdl-skel-detail-a" />
          <div className="mdl-skel-detail-b" />
          <div className="mdl-skel-detail-c" />
        </div>
      </div>

      {/* Action Button Skeleton */}
      <div className="mdl-skel-action" />
    </div>
  );
}
