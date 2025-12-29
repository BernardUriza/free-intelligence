'use client';

/**
 * LicenseRenewalBanner - Displays license expiration warnings
 *
 * Shows a dismissible banner when:
 * - License expires in <= 30 days (yellow warning)
 * - License expires in <= 7 days (orange urgent warning)
 * - License has expired (red critical warning)
 */

import { useState, useEffect, useCallback } from 'react';
import { useLicense, RenewalStatus } from '@/hooks/useLicense';

interface LicenseRenewalBannerProps {
  className?: string;
}

export function LicenseRenewalBanner({ className = '' }: LicenseRenewalBannerProps) {
  const { renewalStatus, requestRenewal, checkRenewalStatus, isValid, daysRemaining } = useLicense();
  const [isDismissed, setIsDismissed] = useState(false);
  const [isRenewing, setIsRenewing] = useState(false);
  const [renewError, setRenewError] = useState<string | null>(null);

  // Reset dismissed state when renewal status changes significantly
  useEffect(() => {
    if (renewalStatus?.needs_renewal) {
      // If days changed by more than 1, show banner again
      setIsDismissed(false);
    }
  }, [renewalStatus?.days_until_expiry]);

  // Don't show if dismissed, no renewal needed, or no warning message
  if (isDismissed || !renewalStatus?.warning_message) {
    return null;
  }

  const days = renewalStatus.days_until_expiry ?? 0;

  // Determine severity
  const isExpired = days < 0;
  const isCritical = days <= 7 && !isExpired;
  const isWarning = days <= 30 && !isCritical && !isExpired;

  // Style based on severity
  const bgColor = isExpired
    ? 'bg-red-600'
    : isCritical
    ? 'bg-orange-500'
    : 'bg-yellow-500';

  const textColor = isExpired || isCritical ? 'text-white' : 'text-gray-900';

  const handleRenew = async () => {
    setIsRenewing(true);
    setRenewError(null);

    try {
      const response = await requestRenewal();

      if (response.renewed) {
        // Success! Banner will hide automatically after checkRenewalStatus
        await checkRenewalStatus();
      } else if (response.renewal_url) {
        // Need to redirect to payment
        window.open(response.renewal_url, '_blank');
      } else {
        setRenewError(response.message);
      }
    } catch (err) {
      setRenewError(err instanceof Error ? err.message : 'Renewal failed');
    } finally {
      setIsRenewing(false);
    }
  };

  const handleDismiss = () => {
    setIsDismissed(true);
  };

  return (
    <div className={`${bgColor} ${textColor} px-4 py-3 ${className}`}>
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Icon + Message */}
        <div className="flex items-center gap-3">
          {/* Warning Icon */}
          <svg
            className="h-5 w-5 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
              clipRule="evenodd"
            />
          </svg>

          <p className="text-sm font-medium">
            {renewalStatus.warning_message}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          {/* Error message */}
          {renewError && (
            <span className="text-xs opacity-80 mr-2">{renewError}</span>
          )}

          {/* Renew Button */}
          <button
            onClick={handleRenew}
            disabled={isRenewing}
            className={`
              text-sm font-medium px-3 py-1 rounded-md
              ${isExpired || isCritical
                ? 'bg-white text-red-600 hover:bg-gray-100'
                : 'bg-gray-900 text-white hover:bg-gray-800'
              }
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors
            `}
          >
            {isRenewing ? 'Renewing...' : isExpired ? 'Renew Now' : 'Renew'}
          </button>

          {/* Open renewal URL directly */}
          {renewalStatus.renewal_url && !isExpired && (
            <a
              href={renewalStatus.renewal_url}
              target="_blank"
              rel="noopener noreferrer"
              className={`
                text-sm underline opacity-80 hover:opacity-100
                ${textColor}
              `}
            >
              Go to billing
            </a>
          )}

          {/* Dismiss (only for warnings, not expired) */}
          {!isExpired && (
            <button
              onClick={handleDismiss}
              className="p-1 rounded-full hover:bg-black/10 transition-colors"
              aria-label="Dismiss"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
