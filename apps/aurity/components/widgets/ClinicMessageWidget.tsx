'use client';

interface ClinicMessageWidgetProps {
  message: string;
  title?: string;
}

export function ClinicMessageWidget({ message, title }: ClinicMessageWidgetProps) {
  return (
    <div className="wgt-message-card">
      <div className="wgt-message-header">
        <div className="wgt-message-avatar">
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
          <h3 className="wgt-message-title" style={{ fontSize: 'clamp(1.25rem, 2.5vw, 2.5rem)' }}>
            {title || 'Mensaje del Doctor'}
          </h3>
          <p className="wgt-message-subtitle" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}>
            Información importante
          </p>
        </div>
      </div>

      <div className="wgt-message-body">
        <p
          className="wgt-message-text"
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

      <div className="wgt-message-footer">
        <div className="wgt-message-pulse-row" style={{ fontSize: 'clamp(0.7rem, 1vw, 1rem)' }}>
          <div className="wgt-message-pulse-dot" />
          <span>Mensaje personalizado de su clínica</span>
        </div>
      </div>
    </div>
  );
}
