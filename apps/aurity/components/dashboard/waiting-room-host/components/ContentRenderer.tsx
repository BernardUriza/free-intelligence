'use client';

/**
 * ContentRenderer - Switches between widgets and text messages
 */

import { memo } from 'react';
import type { ContentItem } from '../types';
import { TVMessage } from '@/components/ui/message';
import {
  WeatherWidget,
  HealthTriviaWidget,
  BreathingExerciseWidget,
  DailyTipWidget,
  CalmingNatureWidget,
  ClinicImageWidget,
  ClinicVideoWidget,
  ClinicMessageWidget,
} from '@/components/widgets';

interface ContentRendererProps {
  /** Current content item */
  content: ContentItem | null;
  /** Clinic name for weather widget */
  clinicName?: string;
}

export const ContentRenderer = memo(function ContentRenderer({
  content,
  clinicName = 'Clínica',
}: ContentRendererProps) {
  if (!content) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-slate-500">Cargando contenido...</div>
      </div>
    );
  }

  // Render widget
  if (content.type === 'widget' && content.widgetType) {
    return (
      <div className="transform transition-all duration-500 ease-in-out flex-1 flex flex-col min-h-0">
        {content.widgetType === 'weather' && <WeatherWidget city={clinicName} />}
        {content.widgetType === 'trivia' && (
          <HealthTriviaWidget {...(content.widgetData as Record<string, unknown>)} />
        )}
        {content.widgetType === 'breathing' && <BreathingExerciseWidget />}
        {content.widgetType === 'daily_tip' && (
          <DailyTipWidget {...(content.widgetData as Record<string, unknown>)} />
        )}
        {content.widgetType === 'calming' && <CalmingNatureWidget />}
        {content.widgetType === 'clinic_image' && (
          <ClinicImageWidget {...(content.widgetData as Record<string, unknown>)} />
        )}
        {content.widgetType === 'clinic_video' && (
          <ClinicVideoWidget {...(content.widgetData as Record<string, unknown>)} />
        )}
        {content.widgetType === 'clinic_message' && (
          <ClinicMessageWidget {...(content.widgetData as Record<string, unknown>)} />
        )}
      </div>
    );
  }

  // Render text message using TVMessage
  return (
    <TVMessage
      message={{
        role: 'assistant',
        content: content.content.replace(/\*\*(.*?)\*\*/g, '$1'), // Strip markdown bold
        timestamp: new Date().toISOString(),
        metadata: { tone: 'waiting_room_host' },
      }}
      className="flex-1"
    />
  );
});
