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
    const data = content.widgetData ?? {};
    return (
      <div className="transform transition-all duration-500 ease-in-out flex-1 flex flex-col min-h-0">
        {content.widgetType === 'weather' && <WeatherWidget city={clinicName} />}
        {content.widgetType === 'trivia' && (
          <HealthTriviaWidget
            question={String(data.question ?? 'Pregunta de trivia')}
            options={Array.isArray(data.options) ? data.options.map(String) : ['A', 'B', 'C', 'D']}
            correctAnswer={typeof data.correctAnswer === 'number' ? data.correctAnswer : 0}
            explanation={String(data.explanation ?? 'Respuesta correcta')}
          />
        )}
        {content.widgetType === 'breathing' && <BreathingExerciseWidget />}
        {content.widgetType === 'daily_tip' && (
          <DailyTipWidget
            tip={String(data.tip ?? 'Tip del día')}
            category={(data.category as 'nutrition' | 'exercise' | 'mental_health' | 'prevention') ?? 'prevention'}
          />
        )}
        {content.widgetType === 'calming' && <CalmingNatureWidget />}
        {content.widgetType === 'clinic_image' && (
          <ClinicImageWidget
            imageUrl={String(data.imageUrl ?? '')}
            title={typeof data.title === 'string' ? data.title : undefined}
            description={typeof data.description === 'string' ? data.description : undefined}
          />
        )}
        {content.widgetType === 'clinic_video' && (
          <ClinicVideoWidget
            videoUrl={String(data.videoUrl ?? '')}
            title={typeof data.title === 'string' ? data.title : undefined}
            description={typeof data.description === 'string' ? data.description : undefined}
          />
        )}
        {content.widgetType === 'clinic_message' && (
          <ClinicMessageWidget
            message={String(data.message ?? 'Mensaje de la clínica')}
            title={typeof data.title === 'string' ? data.title : undefined}
          />
        )}
      </div>
    );
  }

  // Render text message using TVMessage
  // Note: 'waiting_room_host' is not a valid FITone, use 'neutral' for TV display
  return (
    <TVMessage
      message={{
        role: 'assistant',
        content: content.content.replace(/\*\*(.*?)\*\*/g, '$1'), // Strip markdown bold
        timestamp: new Date().toISOString(),
        metadata: { tone: 'neutral' },
      }}
      className="flex-1"
    />
  );
});
