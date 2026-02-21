import { CheckCircle, AlertCircle } from 'lucide-react';

import type { StatusMessage as StatusMessageType } from '../types';

interface StatusMessageProps {
  message: StatusMessageType;
}

export function StatusMessage({ message }: StatusMessageProps) {
  const isSuccess = message.type === 'success';

  return (
    <div className={isSuccess ? 'demo-status-msg-success' : 'demo-status-msg-error'}>
      {isSuccess ? (
        <CheckCircle className="demo-status-icon fi-text-success" />
      ) : (
        <AlertCircle className="demo-status-icon fi-text-error" />
      )}
      <p className={isSuccess ? 'demo-status-text-success' : 'demo-status-text-error'}>
        {message.text}
      </p>
    </div>
  );
}
