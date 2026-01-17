'use client';

/**
 * WaitingRoomHost - Main orchestrator component
 *
 * Displays Free Intelligence as a welcoming host in clinic waiting rooms.
 * Inspired by Telesecundaria model + modern AI receptionist systems.
 *
 * SOLID Architecture:
 * - Single Responsibility: Orchestrates subcomponents
 * - Open/Closed: Easy to add new widget types
 * - Dependency Inversion: Uses hook for content logic
 */

import type { WaitingRoomHostProps } from './types';
import { useWaitingRoomContent } from './hooks/useWaitingRoomContent';
import { AvatarIndicator } from './components/AvatarIndicator';
import { ContentRenderer } from './components/ContentRenderer';
import { ProgressIndicator } from './components/ProgressIndicator';
import { InteractiveHint } from './components/InteractiveHint';

export function WaitingRoomHost({
  mode = 'broadcast',
  clinicName = 'nuestra clínica',
  doctorMessage = null,
  clinicSlides = [],
  onInteraction,
  externalCurrentIndex,
  onIndexChange,
  onContentLoad,
}: WaitingRoomHostProps) {
  const { content, currentIndex, currentContent } = useWaitingRoomContent({
    clinicSlides,
    doctorMessage,
    externalCurrentIndex,
    onIndexChange,
    onContentLoad,
  });

  // Handle interaction (future: QR code → chat)
  const handleClick = () => {
    if (mode === 'interactive' && onInteraction) {
      onInteraction();
    }
  };

  return (
    <div className="relative h-full flex flex-col" onClick={handleClick}>
      {/* Avatar Container */}
      <div className="flex items-start gap-4 sm:gap-6 flex-1 min-h-0">
        {/* Left: Avatar Icon */}
        <AvatarIndicator />

        {/* Right: Content Area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Content (Widget or Message) */}
          <ContentRenderer content={currentContent} clinicName={clinicName} />

          {/* Progress indicator */}
          <ProgressIndicator total={content.length} current={currentIndex} />

          {/* Interaction hint (if interactive mode) */}
          {mode === 'interactive' && <InteractiveHint />}
        </div>
      </div>

      {/* Clinic branding footer removed - InfoBar in dashboard/page.tsx handles this */}
    </div>
  );
}

// Re-export types for convenience
export type { WaitingRoomHostProps, ContentItem, ClinicSlide } from './types';
