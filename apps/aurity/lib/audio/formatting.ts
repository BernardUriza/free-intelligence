/**
 * Audio Formatting Utilities
 *
 * Funciones reutilizables para formatear tiempos y tamaños de archivo.
 * Extraído de ConversationCapture durante refactoring incremental.
 */

/**
 * Formatea segundos a formato MM:SS
 * @example formatTime(125) // "2:05"
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Formatea bytes a formato legible (MB)
 * @example formatFileSize(2500000) // "2.38 MB"
 */
export function formatFileSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
