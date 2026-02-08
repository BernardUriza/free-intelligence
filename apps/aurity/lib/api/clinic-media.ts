/**
 * Clinic Media API Client
 *
 * CRUD operations for clinic media (images, videos, messages)
 * displayed on the waiting room TV.
 *
 * Card: FI-API-REFAC-001
 * Created: 2026-02-07
 */

import { api, getBackendUrl } from './client';
import { ROUTES } from './routes';

// =============================================================================
// TYPES
// =============================================================================

export interface ClinicMediaItem {
  media_id: string;
  media_type: 'image' | 'video' | 'message';
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

export interface ClinicMediaListResponse {
  media: ClinicMediaItem[];
}

export interface ClinicMediaUploadResponse {
  media_id: string;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

const API_BASE = ROUTES.clinicMedia;

/**
 * List clinic media with optional filters
 */
export async function listClinicMedia(options?: {
  activeOnly?: boolean;
  clinicId?: string;
}): Promise<ClinicMediaItem[]> {
  const params = new URLSearchParams();
  if (options?.clinicId) params.append('clinic_id', options.clinicId);
  params.append('active_only', String(options?.activeOnly ?? true));

  const data = await api.get<ClinicMediaListResponse>(
    `${API_BASE}/list?${params}`
  );
  return data.media || [];
}

/**
 * Upload clinic media (image, video, or message)
 */
export async function uploadClinicMedia(
  formData: FormData
): Promise<ClinicMediaUploadResponse> {
  return api.upload<ClinicMediaUploadResponse>(`${API_BASE}/upload`, formData);
}

/**
 * Delete a clinic media item
 */
export async function deleteClinicMedia(mediaId: string): Promise<void> {
  await api.delete(`${API_BASE}/${mediaId}`);
}

/**
 * Update a clinic media item (e.g., toggle active)
 */
export async function updateClinicMedia(
  mediaId: string,
  data: Partial<Pick<ClinicMediaItem, 'is_active' | 'title' | 'description' | 'duration' | 'display_order'>>
): Promise<void> {
  await api.put(`${API_BASE}/${mediaId}`, data);
}

/**
 * Build a full URL for a media file (for <img>/<video> src)
 */
export function buildMediaFileUrl(filePath: string): string {
  return `${getBackendUrl()}${API_BASE}/file/${filePath}`;
}
