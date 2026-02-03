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
import { getBackendUrl } from '@/lib/config/deployment';

const BACKEND_URL = getBackendUrl();

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
  const url = `${BACKEND_URL}/api/aurity/knowledge-base/documents${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch a single document by ID
 *
 * @param docId - Document UUID
 * @param includeText - Whether to include extracted text content
 */
export async function fetchDocument(docId: string, includeText = false): Promise<Document> {
  const url = `${BACKEND_URL}/api/aurity/knowledge-base/documents/${docId}${includeText ? '?include_text=true' : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch document ${docId}: ${response.statusText}`);
  }

  return response.json();
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

  const response = await fetch(`${BACKEND_URL}/api/aurity/knowledge-base/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Upload failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update document metadata
 */
export async function updateDocument(
  docId: string,
  updates: DocumentUpdateRequest
): Promise<DocumentMetadata> {
  const response = await fetch(`${BACKEND_URL}/api/aurity/knowledge-base/documents/${docId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error(`Failed to update document ${docId}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a document
 */
export async function deleteDocument(docId: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/aurity/knowledge-base/documents/${docId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete document ${docId}: ${response.statusText}`);
  }
}

/**
 * Reindex a document (regenerate embeddings)
 */
export async function reindexDocument(docId: string): Promise<DocumentMetadata> {
  const response = await fetch(`${BACKEND_URL}/api/aurity/knowledge-base/documents/${docId}/reindex`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to reindex document ${docId}: ${response.statusText}`);
  }

  return response.json();
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
  const response = await fetch(`${BACKEND_URL}/api/aurity/knowledge-base/documents/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      top_k: options?.top_k ?? 5,
      persona_filter: options?.persona_filter,
    }),
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get questions for a document
 *
 * Returns accumulated questions from:
 * - LLM initial generation (source="llm_initial") - created during indexing
 * - User queries via RAG (source="user_query") - accumulated during usage
 */
export async function getDocumentQuestions(docId: string): Promise<DocumentQuestion[]> {
  const response = await fetch(
    `${BACKEND_URL}/api/aurity/knowledge-base/documents/${docId}/questions`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch questions for document ${docId}: ${response.statusText}`);
  }

  return response.json();
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
