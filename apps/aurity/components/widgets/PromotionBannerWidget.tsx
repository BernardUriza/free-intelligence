'use client';

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
    <div className={`h-full flex flex-col items-center justify-center bg-gradient-to-br ${backgroundColor} border border-purple-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8 text-center`}>
      {highlight && (
        <div
          className="bg-yellow-500/20 border border-yellow-500/50 text-yellow-300 font-bold px-4 sm:px-6 py-2 sm:py-3 rounded-full mb-4 sm:mb-6 lg:mb-8 animate-pulse"
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
          className="bg-white/10 border border-white/30 text-white font-semibold px-6 sm:px-10 py-3 sm:py-5 rounded-xl"
          style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
        >
          {ctaText}
        </div>
      )}

      <div className="absolute top-4 right-4 sm:top-8 sm:right-8 opacity-20">
        <div className="text-white" style={{ fontSize: 'clamp(4rem, 10vw, 10rem)' }}>
          ✨
        </div>
      </div>
    </div>
  );
}
