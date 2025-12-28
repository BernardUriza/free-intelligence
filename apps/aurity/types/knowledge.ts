/**
 * Knowledge Base Types
 *
 * TypeScript types for document management in the Knowledge Base.
 * Card: FI-UI-FEAT-021
 */

/** Document type based on file extension */
export type DocumentType = 'pdf' | 'docx' | 'markdown' | 'text' | 'image' | 'unknown';

/** Document processing status */
export type DocumentStatus = 'pending' | 'processing' | 'indexed' | 'error';

/** Document origin */
export type DocumentOrigin = 'upload' | 'api' | 'system';

/** Document metadata */
export interface DocumentMetadata {
  doc_id: string;
  title: string;
  filename?: string;  // May not be returned by backend detail endpoint
  doc_type: DocumentType;
  status: DocumentStatus;
  origin: DocumentOrigin;
  size_bytes: number;
  sha256: string;
  uploaded_by: string;
  uploaded_at: string;
  updated_at?: string;  // May not always be present
  usage_instructions: string;
  assigned_personas: string[];
  chunks_count: number;  // Backend uses chunks_count
  error_message: string | null;
}

/** Full document with content and text */
export interface Document {
  metadata: DocumentMetadata;
  content?: Uint8Array; // Raw bytes
  text?: string;        // Extracted text
}

/** Document list response */
export interface DocumentsListResponse {
  documents: DocumentMetadata[];
  total: number;
}

/** Document upload request */
export interface DocumentUploadRequest {
  file: File;
  title?: string;
  usage_instructions?: string;
  assigned_personas?: string[];
}

/** Document update request */
export interface DocumentUpdateRequest {
  title?: string;
  usage_instructions?: string;
  assigned_personas?: string[];
}

/** Semantic search result */
export interface SearchResult {
  doc_id: string;
  chunk_id: number;
  similarity: number;
  text: string;
  metadata: DocumentMetadata;
}

/** Search request */
export interface SearchRequest {
  query: string;
  top_k?: number;
  persona_filter?: string;
}

/** Search response */
export interface SearchResponse {
  results: SearchResult[];
  query: string;
  top_k: number;
}

/** Status colors for UI */
export const STATUS_COLORS: Record<DocumentStatus, { bg: string; text: string; icon: string }> = {
  pending: { bg: 'bg-yellow-900/30', text: 'text-yellow-400', icon: 'clock' },
  processing: { bg: 'bg-blue-900/30', text: 'text-blue-400', icon: 'loader' },
  indexed: { bg: 'bg-emerald-900/30', text: 'text-emerald-400', icon: 'check' },
  error: { bg: 'bg-red-900/30', text: 'text-red-400', icon: 'alert' },
};

/** Document type icons */
export const DOC_TYPE_ICONS: Record<DocumentType, string> = {
  pdf: 'file-text',
  docx: 'file-text',
  markdown: 'file-code',
  text: 'file',
  image: 'image',
  unknown: 'file-question',
};

/** Available personas for assignment */
export const AVAILABLE_PERSONAS = [
  { id: 'general_assistant', name: 'General Assistant', icon: 'bot' },
  { id: 'clinical_advisor', name: 'Clinical Advisor', icon: 'stethoscope' },
  { id: 'soap_editor', name: 'SOAP Editor', icon: 'file-text' },
  { id: 'onboarding_guide', name: 'Onboarding Guide', icon: 'hand-wave' },
];
