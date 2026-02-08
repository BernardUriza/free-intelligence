'use client';

import { Sparkles } from 'lucide-react';

interface PromotionBannerWidgetProps {
  title: string;
  subtitle?: string;
  highlight?: string;
  ctaText?: string;
  backgroundColor?: string;
}

export function PromotionBannerWidget({
  title,
  subtitle,
  highlight,
  ctaText,
  backgroundColor = 'from-purple-950/70 to-indigo-950/70',
}: PromotionBannerWidgetProps) {
  return (
    <div className={`wgt-promo-card bg-gradient-to-br ${backgroundColor}`}>
      {highlight && (
        <div
          className="wgt-promo-highlight"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          {highlight}
        </div>
      )}

      <h2
        className="font-black text-white leading-tight mb-4 sm:mb-6"
        style={{
          fontSize: title.length > 30
            ? 'clamp(1.5rem, 5vw, 4rem)'
            : 'clamp(2rem, 7vw, 6rem)',
        }}
      >
        {title}
      </h2>

      {subtitle && (
        <p className="fi-text max-w-3xl mb-6 sm:mb-8" style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}>
          {subtitle}
        </p>
      )}

      {ctaText && (
        <div
          className="wgt-promo-cta"
          style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
        >
          {ctaText}
        </div>
      )}

      <div className="absolute top-4 right-4 sm:top-8 sm:right-8 opacity-20">
        <Sparkles className="text-white w-24 h-24 sm:w-32 sm:h-32 lg:w-40 lg:h-40" strokeWidth={1} aria-hidden="true" />
      </div>
    </div>
  );
}
