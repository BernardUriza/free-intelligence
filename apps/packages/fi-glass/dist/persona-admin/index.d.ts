import { z } from 'zod';
import * as react from 'react';
import { ReactNode } from 'react';

interface PersonaExample {
    input: string;
    output: string | Record<string, unknown>;
}
interface PersonaUsageStats {
    total_invocations: number;
    avg_latency_ms: number;
    avg_cost_usd: number;
}
interface Persona {
    id: string;
    name: string;
    description: string;
    system_prompt: string;
    model: string;
    voice?: string | null;
    temperature: number;
    max_tokens: number;
    examples: PersonaExample[];
    usage_stats?: PersonaUsageStats;
    version?: number;
    last_updated?: string;
    updated_by?: string;
}
interface PersonaCreateRequest {
    id: string;
    name: string;
    description: string;
    system_prompt: string;
    model?: string;
    voice?: string | null;
    temperature?: number;
    max_tokens?: number;
    examples?: PersonaExample[];
}
interface PersonaUpdateRequest {
    name?: string;
    description?: string;
    system_prompt?: string;
    model?: string;
    voice?: string | null;
    temperature?: number;
    max_tokens?: number;
    examples?: PersonaExample[];
}
interface PersonaTestResponse {
    output: string | Record<string, unknown>;
    latency_ms: number;
    tokens_used: number;
    cost_usd: number;
}
/**
 * The persistence seam. A consumer wraps its own API client; the components never import one.
 * Rejections should carry a user-facing `Error.message`: it is rendered as-is.
 */
interface PersonaStore {
    list(): Promise<Persona[]>;
    get(personaId: string): Promise<Persona>;
    create(request: PersonaCreateRequest): Promise<Persona>;
    update(personaId: string, request: PersonaUpdateRequest): Promise<Persona>;
    remove(personaId: string): Promise<void>;
    test(personaId: string, input: string): Promise<PersonaTestResponse>;
}
interface PersonaOption {
    value: string;
    label: string;
    /** Rendered as an `<optgroup>` label; options sharing it are grouped. */
    group?: string;
}
type PersonaHideableField = 'voice' | 'temperature' | 'max_tokens' | 'examples';
type PersonaConfirm = (message: string) => Promise<boolean>;
declare const defaultPersonaConfirm: PersonaConfirm;

declare const PERSONA_ID_PATTERN: RegExp;
declare const personaExampleSchema: z.ZodObject<{
    input: z.ZodString;
    output: z.ZodUnion<readonly [z.ZodString, z.ZodRecord<z.ZodString, z.ZodUnknown>]>;
}, z.core.$strip>;
declare const personaCreateSchema: z.ZodObject<{
    name: z.ZodString;
    description: z.ZodString;
    system_prompt: z.ZodString;
    model: z.ZodString;
    voice: z.ZodOptional<z.ZodNullable<z.ZodString>>;
    temperature: z.ZodNumber;
    max_tokens: z.ZodNumber;
    examples: z.ZodDefault<z.ZodOptional<z.ZodArray<z.ZodObject<{
        input: z.ZodString;
        output: z.ZodUnion<readonly [z.ZodString, z.ZodRecord<z.ZodString, z.ZodUnknown>]>;
    }, z.core.$strip>>>>;
    id: z.ZodString;
}, z.core.$strip>;
declare const personaUpdateSchema: z.ZodObject<{
    name: z.ZodOptional<z.ZodString>;
    description: z.ZodOptional<z.ZodString>;
    system_prompt: z.ZodOptional<z.ZodString>;
    model: z.ZodOptional<z.ZodString>;
    voice: z.ZodOptional<z.ZodOptional<z.ZodNullable<z.ZodString>>>;
    temperature: z.ZodOptional<z.ZodNumber>;
    max_tokens: z.ZodOptional<z.ZodNumber>;
    examples: z.ZodOptional<z.ZodDefault<z.ZodOptional<z.ZodArray<z.ZodObject<{
        input: z.ZodString;
        output: z.ZodUnion<readonly [z.ZodString, z.ZodRecord<z.ZodString, z.ZodUnknown>]>;
    }, z.core.$strip>>>>>;
}, z.core.$strip>;
type PersonaCreateFormValues = z.infer<typeof personaCreateSchema>;
type PersonaUpdateFormValues = z.infer<typeof personaUpdateSchema>;
type PersonaFormValues = PersonaCreateFormValues | PersonaUpdateFormValues;
declare const DEFAULT_PERSONA_VALUES: PersonaCreateFormValues;
declare const PERSONA_FIELD_CONSTRAINTS: {
    readonly name: {
        readonly min: 1;
        readonly max: 100;
    };
    readonly description: {
        readonly min: 10;
        readonly max: 500;
    };
    readonly system_prompt: {
        readonly min: 20;
        readonly max: 10000;
    };
    readonly id: {
        readonly min: 1;
        readonly max: 64;
        readonly pattern: RegExp;
    };
    readonly temperature: {
        readonly min: 0;
        readonly max: 1;
        readonly step: 0.05;
    };
    readonly max_tokens: {
        readonly min: 1;
        readonly max: 8192;
        readonly step: 256;
    };
};
interface PersonaValidation<T> {
    success: boolean;
    data?: T;
    errors?: Record<string, string>;
}
declare function validatePersonaCreate(data: unknown): PersonaValidation<PersonaCreateFormValues>;
declare function validatePersonaUpdate(data: unknown): PersonaValidation<PersonaUpdateFormValues>;

declare function mapFormToCreateRequest(form: PersonaCreateFormValues, hiddenFields?: readonly PersonaHideableField[]): PersonaCreateRequest;
declare function mapFormToUpdateRequest(form: PersonaUpdateFormValues, hiddenFields?: readonly PersonaHideableField[]): PersonaUpdateRequest;
declare function mapPersonaToFormValues(persona: Persona): PersonaUpdateFormValues;

interface PersonaFormProps {
    value: PersonaFormValues;
    onChange: (values: PersonaFormValues) => void;
    /** 'create' adds the editable id field; 'edit' shows `personaId` read-only. */
    mode: 'create' | 'edit';
    modelOptions: readonly PersonaOption[];
    voiceOptions?: readonly PersonaOption[];
    hiddenFields?: readonly PersonaHideableField[];
    disabled?: boolean;
    errors?: Record<string, string>;
    personaId?: string;
    showSystemPrompt?: boolean;
    showExamplesSummary?: boolean;
    noVoiceLabel?: string;
}
declare function generateIdFromName(name: string): string;
declare function PersonaForm({ value, onChange, mode, modelOptions, voiceOptions, hiddenFields, disabled, errors, personaId, showSystemPrompt, showExamplesSummary, noVoiceLabel, }: PersonaFormProps): react.JSX.Element;

interface PersonaCreateModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    store: Pick<PersonaStore, 'create'>;
    onCreated: (persona: Persona) => void;
    modelOptions: readonly PersonaOption[];
    voiceOptions?: readonly PersonaOption[];
    hiddenFields?: readonly PersonaHideableField[];
    initialValues?: Partial<PersonaCreateFormValues>;
    /** Consumer-specific fields rendered above the form (e.g. a slot picker). */
    renderExtraFields?: () => ReactNode;
    /** Runs after the form validates and before `store.create`; a string blocks submit and is shown as the error. */
    validateExtra?: () => string | null;
    title?: string;
    subtitle?: string;
    submitLabel?: string;
}
declare function PersonaCreateModal({ open, onOpenChange, store, onCreated, modelOptions, voiceOptions, hiddenFields, initialValues, renderExtraFields, validateExtra, title, subtitle, submitLabel, }: PersonaCreateModalProps): react.JSX.Element | null;

type PersonaEditorTab = 'config' | 'prompt' | 'examples' | 'test';
interface PersonaEditorProps {
    personaId: string;
    open: boolean;
    onClose: () => void;
    onSaved: (persona: Persona) => void;
    store: Pick<PersonaStore, 'get' | 'update' | 'test'> & Partial<Pick<PersonaStore, 'remove'>>;
    modelOptions: readonly PersonaOption[];
    voiceOptions?: readonly PersonaOption[];
    hiddenFields?: readonly PersonaHideableField[];
    /** Shows the delete action when given together with `store.remove`. */
    onDeleted?: (personaId: string) => void;
    confirm?: PersonaConfirm;
    deleteConfirmMessage?: (persona: Persona) => string;
    locale?: string;
}
declare const defaultDeleteConfirmMessage: (persona: Persona) => string;
declare function PersonaEditor({ personaId, open, onClose, onSaved, store, modelOptions, voiceOptions, hiddenFields, onDeleted, confirm, deleteConfirmMessage, locale, }: PersonaEditorProps): react.JSX.Element | null;

type PersonaPatch = (updates: Partial<Persona>) => void;
declare function PersonaPromptTab({ persona, onChange }: {
    persona: Persona;
    onChange: PersonaPatch;
}): react.JSX.Element;
declare function PersonaExamplesTab({ persona, onChange }: {
    persona: Persona;
    onChange: PersonaPatch;
}): react.JSX.Element;
declare function PersonaTestTab({ personaId, store }: {
    personaId: string;
    store: Pick<PersonaStore, 'test'>;
}): react.JSX.Element;

interface PersonaCardProps {
    persona: Persona;
    selected?: boolean;
    onSelect?: () => void;
    onEdit: () => void;
    /** Omit for a persona that must not be deleted. */
    onDelete?: () => void;
    /** Any CSS color; tints the card border and icon. */
    accentColor?: string;
    hiddenFields?: readonly PersonaHideableField[];
    locale?: string;
}
declare function PersonaCard({ persona, selected, onSelect, onEdit, onDelete, accentColor, hiddenFields, locale, }: PersonaCardProps): react.JSX.Element;

interface PersonaSheetProps {
    onDismiss: () => void;
    labelledBy: string;
    /** 'center' is a dialog; 'side' a slide-over. Both become a full sheet on mobile. */
    placement?: 'center' | 'side';
    header: ReactNode;
    footer?: ReactNode;
    children: ReactNode;
}
declare function PersonaSheet({ onDismiss, labelledBy, placement, header, footer, children }: PersonaSheetProps): react.JSX.Element;

interface UsePersonaCollectionOptions {
    confirm?: PersonaConfirm;
    deleteConfirmMessage?: (persona: Persona) => string;
}
interface PersonaCollection {
    personas: Persona[];
    loading: boolean;
    error: string | null;
    reload: () => Promise<void>;
    /** Insert or replace by id (after a create or a save). */
    upsert: (persona: Persona) => void;
    /** Drop by id without calling the store (after the editor already deleted it). */
    forget: (personaId: string) => void;
    /** Confirms, then calls `store.remove`. Resolves true only if the persona was deleted. */
    remove: (persona: Persona) => Promise<boolean>;
    removeError: string | null;
    clearRemoveError: () => void;
}
declare function usePersonaCollection(store: Pick<PersonaStore, 'list' | 'remove'>, { confirm, deleteConfirmMessage }?: UsePersonaCollectionOptions): PersonaCollection;

declare const FI_PERSONA_ROOT_CLASS = "fi-persona-admin";
/** Inject the idempotent persona-admin stylesheet (no-op on the server / if already present). */
declare function ensurePersonaAdminStyle(): void;
declare function usePersonaAdminStyle(): void;

export { DEFAULT_PERSONA_VALUES, FI_PERSONA_ROOT_CLASS, PERSONA_FIELD_CONSTRAINTS, PERSONA_ID_PATTERN, type Persona, PersonaCard, type PersonaCardProps, type PersonaCollection, type PersonaConfirm, type PersonaCreateFormValues, PersonaCreateModal, type PersonaCreateModalProps, type PersonaCreateRequest, PersonaEditor, type PersonaEditorProps, type PersonaEditorTab, type PersonaExample, PersonaExamplesTab, PersonaForm, type PersonaFormProps, type PersonaFormValues, type PersonaHideableField, type PersonaOption, PersonaPromptTab, PersonaSheet, type PersonaSheetProps, type PersonaStore, type PersonaTestResponse, PersonaTestTab, type PersonaUpdateFormValues, type PersonaUpdateRequest, type PersonaUsageStats, type PersonaValidation, type UsePersonaCollectionOptions, defaultDeleteConfirmMessage, defaultPersonaConfirm, ensurePersonaAdminStyle, generateIdFromName, mapFormToCreateRequest, mapFormToUpdateRequest, mapPersonaToFormValues, personaCreateSchema, personaExampleSchema, personaUpdateSchema, usePersonaAdminStyle, usePersonaCollection, validatePersonaCreate, validatePersonaUpdate };
