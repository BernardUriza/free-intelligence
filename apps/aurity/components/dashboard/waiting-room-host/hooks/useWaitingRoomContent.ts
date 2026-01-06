/**
 * useWaitingRoomContent - Content loading and rotation logic
 * Headless hook that manages content state for WaitingRoomHost
 */

import { useState, useEffect, useCallback } from 'react';
import type { ContentItem, ClinicSlide } from '../types';
import { fetchContentSeeds, buildMediaUrl } from '../services/content-api';

interface UseWaitingRoomContentOptions {
  /** Slides from clinic backend */
  clinicSlides?: ClinicSlide[];
  /** Priority message from doctor */
  doctorMessage?: string | null;
  /** External index control (for preview mode) */
  externalCurrentIndex?: number;
  /** Callback when index changes */
  onIndexChange?: (index: number) => void;
  /** Callback when content is loaded */
  onContentLoad?: (totalItems: number, contentArray?: ContentItem[]) => void;
}

interface UseWaitingRoomContentReturn {
  /** All content items */
  content: ContentItem[];
  /** Current content index */
  currentIndex: number;
  /** Current content item */
  currentContent: ContentItem | null;
  /** Is loading */
  isLoading: boolean;
  /** Navigate to specific index */
  goToIndex: (index: number) => void;
  /** Go to next content */
  next: () => void;
  /** Go to previous content */
  prev: () => void;
}

/**
 * Convert clinic slides to content items
 */
function convertSlidesToContent(slides: ClinicSlide[]): ContentItem[] {
  return slides
    .filter((slide) => slide.is_active)
    .map((slide) => {
      if (slide.media_type === 'image' && slide.file_path) {
        return {
          type: 'widget' as const,
          content: '',
          duration: slide.duration,
          widgetType: 'clinic_image' as const,
          widgetData: {
            imageUrl: buildMediaUrl(slide.file_path),
            title: slide.title,
            description: slide.description,
          },
        };
      }

      if (slide.media_type === 'video' && slide.file_path) {
        return {
          type: 'widget' as const,
          content: '',
          duration: slide.duration,
          widgetType: 'clinic_video' as const,
          widgetData: {
            videoUrl: buildMediaUrl(slide.file_path),
            title: slide.title,
            description: slide.description,
          },
        };
      }

      // Message type
      return {
        type: 'widget' as const,
        content: '',
        duration: slide.duration,
        widgetType: 'clinic_message' as const,
        widgetData: {
          message: slide.description || slide.title || 'Mensaje',
          title: slide.title,
        },
      };
    });
}

export function useWaitingRoomContent(
  options: UseWaitingRoomContentOptions
): UseWaitingRoomContentReturn {
  const {
    clinicSlides = [],
    doctorMessage,
    externalCurrentIndex,
    onIndexChange,
    onContentLoad,
  } = options;

  const [content, setContent] = useState<ContentItem[]>([]);
  const [internalCurrentIndex, setInternalCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Use external index if provided, otherwise internal
  const currentIndex =
    externalCurrentIndex !== undefined ? externalCurrentIndex : internalCurrentIndex;

  const currentContent = content[currentIndex] || null;

  // Load content on mount
  useEffect(() => {
    let isActive = true;

    async function loadContent() {
      try {
        setIsLoading(true);

        // 1. Fetch base content seeds from API
        const baseSeeds = await fetchContentSeeds();

        if (!isActive) return;

        // 2. Convert and append clinic slides
        const slideContent = convertSlidesToContent(clinicSlides);
        const updatedContent = [...baseSeeds, ...slideContent];

        setContent(updatedContent);
        onContentLoad?.(updatedContent.length, updatedContent);
      } catch {
        if (!isActive) return;
        onContentLoad?.(0);
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    loadContent();

    return () => {
      isActive = false;
    };
  }, [clinicSlides, onContentLoad]);

  // Inject doctor message when provided
  useEffect(() => {
    if (!doctorMessage) return;

    const doctorContent: ContentItem = {
      type: 'doctor_message',
      content: `📢 **Mensaje del Doctor**: ${doctorMessage}`,
      duration: 20000, // Doctor messages stay longer
    };

    setContent((prev) => {
      const newContent = [...prev];
      // Insert at index 1 (after welcome)
      newContent.splice(1, 0, doctorContent);
      return newContent;
    });

    // Reset to beginning to show doctor message
    if (externalCurrentIndex === undefined) {
      setInternalCurrentIndex(0);
      onIndexChange?.(0);
    }
  }, [doctorMessage, externalCurrentIndex, onIndexChange]);

  // Auto-advance content rotation
  useEffect(() => {
    if (!currentContent || externalCurrentIndex !== undefined) {
      return;
    }

    const duration = currentContent.duration || 15000;

    const timer = setTimeout(() => {
      const nextIndex = (currentIndex + 1) % content.length;
      setInternalCurrentIndex(nextIndex);
      onIndexChange?.(nextIndex);
    }, duration);

    return () => clearTimeout(timer);
  }, [currentIndex, currentContent, content.length, externalCurrentIndex, onIndexChange]);

  // Navigation functions
  const goToIndex = useCallback(
    (index: number) => {
      const safeIndex = Math.max(0, Math.min(index, content.length - 1));
      if (externalCurrentIndex === undefined) {
        setInternalCurrentIndex(safeIndex);
      }
      onIndexChange?.(safeIndex);
    },
    [content.length, externalCurrentIndex, onIndexChange]
  );

  const next = useCallback(() => {
    goToIndex((currentIndex + 1) % content.length);
  }, [goToIndex, currentIndex, content.length]);

  const prev = useCallback(() => {
    goToIndex((currentIndex - 1 + content.length) % content.length);
  }, [goToIndex, currentIndex, content.length]);

  return {
    content,
    currentIndex,
    currentContent,
    isLoading,
    goToIndex,
    next,
    prev,
  };
}
