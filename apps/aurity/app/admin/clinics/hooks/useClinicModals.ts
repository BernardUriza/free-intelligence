/**
 * useClinicModals Hook
 *
 * Single Responsibility: Modal visibility state and transition handlers
 * for the Clinics Admin page.
 * Keeps UI-only modal logic out of the page component.
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useState, useCallback } from 'react';
import type { Doctor, ClinicCreate } from '@/lib/api/clinics';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';

interface UseClinicModalsOptions {
  onUpdateDoctor: (doctor: Doctor, data: DoctorSaveData) => Promise<void>;
  onCreateClinic: (data: ClinicCreate) => Promise<void>;
}

export function useClinicModals({
  onUpdateDoctor,
  onCreateClinic,
}: UseClinicModalsOptions) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [showCreateDoctorModal, setShowCreateDoctorModal] = useState(false);
  const [showEditDoctorModal, setShowEditDoctorModal] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);

  // ── Open / Close ──────────────────────────────────────────────────

  const openCreateClinic = useCallback(() => setShowCreateModal(true), []);
  const closeCreateClinic = useCallback(() => setShowCreateModal(false), []);

  const openLinkToClinic = useCallback(() => setShowLinkModal(true), []);
  const closeLinkToClinic = useCallback(() => setShowLinkModal(false), []);

  const openCreateDoctor = useCallback(() => setShowCreateDoctorModal(true), []);
  const closeCreateDoctor = useCallback(() => setShowCreateDoctorModal(false), []);

  const openEditDoctor = useCallback((doctor: Doctor) => {
    setEditingDoctor(doctor);
    setShowEditDoctorModal(true);
  }, []);

  const closeEditDoctor = useCallback(() => {
    setShowEditDoctorModal(false);
    setEditingDoctor(null);
  }, []);

  // ── Compound handlers (action + close) ────────────────────────────

  const handleSaveDoctor = useCallback(async (data: DoctorSaveData) => {
    if (!editingDoctor) return;
    await onUpdateDoctor(editingDoctor, data);
    closeEditDoctor();
  }, [editingDoctor, onUpdateDoctor, closeEditDoctor]);

  const handleCreateClinicAndClose = useCallback(async (data: ClinicCreate) => {
    await onCreateClinic(data);
    closeCreateClinic();
  }, [onCreateClinic, closeCreateClinic]);

  return {
    // Visibility flags
    showCreateModal,
    showLinkModal,
    showCreateDoctorModal,
    showEditDoctorModal,
    editingDoctor,

    // Open/Close
    openCreateClinic,
    closeCreateClinic,
    openLinkToClinic,
    closeLinkToClinic,
    openCreateDoctor,
    closeCreateDoctor,
    openEditDoctor,
    closeEditDoctor,

    // Compound handlers
    handleSaveDoctor,
    handleCreateClinicAndClose,
  } as const;
}
