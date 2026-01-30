import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';

type ServiceStatus = 'checking' | 'running' | 'stopped';

interface UseRAGServiceReturn {
  status: ServiceStatus;
  isStarting: boolean;
  selectedPDF: string | null;
  isPdfProcessing: boolean;
  checkStatus: () => Promise<void>;
  startService: () => Promise<void>;
  stopService: () => Promise<void>;
  handlePDFSelect: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
  loadSamplePDF: (filename: string) => Promise<void>;
}

/**
 * Custom hook for managing RAG service lifecycle
 *
 * Handles:
 * - Service status polling
 * - Starting/stopping the RAG service
 * - PDF file upload and processing
 * - Sample PDF loading
 */
export function useRAGService(): UseRAGServiceReturn {
  const [status, setStatus] = useState<ServiceStatus>('checking');
  const [isStarting, setIsStarting] = useState(false);
  const [selectedPDF, setSelectedPDF] = useState<string | null>(null);
  const [isPdfProcessing, setIsPdfProcessing] = useState(false);

  /**
   * Check RAG service status via backend
   */
  const checkStatus = useCallback(async () => {
    try {
      const response = await invoke<{ running: boolean }>('check_rag_service_status');
      setStatus(response.running ? 'running' : 'stopped');
    } catch (error) {
      console.error('Failed to check RAG service status:', error);
      setStatus('stopped');
    }
  }, []);

  /**
   * Start the RAG service
   */
  const startService = useCallback(async () => {
    setIsStarting(true);
    try {
      await invoke('start_rag_service');
      // Poll for status until service is running
      let attempts = 0;
      const maxAttempts = 10;
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await checkStatus();
        const response = await invoke<{ running: boolean }>('check_rag_service_status');
        if (response.running) {
          setStatus('running');
          break;
        }
        attempts++;
      }
    } catch (error) {
      console.error('Failed to start RAG service:', error);
      alert(`Failed to start RAG service: ${error}`);
    } finally {
      setIsStarting(false);
    }
  }, [checkStatus]);

  /**
   * Stop the RAG service
   */
  const stopService = useCallback(async () => {
    try {
      await invoke('stop_rag_service');
      setStatus('stopped');
    } catch (error) {
      console.error('Failed to stop RAG service:', error);
      alert(`Failed to stop RAG service: ${error}`);
    }
  }, []);

  /**
   * Handle custom PDF file selection and upload
   */
  const handlePDFSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsPdfProcessing(true);
    try {
      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      await invoke('upload_pdf_to_rag', {
        filename: file.name,
        content: Array.from(uint8Array),
      });
      setSelectedPDF(file.name);
      alert(`Successfully uploaded ${file.name}`);
    } catch (error) {
      console.error('Failed to upload PDF:', error);
      alert(`Failed to upload PDF: ${error}`);
    } finally {
      setIsPdfProcessing(false);
    }
  }, []);

  /**
   * Load a pre-loaded sample PDF from backend
   */
  const loadSamplePDF = useCallback(async (filename: string) => {
    setIsPdfProcessing(true);
    try {
      await invoke('load_sample_pdf', { filename });
      setSelectedPDF(filename);
      alert(`Successfully loaded ${filename}`);
    } catch (error) {
      console.error('Failed to load sample PDF:', error);
      alert(`Failed to load sample PDF: ${error}`);
    } finally {
      setIsPdfProcessing(false);
    }
  }, []);

  // Initial status check on mount
  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  return {
    status,
    isStarting,
    selectedPDF,
    isPdfProcessing,
    checkStatus,
    startService,
    stopService,
    handlePDFSelect,
    loadSamplePDF,
  };
}
