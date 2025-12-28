'use client';

import { memo } from 'react';
import { AlertCircle } from 'lucide-react';

interface ErrorStateProps {
  message: string;
}

export const ErrorState = memo(function ErrorState({ message }: ErrorStateProps) {
  return (
    <div
      className="p-6 rounded-lg bg-red-500/10 border border-red-500/30"
      role="alert"
    >
      <AlertCircle className="h-6 w-6 text-red-400 mb-2" aria-hidden="true" />
      <p className="fi-text-error">{message}</p>
    </div>
  );
});
