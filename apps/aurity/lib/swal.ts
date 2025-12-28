/**
 * SweetAlert2 Utility Wrapper
 *
 * Provides pre-configured modals for common use cases with dark theme styling.
 * Uses the app's slate color palette for consistency.
 */

import Swal, { type SweetAlertResult } from 'sweetalert2';

// =============================================================================
// THEME CONFIGURATION
// =============================================================================

const darkTheme = {
  background: '#1e293b', // slate-800
  color: '#f1f5f9', // slate-100
  confirmButtonColor: '#3b82f6', // blue-500
  cancelButtonColor: '#64748b', // slate-500
  denyButtonColor: '#ef4444', // red-500
};

// =============================================================================
// PRE-CONFIGURED INSTANCES
// =============================================================================

/**
 * Base Swal instance with dark theme
 */
export const swal = Swal.mixin({
  ...darkTheme,
  customClass: {
    popup: 'rounded-xl border border-slate-700',
    title: 'text-slate-100',
    htmlContainer: 'text-slate-300',
    confirmButton: 'rounded-lg px-4 py-2 font-medium',
    cancelButton: 'rounded-lg px-4 py-2 font-medium',
    denyButton: 'rounded-lg px-4 py-2 font-medium',
  },
});

// =============================================================================
// CONFIRMATION DIALOGS
// =============================================================================

interface ConfirmOptions {
  title: string;
  text?: string;
  confirmText?: string;
  cancelText?: string;
  icon?: 'warning' | 'error' | 'success' | 'info' | 'question';
}

/**
 * Show a confirmation dialog (replaces window.confirm)
 * @returns Promise<boolean> - true if confirmed, false if cancelled
 */
export async function confirmDialog({
  title,
  text,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  icon = 'warning',
}: ConfirmOptions): Promise<boolean> {
  const result = await swal.fire({
    title,
    text,
    icon,
    showCancelButton: true,
    confirmButtonText: confirmText,
    cancelButtonText: cancelText,
    reverseButtons: true,
  });

  return result.isConfirmed;
}

/**
 * Show a delete confirmation dialog
 */
export async function confirmDelete(itemName?: string): Promise<boolean> {
  return confirmDialog({
    title: '¿Estás seguro?',
    text: itemName
      ? `Se eliminará "${itemName}". Esta acción no se puede deshacer.`
      : 'Esta acción no se puede deshacer.',
    confirmText: 'Eliminar',
    cancelText: 'Cancelar',
    icon: 'warning',
  });
}

/**
 * Show a dangerous action confirmation (red button)
 */
export async function confirmDanger({
  title,
  text,
  confirmText = 'Confirmar',
}: Omit<ConfirmOptions, 'icon'>): Promise<boolean> {
  const result = await swal.fire({
    title,
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: confirmText,
    confirmButtonColor: '#ef4444', // red-500
    cancelButtonText: 'Cancelar',
    reverseButtons: true,
  });

  return result.isConfirmed;
}

// =============================================================================
// ALERT DIALOGS
// =============================================================================

interface AlertOptions {
  title: string;
  text?: string;
  icon?: 'success' | 'error' | 'warning' | 'info';
}

/**
 * Show a simple alert dialog (replaces window.alert)
 */
export async function showAlert({
  title,
  text,
  icon = 'info',
}: AlertOptions): Promise<void> {
  await swal.fire({
    title,
    text,
    icon,
    confirmButtonText: 'Aceptar',
  });
}

/**
 * Show a success message
 */
export async function showSuccess(title: string, text?: string): Promise<void> {
  await swal.fire({
    title,
    text,
    icon: 'success',
    confirmButtonText: 'Aceptar',
    timer: 3000,
    timerProgressBar: true,
  });
}

/**
 * Show an error message
 */
export async function showError(title: string, text?: string): Promise<void> {
  await swal.fire({
    title,
    text,
    icon: 'error',
    confirmButtonText: 'Aceptar',
  });
}

/**
 * Show a warning message
 */
export async function showWarning(title: string, text?: string): Promise<void> {
  await swal.fire({
    title,
    text,
    icon: 'warning',
    confirmButtonText: 'Aceptar',
  });
}

/**
 * Show an info message
 */
export async function showInfo(title: string, text?: string): Promise<void> {
  await swal.fire({
    title,
    text,
    icon: 'info',
    confirmButtonText: 'Aceptar',
  });
}

// =============================================================================
// TOAST NOTIFICATIONS
// =============================================================================

const Toast = Swal.mixin({
  toast: true,
  position: 'top-end',
  showConfirmButton: false,
  timer: 3000,
  timerProgressBar: true,
  ...darkTheme,
  didOpen: (toast) => {
    toast.onmouseenter = Swal.stopTimer;
    toast.onmouseleave = Swal.resumeTimer;
  },
});

/**
 * Show a toast notification
 */
export function toast(
  message: string,
  icon: 'success' | 'error' | 'warning' | 'info' = 'info'
): void {
  Toast.fire({
    icon,
    title: message,
  });
}

export const toastSuccess = (message: string) => toast(message, 'success');
export const toastError = (message: string) => toast(message, 'error');
export const toastWarning = (message: string) => toast(message, 'warning');
export const toastInfo = (message: string) => toast(message, 'info');

// =============================================================================
// INPUT DIALOGS
// =============================================================================

interface InputOptions {
  title: string;
  text?: string;
  inputPlaceholder?: string;
  inputValue?: string;
  confirmText?: string;
}

/**
 * Show an input dialog
 * @returns The input value or null if cancelled
 */
export async function promptInput({
  title,
  text,
  inputPlaceholder = '',
  inputValue = '',
  confirmText = 'Aceptar',
}: InputOptions): Promise<string | null> {
  const result = await swal.fire({
    title,
    text,
    input: 'text',
    inputPlaceholder,
    inputValue,
    showCancelButton: true,
    confirmButtonText: confirmText,
    cancelButtonText: 'Cancelar',
    inputAttributes: {
      class: 'swal2-input bg-slate-700 border-slate-600 text-slate-100',
    },
  });

  return result.isConfirmed ? (result.value as string) : null;
}

// =============================================================================
// LOADING STATE
// =============================================================================

/**
 * Show a loading indicator
 */
export function showLoading(title = 'Cargando...'): void {
  swal.fire({
    title,
    allowOutsideClick: false,
    allowEscapeKey: false,
    didOpen: () => {
      Swal.showLoading();
    },
  });
}

/**
 * Update the loading message (while loading is shown)
 */
export function updateLoadingMessage(title: string, text?: string): void {
  Swal.update({
    title,
    text,
  });
}

/**
 * Progressive loading stages configuration
 */
export interface ProgressiveLoadingStage {
  title: string;
  text?: string;
  delay: number; // ms before showing this stage
}

/**
 * Show progressive loading with stage updates over time.
 * Useful for long-running operations where you want to keep the user informed.
 *
 * @param stages - Array of stages to show progressively
 * @returns A controller object to stop the progression or update manually
 */
export function showProgressiveLoading(stages: ProgressiveLoadingStage[]): {
  stop: () => void;
  updateStage: (title: string, text?: string) => void;
} {
  const timeoutIds: ReturnType<typeof setTimeout>[] = [];

  // Show initial loading
  if (stages.length > 0) {
    swal.fire({
      title: stages[0].title,
      text: stages[0].text,
      allowOutsideClick: false,
      allowEscapeKey: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });
  }

  // Schedule stage transitions
  for (let i = 1; i < stages.length; i++) {
    const stage = stages[i];
    const timeoutId = setTimeout(() => {
      Swal.update({
        title: stage.title,
        text: stage.text,
      });
    }, stage.delay);
    timeoutIds.push(timeoutId);
  }

  return {
    stop: () => {
      timeoutIds.forEach((id) => clearTimeout(id));
    },
    updateStage: (title: string, text?: string) => {
      Swal.update({ title, text });
    },
  };
}

/**
 * Close any open Swal dialog
 */
export function closeDialog(): void {
  Swal.close();
}

// Re-export Swal for advanced use cases
export { Swal };
export type { SweetAlertResult };
