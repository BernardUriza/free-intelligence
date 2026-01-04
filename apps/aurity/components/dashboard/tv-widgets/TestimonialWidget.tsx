'use client';

interface TestimonialWidgetProps {
  quote: string;
  author: string;
  role?: string;
  rating?: number;
}

export function TestimonialWidget({
  quote,
  author,
  role = 'Paciente',
  rating = 5,
}: TestimonialWidgetProps) {
  return (
    <div className="h-full flex flex-col items-center justify-center bg-gradient-to-br from-amber-950/50 to-orange-950/50 border border-amber-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8 text-center relative overflow-hidden">
      <div
        className="absolute top-2 sm:top-4 left-4 sm:left-8 text-amber-500/20 font-serif"
        style={{ fontSize: 'clamp(6rem, 15vw, 15rem)' }}
      >
        &quot;
      </div>

      <div className="flex items-center gap-1 sm:gap-2 mb-4 sm:mb-6 lg:mb-8 z-10">
        {[...Array(5)].map((_, i) => (
          <span
            key={i}
            className={i < rating ? 'text-yellow-400' : 'text-slate-600'}
            style={{ fontSize: 'clamp(1.5rem, 3vw, 3rem)' }}
          >
            ★
          </span>
        ))}
      </div>

      <p
        className="text-white font-medium leading-relaxed mb-6 sm:mb-8 lg:mb-10 max-w-4xl z-10"
        style={{
          fontSize: quote.length > 150
            ? 'clamp(1rem, 2vw, 1.75rem)'
            : quote.length > 80
            ? 'clamp(1.25rem, 2.5vw, 2.25rem)'
            : 'clamp(1.5rem, 3vw, 2.75rem)',
        }}
      >
        &quot;{quote}&quot;
      </p>

      <div className="z-10">
        <p className="font-bold text-amber-300 mb-1" style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}>
          — {author}
        </p>
        <p className="fi-text-warning/70" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}>
          {role}
        </p>
      </div>

      <div
        className="absolute bottom-2 sm:bottom-4 right-4 sm:right-8 text-amber-500/20 font-serif rotate-180"
        style={{ fontSize: 'clamp(6rem, 15vw, 15rem)' }}
      >
        &quot;
      </div>
    </div>
  );
}
