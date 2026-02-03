/**
 * Clinic Media Types
 *
 * Type definitions for waiting room TV content management API.
 * Used by MediaUploader, SlideManager, and waiting-room-host components.
 *
 * API Base: /api/aurity/clinic/clinic-media/*
 * Card: FI-UI-FEAT-TVD-001
 */

// =============================================================================
// Media Types
// =============================================================================

export type MediaType = 'image' | 'video' | 'message';

/**
 * Media item as returned from backend API
 */
export interface MediaItem {
  media_id: string;
  media_type: MediaType;
  title?: string;
  description?: string;
  file_path?: string;
  message_content?: string;
  uploaded_at: number;
  duration: number;
  is_active: boolean;
  display_order?: number;
  clinic_id?: string;
  doctor_id?: string;
}

/**
 * Frontend representation of uploaded media
 */
export interface UploadedMedia {
  mediaId: string;
  mediaType: MediaType;
  title?: string;
  description?: string;
  url?: string; // For image/video
  message?: string; // For text messages
  duration: number; // Display duration in ms
}

// =============================================================================
// API Request/Response Types
// =============================================================================

/**
 * Response from POST /api/aurity/clinic/clinic-media/upload
 */
export interface MediaUploadResponse {
  media_id: string;
  media_type: MediaType;
  title?: string;
  description?: string;
  file_path?: string;
  message_content?: string;
  duration: number;
  is_active: boolean;
  uploaded_at: number;
}

/**
 * Response from GET /api/aurity/clinic/clinic-media/list
 */
export interface MediaListResponse {
  media: MediaItem[];
  total: number;
}

/**
 * Request body for PUT /api/aurity/clinic/clinic-media/:id
 */
export interface MediaUpdateRequest {
  title?: string;
  description?: string;
  duration?: number;
  is_active?: boolean;
  display_order?: number;
}

/**
 * Response from PUT /api/aurity/clinic/clinic-media/:id
 */
export interface MediaUpdateResponse extends MediaItem {}

/**
 * Response from DELETE /api/aurity/clinic/clinic-media/:id
 */
export interface MediaDeleteResponse {
  success: boolean;
  message: string;
}
