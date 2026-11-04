'use client';

import type { ReactNode } from 'react';
import { AdminSheet, type AdminSheetProps } from '../admin-kit';
import { FI_PERSONA_ROOT_CLASS, usePersonaAdminStyle } from './personaAdminStyle';

export type PersonaSheetProps = Omit<AdminSheetProps, 'className' | 'bodyRef'>;

const row = (node: ReactNode) => <div className="fi-admin-head-row">{node}</div>;

export function PersonaSheet({ header, footer, ...rest }: PersonaSheetProps) {
  usePersonaAdminStyle();
  return (
    <AdminSheet {...rest} className={FI_PERSONA_ROOT_CLASS} header={row(header)} footer={footer ? row(footer) : undefined} />
  );
}
