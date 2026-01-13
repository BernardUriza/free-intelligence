/*
  Backwards-compatible wrapper: prefer using `confirmDelete` from '@/lib/swal'.
  This file kept to avoid breaking imports that expected ConfirmDialog component.
*/
import React from 'react';
import { confirmDelete } from '@/lib/swal';

export function ConfirmDialog({
  children,
  onConfirm,
}: {
  children: React.ReactNode;
  onConfirm?: () => void;
}) {
  return (
    <div onClick={async () => {
      const ok = await confirmDelete();
      if (ok) onConfirm?.();
    }}>{children}</div>
  );
}

export default ConfirmDialog;
