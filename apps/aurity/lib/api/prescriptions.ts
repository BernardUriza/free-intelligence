/**
 * Prescriptions API Client
 *
 * Types and API functions for the prescription template engine.
 * Connects to: /api/aurity/prescriptions/*
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @card FI-RX-002
 */

import { getBackendUrl } from "./client";

// ============================================================================
// Enums
// ============================================================================

/**
 * Medication administration routes (vías de administración)
 */
export type MedicationRoute =
  | "oral"
  | "sublingual"
  | "intravenous"
  | "intramuscular"
  | "subcutaneous"
  | "topical"
  | "ophthalmic"
  | "otic"
  | "nasal"
  | "inhalation"
  | "rectal"
  | "vaginal"
  | "transdermal";

/**
 * Common medication frequencies
 */
export type MedicationFrequency =
  | "once_daily"
  | "twice_daily"
  | "three_times_daily"
  | "four_times_daily"
  | "every_4_hours"
  | "every_6_hours"
  | "every_8_hours"
  | "every_12_hours"
  | "every_24_hours"
  | "weekly"
  | "as_needed"
  | "before_meals"
  | "after_meals"
  | "at_bedtime"
  | "custom";

/**
 * Prescription lifecycle status
 */
export type PrescriptionStatus =
  | "draft"
  | "pending_signature"
  | "signed"
  | "dispensed"
  | "cancelled"
  | "expired";

/**
 * Template field types
 */
export type FieldType =
  | "text"
  | "number"
  | "date"
  | "select"
  | "multiselect"
  | "textarea"
  | "medication"
  | "signature";

// ============================================================================
// Label Helpers
// ============================================================================

export const ROUTE_LABELS: Record<MedicationRoute, string> = {
  oral: "Vía oral",
  sublingual: "Sublingual",
  intravenous: "Intravenosa (IV)",
  intramuscular: "Intramuscular (IM)",
  subcutaneous: "Subcutánea (SC)",
  topical: "Tópica",
  ophthalmic: "Oftálmica",
  otic: "Ótica",
  nasal: "Nasal",
  inhalation: "Inhalada",
  rectal: "Rectal",
  vaginal: "Vaginal",
  transdermal: "Transdérmica",
};

export const FREQUENCY_LABELS: Record<MedicationFrequency, string> = {
  once_daily: "Una vez al día",
  twice_daily: "Cada 12 horas",
  three_times_daily: "Cada 8 horas",
  four_times_daily: "Cada 6 horas",
  every_4_hours: "Cada 4 horas",
  every_6_hours: "Cada 6 horas",
  every_8_hours: "Cada 8 horas",
  every_12_hours: "Cada 12 horas",
  every_24_hours: "Cada 24 horas",
  weekly: "Una vez por semana",
  as_needed: "Según se necesite (PRN)",
  before_meals: "Antes de los alimentos",
  after_meals: "Después de los alimentos",
  at_bedtime: "Al acostarse",
  custom: "Personalizada",
};

export const STATUS_LABELS: Record<PrescriptionStatus, string> = {
  draft: "Borrador",
  pending_signature: "Pendiente de firma",
  signed: "Firmada",
  dispensed: "Surtida",
  cancelled: "Cancelada",
  expired: "Expirada",
};

// ============================================================================
// Medication Types
// ============================================================================

/**
 * Individual medication in a prescription
 */
export interface Medication {
  name: string;
  active_ingredient?: string;
  dosage: string;
  dosage_form: string;
  frequency: MedicationFrequency;
  frequency_custom?: string;
  duration_days?: number;
  duration_text?: string;
  route: MedicationRoute;
  quantity?: string;
  instructions?: string;
  indication?: string;
  warnings?: string;
}

/**
 * Default medication values
 */
export const DEFAULT_MEDICATION: Partial<Medication> = {
  dosage_form: "tableta",
  frequency: "every_8_hours",
  route: "oral",
  duration_days: 7,
};

// ============================================================================
// Template Types
// ============================================================================

/**
 * Customizable field in a prescription template
 */
export interface TemplateField {
  key: string;
  label: string;
  field_type: FieldType;
  required: boolean;
  default_value?: unknown;
  placeholder?: string;
  options?: string[];
  min_length?: number;
  max_length?: number;
  order: number;
  visible: boolean;
  help_text?: string;
}

/**
 * Header configuration (membrete)
 */
export interface HeaderConfig {
  institution_name?: string;
  institution_address?: string;
  institution_phone?: string;
  institution_logo_url?: string;
  physician_name?: string;
  physician_specialty?: string;
  physician_license?: string;
  physician_university?: string;
  physician_specialty_license?: string;
}

/**
 * Footer configuration
 */
export interface FooterConfig {
  include_signature_line: boolean;
  signature_label: string;
  include_date_line: boolean;
  disclaimer_text?: string;
  include_qr_code: boolean;
}

/**
 * Prescription template configuration
 */
export interface PrescriptionTemplate {
  id: string;
  name: string;
  description?: string;
  owner_id?: string;
  owner_type: "physician" | "institution" | "system";
  is_default: boolean;
  header: HeaderConfig;
  footer: FooterConfig;
  fields: TemplateField[];
  medication_fields: string[];
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

// ============================================================================
// Prescription Types
// ============================================================================

/**
 * Patient information for prescription
 */
export interface PatientInfo {
  name: string;
  age?: string;
  date_of_birth?: string;
  gender?: string;
  weight_kg?: number;
  allergies: string[];
  patient_id?: string;
}

/**
 * Physician information for prescription
 */
export interface PhysicianInfo {
  name: string;
  professional_license: string;
  specialty?: string;
  specialty_license?: string;
  institution?: string;
  address?: string;
  phone?: string;
  email?: string;
  physician_id?: string;
}

/**
 * Complete prescription
 */
export interface Prescription {
  id: string;
  template_id: string;
  session_id?: string;
  status: PrescriptionStatus;
  patient: PatientInfo;
  physician: PhysicianInfo;
  diagnosis: string;
  diagnosis_code?: string;
  secondary_diagnoses: string[];
  medications: Medication[];
  general_instructions?: string;
  next_appointment?: string;
  validity_days: number;
  created_at: string;
  signed_at?: string;
  dispensed_at?: string;
  expires_at?: string;
  signature_hash?: string;
  notes?: string;
  custom_fields: Record<string, unknown>;
  // Computed fields
  medication_count: number;
  is_signed: boolean;
  is_valid: boolean;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface CreatePrescriptionRequest {
  template_id?: string;
  session_id?: string;
  patient: PatientInfo;
  physician: PhysicianInfo;
  diagnosis: string;
  diagnosis_code?: string;
  medications: Medication[];
  general_instructions?: string;
  next_appointment?: string;
}

export interface UpdatePrescriptionRequest {
  diagnosis?: string;
  diagnosis_code?: string;
  medications?: Medication[];
  general_instructions?: string;
  next_appointment?: string;
  patient?: Partial<PatientInfo>;
}

export interface CreateFromSOAPRequest {
  session_id: string;
  template_id?: string;
  patient: PatientInfo;
  physician: PhysicianInfo;
}

export interface CancelPrescriptionRequest {
  reason?: string;
}

export interface PrescriptionResponse {
  success: boolean;
  prescription?: Prescription;
  message?: string;
}

export interface TemplateListResponse {
  templates: PrescriptionTemplate[];
  count: number;
}

export interface PrescriptionListResponse {
  prescriptions: Prescription[];
  count: number;
}

export interface ExportResponse {
  format: "text" | "json";
  content: string | Prescription;
  prescription_id: string;
}

// ============================================================================
// API Client Functions
// ============================================================================

const API_BASE = () => `${getBackendUrl()}/api/aurity/prescriptions`;

/**
 * List available prescription templates
 */
export async function listTemplates(
  ownerId?: string,
  includeSystem = true
): Promise<TemplateListResponse> {
  const params = new URLSearchParams();
  if (ownerId) params.set("owner_id", ownerId);
  params.set("include_system", String(includeSystem));

  const response = await fetch(`${API_BASE()}/templates?${params}`);
  if (!response.ok) {
    throw new Error(`Failed to list templates: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get a specific template by ID
 */
export async function getTemplate(
  templateId: string
): Promise<PrescriptionTemplate> {
  const response = await fetch(`${API_BASE()}/templates/${templateId}`);
  if (!response.ok) {
    throw new Error(`Failed to get template: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create a new prescription
 */
export async function createPrescription(
  data: CreatePrescriptionRequest
): Promise<PrescriptionResponse> {
  const response = await fetch(API_BASE(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to create prescription: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create prescription from SOAP note
 */
export async function createPrescriptionFromSOAP(
  data: CreateFromSOAPRequest
): Promise<PrescriptionResponse> {
  const response = await fetch(`${API_BASE()}/from-soap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to create prescription from SOAP: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get a prescription by ID
 */
export async function getPrescription(
  prescriptionId: string
): Promise<PrescriptionResponse> {
  const response = await fetch(`${API_BASE()}/${prescriptionId}`);
  if (!response.ok) {
    throw new Error(`Failed to get prescription: ${response.statusText}`);
  }
  return response.json();
}

/**
 * List prescriptions with optional filters
 */
export async function listPrescriptions(options?: {
  sessionId?: string;
  patientId?: string;
  physicianId?: string;
  status?: PrescriptionStatus;
  limit?: number;
}): Promise<PrescriptionListResponse> {
  const params = new URLSearchParams();
  if (options?.sessionId) params.set("session_id", options.sessionId);
  if (options?.patientId) params.set("patient_id", options.patientId);
  if (options?.physicianId) params.set("physician_id", options.physicianId);
  if (options?.status) params.set("status", options.status);
  if (options?.limit) params.set("limit", String(options.limit));

  const response = await fetch(`${API_BASE()}?${params}`);
  if (!response.ok) {
    throw new Error(`Failed to list prescriptions: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update a draft prescription
 */
export async function updatePrescription(
  prescriptionId: string,
  data: UpdatePrescriptionRequest
): Promise<PrescriptionResponse> {
  const response = await fetch(`${API_BASE()}/${prescriptionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to update prescription: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Sign a prescription
 */
export async function signPrescription(
  prescriptionId: string
): Promise<PrescriptionResponse> {
  const response = await fetch(`${API_BASE()}/${prescriptionId}/sign`, {
    method: "POST",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to sign prescription: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Cancel a prescription
 */
export async function cancelPrescription(
  prescriptionId: string,
  reason?: string
): Promise<PrescriptionResponse> {
  const response = await fetch(`${API_BASE()}/${prescriptionId}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to cancel prescription: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Export prescription to text or JSON
 */
export async function exportPrescription(
  prescriptionId: string,
  format: "text" | "json" = "text"
): Promise<ExportResponse> {
  const response = await fetch(
    `${API_BASE()}/${prescriptionId}/export?format=${format}`
  );
  if (!response.ok) {
    throw new Error(`Failed to export prescription: ${response.statusText}`);
  }
  return response.json();
}

// ============================================================================
// Medication Catalog Types (FI-RX-004)
// ============================================================================

/**
 * Therapeutic categories for medications
 */
export type DrugCategory =
  | "analgesic"
  | "antibiotic"
  | "antiviral"
  | "antifungal"
  | "antiinflammatory"
  | "antihypertensive"
  | "antidiabetic"
  | "antihistamine"
  | "antacid"
  | "bronchodilator"
  | "corticosteroid"
  | "antidepressant"
  | "anxiolytic"
  | "antipsychotic"
  | "anticoagulant"
  | "anticonvulsant"
  | "diuretic"
  | "vitamin"
  | "hormone"
  | "muscle_relaxant"
  | "gastrointestinal"
  | "dermatologic"
  | "ophthalmic"
  | "otic"
  | "other";

/**
 * Controlled substance levels (Mexican law)
 */
export type ControlledSubstanceLevel =
  | "none"
  | "fraction_i"
  | "fraction_ii"
  | "fraction_iii"
  | "fraction_iv"
  | "fraction_v"
  | "fraction_vi";

/**
 * Medication presentation/formulation
 */
export interface CatalogPresentation {
  form: string;
  strength: string;
  unit: string;
  package_size?: string;
  route: MedicationRoute;
}

/**
 * Standard dosing information
 */
export interface StandardDosing {
  adult_dose: string;
  pediatric_dose?: string;
  max_daily_dose?: string;
  duration_typical?: string;
  notes?: string;
}

/**
 * Medication catalog entry
 */
export interface MedicationCatalogEntry {
  id: string;
  generic_name: string;
  active_ingredient: string;
  commercial_names: string[];
  category: DrugCategory;
  presentations: CatalogPresentation[];
  standard_dosing?: StandardDosing;
  contraindications: string[];
  interactions: string[];
  warnings: string[];
  controlled_level: ControlledSubstanceLevel;
  requires_prescription: boolean;
  cofepris_key?: string;
  is_essential: boolean;
  is_active: boolean;
}

/**
 * Catalog search result
 */
export interface CatalogSearchResult {
  medication: MedicationCatalogEntry;
  score: number;
  match_type: "exact" | "starts_with" | "contains" | "commercial_exact" | "commercial_starts_with";
}

/**
 * Search response
 */
export interface CatalogSearchResponse {
  query: string;
  total_matches: number;
  results: CatalogSearchResult[];
}

/**
 * Autocomplete response
 */
export interface AutocompleteResponse {
  prefix: string;
  suggestions: string[];
}

/**
 * Category option
 */
export interface CategoryOption {
  value: string;
  label: string;
}

/**
 * Catalog statistics
 */
export interface CatalogStats {
  total_medications: number;
  active_medications: number;
  essential_medications: number;
  otc_medications: number;
  controlled_medications: number;
  categories_used: number;
}

// ============================================================================
// Drug Category Labels
// ============================================================================

export const DRUG_CATEGORY_LABELS: Record<DrugCategory, string> = {
  analgesic: "Analgésico",
  antibiotic: "Antibiótico",
  antiviral: "Antiviral",
  antifungal: "Antimicótico",
  antiinflammatory: "Antiinflamatorio",
  antihypertensive: "Antihipertensivo",
  antidiabetic: "Antidiabético",
  antihistamine: "Antihistamínico",
  antacid: "Antiácido/IBP",
  bronchodilator: "Broncodilatador",
  corticosteroid: "Corticosteroide",
  antidepressant: "Antidepresivo",
  anxiolytic: "Ansiolítico",
  antipsychotic: "Antipsicótico",
  anticoagulant: "Anticoagulante",
  anticonvulsant: "Anticonvulsivo",
  diuretic: "Diurético",
  vitamin: "Vitamina/Suplemento",
  hormone: "Hormona",
  muscle_relaxant: "Relajante Muscular",
  gastrointestinal: "Gastrointestinal",
  dermatologic: "Dermatológico",
  ophthalmic: "Oftálmico",
  otic: "Ótico",
  other: "Otro",
};

export const CONTROLLED_LEVEL_LABELS: Record<ControlledSubstanceLevel, string> = {
  none: "Sin control",
  fraction_i: "Fracción I - No uso médico",
  fraction_ii: "Fracción II - Receta especial",
  fraction_iii: "Fracción III - Receta retenida",
  fraction_iv: "Fracción IV - Receta médica",
  fraction_v: "Fracción V - OTC con restricciones",
  fraction_vi: "Fracción VI - OTC",
};

// ============================================================================
// Catalog API Functions
// ============================================================================

/**
 * Search medication catalog
 */
export async function searchCatalog(options: {
  query: string;
  category?: DrugCategory;
  essentialOnly?: boolean;
  otcOnly?: boolean;
  limit?: number;
}): Promise<CatalogSearchResponse> {
  const params = new URLSearchParams();
  params.set("q", options.query);
  if (options.category) params.set("category", options.category);
  if (options.essentialOnly) params.set("essential_only", "true");
  if (options.otcOnly) params.set("otc_only", "true");
  if (options.limit) params.set("limit", String(options.limit));

  const response = await fetch(`${API_BASE()}/catalog/search?${params}`);
  if (!response.ok) {
    throw new Error(`Failed to search catalog: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get autocomplete suggestions for medication names
 */
export async function autocompleteMedication(
  prefix: string,
  limit = 5,
  category?: DrugCategory
): Promise<AutocompleteResponse> {
  const params = new URLSearchParams();
  params.set("prefix", prefix);
  params.set("limit", String(limit));
  if (category) params.set("category", category);

  const response = await fetch(`${API_BASE()}/catalog/autocomplete?${params}`);
  if (!response.ok) {
    throw new Error(`Failed to autocomplete: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get medication details by ID
 */
export async function getCatalogMedication(
  medicationId: string
): Promise<{ medication: MedicationCatalogEntry }> {
  const response = await fetch(`${API_BASE()}/catalog/${medicationId}`);
  if (!response.ok) {
    throw new Error(`Failed to get medication: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get all available drug categories
 */
export async function getCatalogCategories(): Promise<{
  categories: CategoryOption[];
}> {
  const response = await fetch(`${API_BASE()}/catalog/categories/list`);
  if (!response.ok) {
    throw new Error(`Failed to get categories: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get catalog statistics
 */
export async function getCatalogStats(): Promise<{ stats: CatalogStats }> {
  const response = await fetch(`${API_BASE()}/catalog/stats`);
  if (!response.ok) {
    throw new Error(`Failed to get catalog stats: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get essential medications (cuadro básico)
 */
export async function getEssentialMedications(
  limit = 50
): Promise<{ count: number; medications: MedicationCatalogEntry[] }> {
  const response = await fetch(
    `${API_BASE()}/catalog/essential?limit=${limit}`
  );
  if (!response.ok) {
    throw new Error(`Failed to get essential medications: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get OTC medications
 */
export async function getOTCMedications(
  limit = 50
): Promise<{ count: number; medications: MedicationCatalogEntry[] }> {
  const response = await fetch(`${API_BASE()}/catalog/otc?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to get OTC medications: ${response.statusText}`);
  }
  return response.json();
}

// ============================================================================
// Safety Check Types (FI-RX-008 + FI-RX-009)
// ============================================================================

/**
 * Interaction severity levels
 */
export type InteractionSeverity =
  | "minor"
  | "moderate"
  | "major"
  | "contraindicated";

/**
 * Allergy severity levels
 */
export type AllergySeverity = "mild" | "moderate" | "severe";

/**
 * Drug interaction alert
 */
export interface InteractionAlertData {
  drug_1: string;
  drug_2: string;
  severity: InteractionSeverity;
  effect: string;
  recommendation: string;
  can_override: boolean;
  alert_message?: string;
}

/**
 * Allergy alert
 */
export interface AllergyAlertData {
  medication: string;
  patient_allergy: string;
  severity: AllergySeverity;
  allergen_type: string;
  notes: string | null;
  can_override: boolean;
  alert_message?: string;
}

/**
 * Interaction check result
 */
export interface InteractionCheckResult {
  alert_count: number;
  has_major: boolean;
  can_proceed: boolean;
  summary: string;
  alerts: InteractionAlertData[];
}

/**
 * Allergy check result
 */
export interface AllergyCheckResult {
  alert_count: number;
  has_severe: boolean;
  can_proceed: boolean;
  summary: string;
  alerts: AllergyAlertData[];
}

/**
 * Full safety check response
 */
export interface SafetyCheckResponse {
  medications_checked: string[];
  patient_allergies: string[];
  can_proceed: boolean;
  has_critical_issues: boolean;
  summary: string;
  interactions: InteractionCheckResult;
  allergies: AllergyCheckResult;
}

// ============================================================================
// Severity Labels
// ============================================================================

export const INTERACTION_SEVERITY_LABELS: Record<InteractionSeverity, string> = {
  minor: "Menor",
  moderate: "Moderada",
  major: "Mayor",
  contraindicated: "Contraindicada",
};

export const ALLERGY_SEVERITY_LABELS: Record<AllergySeverity, string> = {
  mild: "Leve",
  moderate: "Moderada",
  severe: "Grave",
};

export const INTERACTION_SEVERITY_COLORS: Record<InteractionSeverity, string> = {
  minor: "text-blue-500 bg-blue-50 border-blue-200",
  moderate: "text-yellow-600 bg-yellow-50 border-yellow-200",
  major: "text-orange-600 bg-orange-50 border-orange-200",
  contraindicated: "text-red-600 bg-red-50 border-red-200",
};

export const ALLERGY_SEVERITY_COLORS: Record<AllergySeverity, string> = {
  mild: "text-blue-500 bg-blue-50 border-blue-200",
  moderate: "text-yellow-600 bg-yellow-50 border-yellow-200",
  severe: "text-red-600 bg-red-50 border-red-200",
};

// ============================================================================
// Safety Check API Functions
// ============================================================================

/**
 * Check medications for drug interactions
 */
export async function checkInteractions(
  medications: string[]
): Promise<{
  medications_checked: string[];
  alert_count: number;
  has_major_interactions: boolean;
  can_proceed: boolean;
  summary: string;
  alerts: InteractionAlertData[];
}> {
  const response = await fetch(`${API_BASE()}/interactions/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ medications }),
  });
  if (!response.ok) {
    throw new Error(`Failed to check interactions: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Check medications against patient allergies
 */
export async function checkAllergies(
  medications: string[],
  patientAllergies: string[]
): Promise<{
  medications_checked: string[];
  patient_allergies: string[];
  alert_count: number;
  has_severe_allergies: boolean;
  can_proceed: boolean;
  summary: string;
  alerts: AllergyAlertData[];
}> {
  const response = await fetch(`${API_BASE()}/allergies/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      medications,
      patient_allergies: patientAllergies,
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to check allergies: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Run comprehensive safety check (interactions + allergies)
 */
export async function runSafetyCheck(
  medications: Medication[],
  patientAllergies: string[] = []
): Promise<SafetyCheckResponse> {
  const response = await fetch(`${API_BASE()}/safety/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      medications,
      patient_allergies: patientAllergies,
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to run safety check: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get interactions for a specific drug
 */
export async function getDrugInteractions(
  drugName: string
): Promise<{
  drug_name: string;
  interaction_count: number;
  interactions: Array<{
    id: string;
    interacting_drug: string;
    severity: InteractionSeverity;
    effect: string;
    recommendation: string;
    mechanism: string | null;
  }>;
}> {
  const response = await fetch(
    `${API_BASE()}/interactions/drug/${encodeURIComponent(drugName)}`
  );
  if (!response.ok) {
    throw new Error(`Failed to get drug interactions: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get allergens for a specific medication
 */
export async function getMedicationAllergens(
  medicationName: string
): Promise<{
  medication_name: string;
  allergen_count: number;
  allergens: Array<{
    id: string;
    name: string;
    type: string;
    severity: AllergySeverity;
    notes: string | null;
  }>;
}> {
  const response = await fetch(
    `${API_BASE()}/allergies/medication/${encodeURIComponent(medicationName)}`
  );
  if (!response.ok) {
    throw new Error(`Failed to get medication allergens: ${response.statusText}`);
  }
  return response.json();
}
