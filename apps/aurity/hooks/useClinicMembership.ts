/**
 * useClinicMembership Hook
 *
 * Single Responsibility: Clinic membership state and link-to-clinic flow.
 * Extracted from useClinicsAdmin for SRP compliance.
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useState, useCallback } from 'react';
import type { Clinic, ClinicMembership, ClinicRole } from '@/lib/api/clinics';
import { getClinicMembership, linkToClinic } from '@/lib/api/clinics';
import { toastError } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ClinicMembership');

interface LinkForm {
  nombre: string;
  apellido: string;
  especialidad: string;
  role: ClinicRole;
}

interface UserContext {
  sub: string;
  email?: string | null;
}

export function useClinicMembership() {
  const [membership, setMembership] = useState<ClinicMembership | null>(null);
  const [linkingToClinic, setLinkingToClinic] = useState(false);

  const loadMembership = useCallback(async (user: UserContext) => {
    try {
      const data = await getClinicMembership(user.sub, user.email ?? undefined);
      setMembership(data);
    } catch (err) {
      log.error('Failed to load membership', { error: String(err) });
    }
  }, []);

  const handleLinkToClinic = useCallback(async (
    user: UserContext,
    selectedClinic: Clinic,
    form: LinkForm,
    onSuccess: () => void,
  ) => {
    setLinkingToClinic(true);
    try {
      const result = await linkToClinic(
        user.sub,
        {
          clinic_id: selectedClinic.clinic_id,
          role: form.role,
          nombre: form.nombre,
          apellido: form.apellido,
          especialidad: form.especialidad || undefined,
        },
        user.email ?? undefined,
      );

      if (result.success && result.membership) {
        setMembership(result.membership);
        onSuccess();
        return true;
      }
      return false;
    } catch (err) {
      log.error('Failed to link to clinic', { error: String(err) });
      toastError(err instanceof Error ? err.message : 'Error al vincularse a la clínica');
      return false;
    } finally {
      setLinkingToClinic(false);
    }
  }, []);

  return {
    membership,
    linkingToClinic,
    loadMembership,
    handleLinkToClinic,
  } as const;
}
