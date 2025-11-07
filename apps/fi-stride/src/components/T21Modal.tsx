/**
 * T21Modal - Accessible modal with large buttons and clear close
 * AC: Animaciones suaves, contraste alto, audio-guía ready
 */

import React, { useEffect } from 'react';
import { T21Button } from './T21Button';

interface T21ModalProps {
  isOpen: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  confirmText?: string;
  onConfirm?: () => void;
  cancelText?: string;
  icon?: React.ReactNode;
}

export const T21Modal: React.FC<T21ModalProps> = ({
  isOpen,
  title,
  children,
  onClose,
  confirmText = 'Confirmar',
  onConfirm,
  cancelText = 'Cancelar',
  icon,
}) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity duration-300 ease-out"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
                   bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4
                   transition-all duration-300 ease-out
                   border-4 border-gray-900"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          {icon && <span className="text-5xl">{icon}</span>}
          <h2 id="modal-title" className="text-4xl font-bold text-gray-900 uppercase">
            {title}
          </h2>
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-4xl font-bold text-gray-700
                     hover:text-gray-900 focus:outline-2 focus:outline-offset-2 focus:outline-blue-500"
          aria-label="Cerrar"
        >
          ✕
        </button>

        {/* Content */}
        <div className="mb-8 text-2xl text-gray-800 leading-relaxed">{children}</div>

        {/* Actions */}
        <div className="flex gap-4 flex-col">
          {onConfirm && (
            <T21Button
              onClick={onConfirm}
              variant="success"
              size="xl"
              ariaLabel={confirmText}
              icon="✓"
            >
              {confirmText}
            </T21Button>
          )}
          <T21Button
            onClick={onClose}
            variant="info"
            size="xl"
            ariaLabel={cancelText}
            icon="✕"
          >
            {cancelText}
          </T21Button>
        </div>
      </div>
    </>
  );
};
