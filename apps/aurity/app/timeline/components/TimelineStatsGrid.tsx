/** Stats cards row — total events, chat, audio, duration. */

'use client';

import React from 'react';
import { MessageCircle, Mic } from 'lucide-react';
import type { TimelineMetrics } from '../types';

interface TimelineStatsGridProps {
  metrics: TimelineMetrics;
}

export function TimelineStatsGrid({ metrics }: TimelineStatsGridProps) {
  return (
    <div className="tl-stats-grid">
      <div className="fi-stat-card">
        <div className="fi-stat-value">{metrics.totalEvents}</div>
        <div className="fi-stat-label">Total Eventos</div>
      </div>

      <div className="fi-stat-card-sky">
        <div className="tl-stat-inner">
          <MessageCircle className="tl-stat-icon-sky" />
          <div className="tl-stat-value-sky">{metrics.chatCount}</div>
        </div>
        <div className="fi-text-xs">Chat Messages</div>
      </div>

      <div className="fi-stat-card-emerald">
        <div className="tl-stat-inner">
          <Mic className="tl-stat-icon-sm fi-text-success" />
          <div className="tl-stat-value-accent fi-text-success">
            {metrics.audioCount}
          </div>
        </div>
        <div className="fi-text-xs">Transcripciones</div>
      </div>

      <div className="fi-stat-card">
        <div className="fi-stat-value">
          {metrics.totalDuration.toFixed(0)}s
        </div>
        <div className="fi-stat-label">Audio Total</div>
      </div>
    </div>
  );
}
