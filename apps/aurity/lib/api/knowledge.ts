/**
 * Knowledge Base API Client
 *
 * Functions for managing documents in the Knowledge Base.
 * Card: FI-UI-FEAT-021
 */

import type {
  DocumentMetadata,
  Document,
  DocumentsListResponse,
  DocumentUpdateRequest,
  SearchResponse,
  DocumentStatus,
  DocumentQuestion,
} from '@aurity-standalone/types/knowledge';
import { api } from './client';

const API_BASE = '/api/aurity/knowledge-base/documents';

/**
 * Fetch all documents with optional filters
 */
export async function fetchDocuments(params?: {
  status?: DocumentStatus;
  persona?: string;
}): Promise<DocumentsListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.persona) query.set('persona', params.persona);

  const queryString = query.toString();
  return api.get<DocumentsListResponse>(`${API_BASE}${queryString ? `?${queryString}` : ''}`);
}

/**
 * Fetch a single document by ID
 *
 * @param docId - Document UUID
 * @param includeText - Whether to include extracted text content
 */
export async function fetchDocument(docId: string, includeText = false): Promise<Document> {
  return api.get<Document>(`${API_BASE}/${docId}${includeText ? '?include_text=true' : ''}`);
}

/**
 * Upload a new document
 */
export async function uploadDocument(
  file: File,
  metadata: {
    title?: string;
    usage_instructions?: string;
    assigned_personas?: string[];
  }
): Promise<DocumentMetadata> {
  const formData = new FormData();
  formData.append('file', file);
  if (metadata.title) formData.append('title', metadata.title);
  if (metadata.usage_instructions) formData.append('usage_instructions', metadata.usage_instructions);
  if (metadata.assigned_personas) {
    formData.append('assigned_personas', JSON.stringify(metadata.assigned_personas));
  }

  return api.upload<DocumentMetadata>(`${API_BASE}/upload`, formData);
}

/**
 * Update document metadata
 */
export async function updateDocument(
  docId: string,
  updates: DocumentUpdateRequest
): Promise<DocumentMetadata> {
  return api.put<DocumentMetadata>(`${API_BASE}/${docId}`, updates);
}

/**
 * Delete a document
 */
export async function deleteDocument(docId: string): Promise<void> {
  await api.delete<void>(`${API_BASE}/${docId}`);
}

/**
 * Reindex a document (regenerate embeddings)
 */
export async function reindexDocument(docId: string): Promise<DocumentMetadata> {
  return api.post<DocumentMetadata>(`${API_BASE}/${docId}/reindex`);
}

/**
 * Semantic search across documents
 */
export async function searchDocuments(
  query: string,
  options?: {
    top_k?: number;
    persona_filter?: string;
  }
): Promise<SearchResponse> {
  return api.post<SearchResponse>(`${API_BASE}/search`, {
    query,
    top_k: options?.top_k ?? 5,
    persona_filter: options?.persona_filter,
  });
}

/**
 * Get questions for a document
 *
 * Returns accumulated questions from:
 * - LLM initial generation (source="llm_initial") - created during indexing
 * - User queries via RAG (source="user_query") - accumulated during usage
 */
export async function getDocumentQuestions(docId: string): Promise<DocumentQuestion[]> {
  return api.get<DocumentQuestion[]>(`${API_BASE}/${docId}/questions`);
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Format date for display
 */
export function formatDate(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    return date.toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'Fecha inválida';
  }
}
