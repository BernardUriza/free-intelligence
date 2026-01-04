'use client';

interface ClinicMessageWidgetProps {
  message: string;
  title?: string;
}

export function ClinicMessageWidget({ message, title }: ClinicMessageWidgetProps) {
  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-indigo-950/60 to-violet-950/40 border border-indigo-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      <div className="flex items-center gap-4 sm:gap-6 mb-4 sm:mb-6 flex-shrink-0">
        <div className="rounded-full bg-gradient-to-br from-indigo-600/30 to-violet-600/30 border-2 border-indigo-500/40 flex items-center justify-center p-4 sm:p-6">
          <svg
            className="text-indigo-300"
            fill="currentColor"
            viewBox="0 0 20 20"
            style={{ width: 'clamp(2rem, 4vw, 4rem)', height: 'clamp(2rem, 4vw, 4rem)' }}
          >
            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
          </svg>
        </div>
        <div>
          <h3 className="font-bold text-indigo-300" style={{ fontSize: 'clamp(1.25rem, 2.5vw, 2.5rem)' }}>
            {title || 'Mensaje del Doctor'}
          </h3>
          <p className="text-indigo-400/60" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}>
            Información importante
          </p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center min-h-0 px-4 sm:px-8 lg:px-16">
        <p
          className="text-white text-center leading-relaxed font-medium"
          style={{
            fontSize: message.length > 200
              ? 'clamp(1rem, 2vw, 1.75rem)'
              : message.length > 100
              ? 'clamp(1.25rem, 3vw, 2.5rem)'
              : 'clamp(1.5rem, 4vw, 3.5rem)',
            maxWidth: '90%',
          }}
        >
          {message}
        </p>
      </div>

      <div className="flex-shrink-0 mt-4 pt-4 border-t border-indigo-700/30">
        <div className="flex items-center justify-center gap-2 text-indigo-400" style={{ fontSize: 'clamp(0.7rem, 1vw, 1rem)' }}>
          <div className="w-2 h-2 sm:w-3 sm:h-3 bg-indigo-500 rounded-full animate-pulse" />
          <span>Mensaje personalizado de su clínica</span>
        </div>
      </div>
    </div>
  );
}
