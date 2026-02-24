/**
 * SuperadminBanner
 *
 * Top-level badge showing current superadmin identity.
 */

import { Star } from 'lucide-react';
import type { SuperadminBannerProps } from '../types';

export function SuperadminBanner({ email }: SuperadminBannerProps) {
  return (
    <div className="cfg-superadmin-banner">
      <div className="fi-flex-gap">
        <Star className="cfg-superadmin-star" />
        <span className="cfg-superadmin-label">SUPERADMIN Access</span>
        <span className="cfg-superadmin-dot">·</span>
        <span className="cfg-superadmin-email">{email}</span>
      </div>
    </div>
  );
}
