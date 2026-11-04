'use client';

import { AdminSheet, type AdminSheetProps } from '../admin-kit';
import { FI_MODEL_CATALOG_ROOT_CLASS, useModelCatalogStyle } from './modelCatalogStyle';

export type ModelSheetProps = Omit<AdminSheetProps, 'className'>;

export function ModelSheet(props: ModelSheetProps) {
  useModelCatalogStyle();
  return <AdminSheet {...props} className={FI_MODEL_CATALOG_ROOT_CLASS} />;
}
