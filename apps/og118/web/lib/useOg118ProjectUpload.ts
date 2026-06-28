'use client';

/**
 * useOg118ProjectUpload — the consumer-owned upload transport for Projects
 * (PROJECTS-DOCS-E2E). fi-glass ships the PRESENTATION (`ChatFilePreview`) and
 * the `UploadStatus` contract; each app owns its own upload hook (the shell's
 * type comment is explicit: "state from the app's useChatUpload"). This is that
 * hook for og118 — it posts a text file to the project's corpus.
 *
 * Contract (server/app.py POST /projects/{project_id}/upload):
 *   multipart `file`, UTF-8 text only (txt/md). Synchronous ingest — the 200
 *   carries {corpus_id, doc_id, chunks}, so there is NO pending-instructions /
 *   processing / polling step (unlike aurity's knowledge-base flow). The status
 *   path is just `uploading` → `indexed` | `error`.
 *
 * Non-text (PDF/DOCX/binary) is rejected client-side with the same meaning the
 * backend would return (NOT_TEXT), so the user gets the guidance before a wasted
 * round-trip. The corpus is already owner-gated server-side; this only carries
 * the Auth0/bearer header so the upload lands under the caller's account.
 */

import { useCallback, useRef, useState } from 'react';
import type { UploadStatus } from 'fi-glass/shell';
import { authHeaders } from './og118Token';

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';
const MAX_SIZE_MB = 5;
const TEXT_EXTENSIONS = ['txt', 'md', 'markdown'];
const TEXT_MIME = ['text/plain', 'text/markdown', 'text/x-markdown'];

/** Picker filter — only what the backend can ingest (UTF-8 text). */
export const OG118_UPLOAD_ACCEPT = '.txt,.md,.markdown,text/plain,text/markdown';

export interface Og118UploadResult {
  corpusId: string;
  docId: string;
  chunks: number;
}

export interface UseOg118ProjectUpload {
  file: File | null;
  status: UploadStatus;
  progress: number;
  error: string | null;
  result: Og118UploadResult | null;
  /** True while a file is selected/uploading/done — drives the preview visibility. */
  isActive: boolean;
  /** Open the OS picker; the chosen file uploads to `projectId`'s corpus. */
  openFilePicker: (projectId: string) => void;
  /** Programmatic entry (also the test seam) — upload an already-picked file. */
  uploadFile: (projectId: string, file: File) => Promise<void>;
  /** Abort an in-flight upload and clear the preview. */
  cancel: () => void;
}

function isTextFile(file: File): boolean {
  if (TEXT_MIME.includes(file.type)) return true;
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  return TEXT_EXTENSIONS.includes(ext);
}

function describeError(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: unknown }).message);
  }
  return 'No se pudo subir el archivo';
}

export function useOg118ProjectUpload(): UseOg118ProjectUpload {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>('selecting');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Og118UploadResult | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const progressTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopProgress = useCallback(() => {
    if (progressTimer.current) {
      clearInterval(progressTimer.current);
      progressTimer.current = null;
    }
  }, []);

  const uploadFile = useCallback(
    async (projectId: string, picked: File): Promise<void> => {
      if (!isTextFile(picked)) {
        setFile(picked);
        setStatus('error');
        setProgress(0);
        setResult(null);
        setError('Solo archivos de texto (.txt o .md). Para PDF/DOCX, extrae el texto primero.');
        return;
      }
      if (picked.size > MAX_SIZE_MB * 1024 * 1024) {
        setFile(picked);
        setStatus('error');
        setProgress(0);
        setResult(null);
        setError(`El archivo es muy grande. Máximo ${MAX_SIZE_MB} MB.`);
        return;
      }

      setFile(picked);
      setStatus('uploading');
      setProgress(0);
      setError(null);
      setResult(null);

      // fetch has no upload-progress events; simulate up to 90% so the bar moves,
      // then snap to 100 on the real response.
      stopProgress();
      progressTimer.current = setInterval(() => {
        setProgress((p) => (p < 90 ? p + 10 : p));
      }, 120);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const form = new FormData();
        form.append('file', picked, picked.name);
        // No explicit Content-Type — the browser sets the multipart boundary.
        const res = await fetch(`${API}/projects/${encodeURIComponent(projectId)}/upload`, {
          method: 'POST',
          headers: { ...authHeaders() },
          body: form,
          signal: controller.signal,
        });

        stopProgress();

        if (!res.ok) {
          let detail: unknown = null;
          try {
            detail = (await res.json()).detail;
          } catch {
            /* non-JSON body */
          }
          setStatus('error');
          setProgress(0);
          setError(describeError(detail));
          return;
        }

        const body = (await res.json()) as { corpus_id: string; doc_id: string; chunks: number };
        setProgress(100);
        setStatus('indexed');
        setResult({ corpusId: body.corpus_id, docId: body.doc_id, chunks: body.chunks });
      } catch (err) {
        stopProgress();
        if (controller.signal.aborted) return; // cancel() already reset the state
        setStatus('error');
        setProgress(0);
        setError(err instanceof Error ? err.message : 'No se pudo subir el archivo');
      } finally {
        abortRef.current = null;
      }
    },
    [stopProgress],
  );

  const openFilePicker = useCallback(
    (projectId: string) => {
      if (typeof document === 'undefined') return;
      if (!inputRef.current) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = OG118_UPLOAD_ACCEPT;
        input.style.display = 'none';
        document.body.appendChild(input);
        inputRef.current = input;
      }
      const input = inputRef.current;
      input.onchange = () => {
        const picked = input.files?.[0];
        input.value = ''; // allow re-selecting the same file
        if (picked) void uploadFile(projectId, picked);
      };
      input.click();
    },
    [uploadFile],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    stopProgress();
    setFile(null);
    setStatus('selecting');
    setProgress(0);
    setError(null);
    setResult(null);
  }, [stopProgress]);

  return {
    file,
    status,
    progress,
    error,
    result,
    isActive: file !== null,
    openFilePicker,
    uploadFile,
    cancel,
  };
}
