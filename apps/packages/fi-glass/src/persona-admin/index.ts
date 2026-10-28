// fi-glass · persona-admin: list, create, edit, test and delete personas through a PersonaStore.
// Also importable via `fi-glass/persona-admin`; extracted from aurity's admin panel.
export type {
  Persona,
  PersonaExample,
  PersonaUsageStats,
  PersonaCreateRequest,
  PersonaUpdateRequest,
  PersonaTestResponse,
  PersonaStore,
  PersonaOption,
  PersonaHideableField,
  PersonaConfirm,
} from './types';
export { defaultPersonaConfirm } from './types';

export {
  PERSONA_ID_PATTERN,
  PERSONA_FIELD_CONSTRAINTS,
  DEFAULT_PERSONA_VALUES,
  personaExampleSchema,
  personaCreateSchema,
  personaUpdateSchema,
  validatePersonaCreate,
  validatePersonaUpdate,
  type PersonaCreateFormValues,
  type PersonaUpdateFormValues,
  type PersonaFormValues,
  type PersonaValidation,
} from './schema';

export { mapFormToCreateRequest, mapFormToUpdateRequest, mapPersonaToFormValues } from './mappers';

export { PersonaForm, generateIdFromName, type PersonaFormProps } from './PersonaForm';
export { PersonaCreateModal, type PersonaCreateModalProps } from './PersonaCreateModal';
export {
  PersonaEditor,
  defaultDeleteConfirmMessage,
  type PersonaEditorProps,
  type PersonaEditorTab,
} from './PersonaEditor';
export { PersonaPromptTab, PersonaExamplesTab, PersonaTestTab } from './PersonaEditorTabs';
export { PersonaCard, type PersonaCardProps } from './PersonaCard';
export { PersonaSheet, type PersonaSheetProps } from './PersonaSheet';
export {
  usePersonaCollection,
  type PersonaCollection,
  type UsePersonaCollectionOptions,
} from './usePersonaCollection';
export { FI_PERSONA_ROOT_CLASS, ensurePersonaAdminStyle, usePersonaAdminStyle } from './personaAdminStyle';
