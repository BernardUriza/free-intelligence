/**
 * WaitingRoomHost Types
 * Single source of truth for waiting room display types
 */

export interface ContentItem {
  type: 'welcome' | 'tip' | 'metric' | 'philosophy' | 'doctor_message' | 'widget';
  content: string;
  duration?: number; // ms to display (default: 15000)
  metadata?: Record<string, unknown>;
  widgetType?: WidgetType;
  widgetData?: Record<string, unknown>;
}

export type WidgetType =
  | 'weather'
  | 'trivia'
  | 'breathing'
  | 'daily_tip'
  | 'calming'
  | 'clinic_image'
  | 'clinic_video'
  | 'clinic_message';

export interface ClinicSlide {
  media_id: string;
  media_type: 'image' | 'video' | 'message';
  title?: string;
  description?: string;
  file_path?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  uploaded_at: number;
  uploaded_by: string;
  clinic_id: string;
  duration: number;
  is_active: boolean;
}

export interface WaitingRoomHostProps {
  /** Display mode: broadcast (auto-rotate) or interactive (QR enabled) */
  mode?: 'broadcast' | 'interactive';
  /** Clinic name for branding */
  clinicName?: string;
  /** Priority message from doctor control panel */
  doctorMessage?: string | null;
  /** Slides from backend (images, videos, messages) */
  clinicSlides?: ClinicSlide[];
  /** Callback when user interacts (interactive mode) */
  onInteraction?: () => void;
  /** External navigation control (for preview mode) */
  externalCurrentIndex?: number;
  /** Callback when index changes */
  onIndexChange?: (index: number) => void;
  /** Callback when content is loaded */
  onContentLoad?: (totalItems: number, contentArray?: ContentItem[]) => void;
}
