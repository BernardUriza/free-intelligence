'use client';

import {
  AdminAlert,
  AdminButton,
  AdminSheet,
  ensureAdminKitStyle
} from "../chunk-VQSI5OGB.js";
import {
  glassTokens
} from "../chunk-LO4SF24V.js";
import "../chunk-SMPLGG7E.js";
import {
  FI_MOBILE_QUERY,
  FI_TOUCH_QUERY
} from "../chunk-HJ2CVNCV.js";

// src/persona-admin/types.ts
var defaultPersonaConfirm = async (message) => typeof window !== "undefined" && typeof window.confirm === "function" ? window.confirm(message) : false;
function errorMessage(err, fallback) {
  return err instanceof Error && err.message ? err.message : fallback;
}

// src/persona-admin/schema.ts
import { z } from "zod";
var PERSONA_ID_PATTERN = /^[a-z][a-z0-9_]*$/;
var personaExampleSchema = z.object({
  input: z.string().min(1, { message: "Input is required" }),
  output: z.union([z.string(), z.record(z.string(), z.unknown())])
});
var basePersonaSchema = z.object({
  name: z.string().min(1, "El nombre es requerido").max(100, "El nombre no puede exceder 100 caracteres"),
  description: z.string().min(10, "La descripci\xF3n debe tener al menos 10 caracteres").max(500, "La descripci\xF3n no puede exceder 500 caracteres"),
  system_prompt: z.string().min(20, "El prompt del sistema debe tener al menos 20 caracteres").max(1e4, "El prompt del sistema no puede exceder 10,000 caracteres"),
  model: z.string().min(1, "El modelo es requerido"),
  voice: z.string().nullable().optional(),
  temperature: z.number().min(0, "La temperatura debe ser al menos 0").max(1, "La temperatura no puede exceder 1"),
  max_tokens: z.number().int("Max tokens debe ser un n\xFAmero entero").min(1, "Max tokens debe ser al menos 1").max(8192, "Max tokens no puede exceder 8192"),
  examples: z.array(personaExampleSchema).optional().default([])
});
var personaCreateSchema = basePersonaSchema.extend({
  id: z.string().min(1, "El ID es requerido").max(64, "El ID no puede exceder 64 caracteres").regex(
    PERSONA_ID_PATTERN,
    "El ID debe empezar con letra min\xFAscula y solo contener letras, n\xFAmeros y guiones bajos"
  )
});
var personaUpdateSchema = basePersonaSchema.partial();
var DEFAULT_PERSONA_VALUES = {
  id: "",
  name: "",
  description: "",
  system_prompt: "",
  model: "qwen3:1.7b",
  voice: "nova",
  temperature: 0.7,
  max_tokens: 2048,
  examples: []
};
var PERSONA_FIELD_CONSTRAINTS = {
  name: { min: 1, max: 100 },
  description: { min: 10, max: 500 },
  system_prompt: { min: 20, max: 1e4 },
  id: { min: 1, max: 64, pattern: PERSONA_ID_PATTERN },
  temperature: { min: 0, max: 1, step: 0.05 },
  max_tokens: { min: 1, max: 8192, step: 256 }
};
function toResult(result) {
  if (result.success) return { success: true, data: result.data };
  const errors = {};
  for (const issue of result.error.issues) {
    const path = issue.path.join(".") || "root";
    if (!(path in errors)) errors[path] = issue.message;
  }
  return { success: false, errors };
}
function validatePersonaCreate(data) {
  return toResult(personaCreateSchema.safeParse(data));
}
function validatePersonaUpdate(data) {
  return toResult(personaUpdateSchema.safeParse(data));
}

// src/persona-admin/mappers.ts
function omitHidden(request, hiddenFields) {
  if (hiddenFields.length === 0) return request;
  const copy = { ...request };
  for (const field of hiddenFields) delete copy[field];
  return copy;
}
function mapFormToCreateRequest(form, hiddenFields = []) {
  return omitHidden(
    {
      id: form.id,
      name: form.name,
      description: form.description,
      system_prompt: form.system_prompt,
      model: form.model,
      voice: form.voice,
      temperature: form.temperature,
      max_tokens: form.max_tokens,
      examples: form.examples
    },
    hiddenFields
  );
}
function mapFormToUpdateRequest(form, hiddenFields = []) {
  const request = {};
  if (form.name !== void 0) request.name = form.name;
  if (form.description !== void 0) request.description = form.description;
  if (form.system_prompt !== void 0) request.system_prompt = form.system_prompt;
  if (form.model !== void 0) request.model = form.model;
  if (form.voice !== void 0) request.voice = form.voice;
  if (form.temperature !== void 0) request.temperature = form.temperature;
  if (form.max_tokens !== void 0) request.max_tokens = form.max_tokens;
  if (form.examples !== void 0) request.examples = form.examples;
  return omitHidden(request, hiddenFields);
}
function mapPersonaToFormValues(persona) {
  return {
    name: persona.name,
    description: persona.description,
    system_prompt: persona.system_prompt,
    model: persona.model,
    voice: persona.voice ?? null,
    temperature: persona.temperature,
    max_tokens: persona.max_tokens,
    examples: persona.examples
  };
}

// src/persona-admin/PersonaForm.tsx
import { useCallback, useId } from "react";
import { Cpu, Mic } from "lucide-react";

// src/persona-admin/controls.tsx
import { AlertCircle } from "lucide-react";
import { jsx, jsxs } from "react/jsx-runtime";
function FieldLabel({
  htmlFor,
  required,
  icon: Icon,
  children
}) {
  return /* @__PURE__ */ jsxs("label", { className: "fi-persona-label", htmlFor, children: [
    Icon ? /* @__PURE__ */ jsx(Icon, { size: 14, "aria-hidden": "true" }) : null,
    children,
    required ? /* @__PURE__ */ jsx("span", { className: "fi-persona-required", children: "*" }) : null
  ] });
}
function FieldError({ id, error }) {
  if (!error) return null;
  return /* @__PURE__ */ jsxs("p", { id, className: "fi-persona-error", role: "alert", children: [
    /* @__PURE__ */ jsx(AlertCircle, { size: 12, "aria-hidden": "true" }),
    error
  ] });
}
function OptionSelect({
  id,
  value,
  options,
  onChange,
  disabled,
  emptyLabel,
  ariaInvalid
}) {
  const known = value === "" || options.some((o) => o.value === value);
  const all = known ? [...options] : [{ value, label: value }, ...options];
  const ungrouped = all.filter((o) => !o.group);
  const groups = [...new Set(all.filter((o) => o.group).map((o) => o.group))];
  return /* @__PURE__ */ jsxs(
    "select",
    {
      id,
      className: "fi-persona-input",
      value,
      onChange: (e) => onChange(e.target.value),
      disabled,
      "aria-invalid": ariaInvalid || void 0,
      children: [
        emptyLabel !== void 0 ? /* @__PURE__ */ jsx("option", { value: "", children: emptyLabel }) : null,
        ungrouped.map((o) => /* @__PURE__ */ jsx("option", { value: o.value, children: o.label }, o.value)),
        groups.map((group) => /* @__PURE__ */ jsx("optgroup", { label: group, children: all.filter((o) => o.group === group).map((o) => /* @__PURE__ */ jsx("option", { value: o.value, children: o.label }, `${group}-${o.value}`)) }, group))
      ]
    }
  );
}

// src/persona-admin/personaAdminStyle.ts
import { useInsertionEffect } from "react";
var FI_PERSONA_ROOT_CLASS = "fi-persona-admin";
var STYLE_ID = "fi-persona-admin-style";
var ACCENT = `var(--fi-persona-accent, ${glassTokens.accent})`;
var TEXT = `var(--glass-chat-text, ${glassTokens.text})`;
var MUTED = `var(--glass-chat-text-muted, ${glassTokens.textMuted})`;
var DANGER = `var(--fi-persona-danger, ${glassTokens.danger})`;
var BORDER = `var(--fi-persona-border, ${glassTokens.surfaceBorder})`;
var FIELD_BG = `var(--fi-persona-field-bg, ${glassTokens.searchFill})`;
var CSS = `
.${FI_PERSONA_ROOT_CLASS} { color: ${TEXT}; font-size: 0.875rem; --fi-admin-sheet-width: var(--fi-persona-sheet-width, 42rem); --fi-admin-panel-width: var(--fi-persona-panel-width, 64rem); --fi-admin-accent: ${ACCENT}; }
.fi-persona-stack { display: flex; flex-direction: column; gap: 1.25rem; }
.fi-persona-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.fi-persona-field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.fi-persona-label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8125rem; font-weight: 500; color: ${MUTED}; }
.fi-persona-required { color: ${DANGER}; }
.fi-persona-input {
  width: 100%; box-sizing: border-box; padding: 0.625rem 0.75rem; border-radius: 10px;
  font: inherit; font-size: 0.875rem; color: ${TEXT}; background: ${FIELD_BG};
  border-width: 1px; border-style: solid; border-color: ${BORDER}; outline: none; transition: border-color 0.12s ease;
}
.fi-persona-input:focus-visible { border-color: ${ACCENT}; box-shadow: 0 0 0 1px ${ACCENT}; }
.fi-persona-input[aria-invalid="true"] { border-color: ${DANGER}; }
.fi-persona-input:disabled { opacity: 0.55; cursor: not-allowed; }
.fi-persona-input option, .fi-persona-input optgroup { color: #0f172a; }
textarea.fi-persona-input { resize: vertical; line-height: 1.5; }
.fi-persona-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.fi-persona-range { width: 100%; accent-color: ${ACCENT}; min-height: 24px; }
.fi-persona-hint { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.75rem; color: ${MUTED}; }
.fi-persona-error { display: flex; align-items: center; gap: 0.25rem; margin: 0; font-size: 0.75rem; color: ${DANGER}; }
.fi-persona-title { margin: 0; font-size: 1.125rem; font-weight: 600; color: ${TEXT}; display: flex; align-items: center; gap: 0.5rem; }
.fi-persona-subtitle { margin: 0.15rem 0 0; font-size: 0.8125rem; color: ${MUTED}; }
.fi-persona-actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.fi-persona-tabs { display: flex; gap: 0.35rem; overflow-x: auto; width: 100%; scrollbar-width: none; }
.fi-persona-tab { white-space: nowrap; }
.fi-persona-tab[aria-selected="true"] { border-color: ${ACCENT}; color: ${ACCENT}; }
.fi-persona-card {
  display: flex; flex-direction: column; gap: 1rem; padding: 1.25rem; border-radius: 14px; cursor: pointer;
  text-align: left; color: inherit; background: ${glassTokens.surface};
  border-width: 1px; border-style: solid; border-color: color-mix(in srgb, ${ACCENT} 30%, transparent); transition: border-color 0.12s ease, background 0.12s ease;
}
.fi-persona-card:hover { border-color: ${ACCENT}; }
.fi-persona-card[data-selected="true"] { border-color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 10%, ${glassTokens.surface}); }
.fi-persona-card:focus-visible { outline: none; box-shadow: 0 0 0 2px ${ACCENT}; }
.fi-persona-card-head { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.fi-persona-card-id { display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
.fi-persona-card-icon {
  flex: 0 0 auto; display: inline-flex; padding: 0.5rem; border-radius: 10px; color: ${ACCENT};
  background: color-mix(in srgb, ${ACCENT} 15%, transparent); border-width: 1px; border-style: solid; border-color: color-mix(in srgb, ${ACCENT} 40%, transparent);
}
.fi-persona-card-name { margin: 0; font-size: 1.0625rem; font-weight: 700; color: ${TEXT}; overflow: hidden; text-overflow: ellipsis; }
.fi-persona-card-desc {
  margin: 0; color: ${MUTED}; min-height: 2.5em; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden;
}
.fi-persona-card-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }
.fi-persona-mini { padding: 0.5rem 0.625rem; border-radius: 8px; background: ${glassTokens.chipFill}; min-width: 0; }
.fi-persona-mini dt { font-size: 0.6875rem; color: ${MUTED}; }
.fi-persona-mini dd { margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fi-persona-card-foot { display: flex; flex-direction: column; gap: 0.25rem; padding-top: 0.75rem; border-top-width: 1px; border-top-style: solid; border-top-color: ${BORDER}; font-size: 0.75rem; color: ${MUTED}; }
.fi-persona-row { display: flex; justify-content: space-between; gap: 0.5rem; }
.fi-persona-row b { color: ${TEXT}; font-weight: 600; }
.fi-persona-example { display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; border-radius: 12px; background: ${glassTokens.surface}; border-width: 1px; border-style: solid; border-color: ${BORDER}; }
.fi-persona-pre { margin: 0; padding: 1rem; border-radius: 10px; white-space: pre-wrap; overflow-x: auto; background: ${glassTokens.codeBlockBg}; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.8125rem; }
.fi-persona-empty { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 2rem 1rem; color: ${MUTED}; text-align: center; }
@media ${FI_MOBILE_QUERY} {
  .fi-persona-grid, .fi-persona-card-stats { grid-template-columns: minmax(0, 1fr); }
  .fi-persona-input { font-size: 16px; }
}
@media ${FI_TOUCH_QUERY} {
  .fi-persona-input { min-height: var(--fi-touch-target, 44px); }
}
`;
function ensurePersonaAdminStyle() {
  if (typeof document === "undefined") return;
  ensureAdminKitStyle();
  if (document.getElementById(STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}
function usePersonaAdminStyle() {
  useInsertionEffect(() => {
    ensurePersonaAdminStyle();
  }, []);
}

// src/persona-admin/PersonaForm.tsx
import { jsx as jsx2, jsxs as jsxs2 } from "react/jsx-runtime";
function generateIdFromName(name) {
  return name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9\s]/g, "").trim().replace(/\s+/g, "_").replace(/^[^a-z]+/, "").slice(0, PERSONA_FIELD_CONSTRAINTS.id.max);
}
function temperatureLabel(t) {
  if (t < 0.3) return "Determin\xEDstico";
  if (t < 0.7) return "Balanceado";
  return "Creativo";
}
function PersonaForm({
  value,
  onChange,
  mode,
  modelOptions,
  voiceOptions = [],
  hiddenFields = [],
  disabled = false,
  errors = {},
  personaId,
  showSystemPrompt = true,
  showExamplesSummary = false,
  noVoiceLabel = "Sin voz (Solo texto)"
}) {
  usePersonaAdminStyle();
  const uid = useId();
  const fid = (name) => `${uid}-${name}`;
  const isCreate = mode === "create";
  const form = value;
  const hidden = new Set(hiddenFields);
  const set = useCallback(
    (field, next) => {
      onChange({ ...value, [field]: next });
    },
    [value, onChange]
  );
  const setName = useCallback(
    (name) => {
      if (!isCreate) return onChange({ ...value, name });
      const current = form.id ?? "";
      const derived = !current || current === generateIdFromName(form.name ?? "");
      onChange({ ...value, name, ...derived ? { id: generateIdFromName(name) } : {} });
    },
    [value, onChange, isCreate, form.id, form.name]
  );
  const invalid = (field) => errors[field] ? true : void 0;
  const describedBy = (field) => errors[field] ? fid(`${field}-error`) : void 0;
  const temperature = form.temperature ?? 0.7;
  return /* @__PURE__ */ jsxs2("div", { className: `${FI_PERSONA_ROOT_CLASS} fi-persona-stack`, children: [
    /* @__PURE__ */ jsxs2("div", { className: "fi-persona-grid", children: [
      /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsx2(FieldLabel, { htmlFor: fid("name"), required: true, children: "Nombre" }),
        /* @__PURE__ */ jsx2(
          "input",
          {
            id: fid("name"),
            className: "fi-persona-input",
            type: "text",
            value: form.name ?? "",
            onChange: (e) => setName(e.target.value),
            placeholder: "Ej: Asistente de Nutrici\xF3n",
            disabled,
            maxLength: PERSONA_FIELD_CONSTRAINTS.name.max,
            "aria-invalid": invalid("name"),
            "aria-describedby": describedBy("name")
          }
        ),
        /* @__PURE__ */ jsx2(FieldError, { id: fid("name-error"), error: errors.name })
      ] }),
      /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsx2(FieldLabel, { htmlFor: fid("id"), required: isCreate, children: "ID \xFAnico" }),
        /* @__PURE__ */ jsx2(
          "input",
          {
            id: fid("id"),
            className: "fi-persona-input fi-persona-mono",
            type: "text",
            value: isCreate ? form.id ?? "" : personaId ?? "",
            onChange: (e) => set("id", e.target.value.toLowerCase()),
            placeholder: "ej: nutrition_assistant",
            disabled: disabled || !isCreate,
            readOnly: !isCreate,
            maxLength: PERSONA_FIELD_CONSTRAINTS.id.max,
            "aria-invalid": invalid("id"),
            "aria-describedby": describedBy("id")
          }
        ),
        /* @__PURE__ */ jsx2(FieldError, { id: fid("id-error"), error: errors.id })
      ] })
    ] }),
    /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
      /* @__PURE__ */ jsx2(FieldLabel, { htmlFor: fid("description"), required: true, children: "Descripci\xF3n" }),
      /* @__PURE__ */ jsx2(
        "textarea",
        {
          id: fid("description"),
          className: "fi-persona-input",
          rows: 2,
          value: form.description ?? "",
          onChange: (e) => set("description", e.target.value),
          placeholder: "Describe el prop\xF3sito y comportamiento de esta persona...",
          disabled,
          maxLength: PERSONA_FIELD_CONSTRAINTS.description.max,
          "aria-invalid": invalid("description"),
          "aria-describedby": describedBy("description")
        }
      ),
      /* @__PURE__ */ jsxs2("div", { className: "fi-persona-hint", children: [
        /* @__PURE__ */ jsx2(FieldError, { id: fid("description-error"), error: errors.description }),
        /* @__PURE__ */ jsxs2("span", { children: [
          (form.description ?? "").length,
          "/",
          PERSONA_FIELD_CONSTRAINTS.description.max
        ] })
      ] })
    ] }),
    showSystemPrompt ? /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
      /* @__PURE__ */ jsx2(FieldLabel, { htmlFor: fid("system_prompt"), required: true, children: "System Prompt" }),
      /* @__PURE__ */ jsx2(
        "textarea",
        {
          id: fid("system_prompt"),
          className: "fi-persona-input fi-persona-mono",
          rows: 5,
          value: form.system_prompt ?? "",
          onChange: (e) => set("system_prompt", e.target.value),
          placeholder: "Eres un asistente especializado en...",
          disabled,
          maxLength: PERSONA_FIELD_CONSTRAINTS.system_prompt.max,
          "aria-invalid": invalid("system_prompt"),
          "aria-describedby": describedBy("system_prompt")
        }
      ),
      /* @__PURE__ */ jsxs2("div", { className: "fi-persona-hint", children: [
        /* @__PURE__ */ jsx2(FieldError, { id: fid("system_prompt-error"), error: errors.system_prompt }),
        /* @__PURE__ */ jsxs2("span", { children: [
          (form.system_prompt ?? "").length,
          " caracteres"
        ] })
      ] })
    ] }) : null,
    /* @__PURE__ */ jsxs2("div", { className: "fi-persona-grid", children: [
      /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsx2(FieldLabel, { htmlFor: fid("model"), icon: Cpu, children: "Modelo" }),
        /* @__PURE__ */ jsx2(
          OptionSelect,
          {
            id: fid("model"),
            value: form.model ?? "",
            options: modelOptions,
            onChange: (v) => set("model", v),
            disabled,
            ariaInvalid: !!errors.model
          }
        ),
        /* @__PURE__ */ jsx2(FieldError, { error: errors.model })
      ] }),
      hidden.has("voice") ? null : /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsx2(FieldLabel, { htmlFor: fid("voice"), icon: Mic, children: "Voz TTS" }),
        /* @__PURE__ */ jsx2(
          OptionSelect,
          {
            id: fid("voice"),
            value: form.voice ?? "",
            options: voiceOptions,
            onChange: (v) => set("voice", v || null),
            disabled,
            emptyLabel: noVoiceLabel
          }
        ),
        /* @__PURE__ */ jsx2(FieldError, { error: errors.voice })
      ] })
    ] }),
    hidden.has("temperature") && hidden.has("max_tokens") ? null : /* @__PURE__ */ jsxs2("div", { className: "fi-persona-grid", children: [
      hidden.has("temperature") ? null : /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsxs2(FieldLabel, { htmlFor: fid("temperature"), children: [
          "Temperatura: ",
          temperature.toFixed(2),
          " (",
          temperatureLabel(temperature),
          ")"
        ] }),
        /* @__PURE__ */ jsx2(
          "input",
          {
            id: fid("temperature"),
            className: "fi-persona-range",
            type: "range",
            min: PERSONA_FIELD_CONSTRAINTS.temperature.min,
            max: PERSONA_FIELD_CONSTRAINTS.temperature.max,
            step: PERSONA_FIELD_CONSTRAINTS.temperature.step,
            value: temperature,
            onChange: (e) => set("temperature", parseFloat(e.target.value)),
            disabled
          }
        ),
        /* @__PURE__ */ jsxs2("div", { className: "fi-persona-hint", children: [
          /* @__PURE__ */ jsx2("span", { children: "Preciso" }),
          /* @__PURE__ */ jsx2("span", { children: "Creativo" })
        ] }),
        /* @__PURE__ */ jsx2(FieldError, { error: errors.temperature })
      ] }),
      hidden.has("max_tokens") ? null : /* @__PURE__ */ jsxs2("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsx2(FieldLabel, { htmlFor: fid("max_tokens"), children: "Max tokens" }),
        /* @__PURE__ */ jsx2(
          "input",
          {
            id: fid("max_tokens"),
            className: "fi-persona-input",
            type: "number",
            inputMode: "numeric",
            min: PERSONA_FIELD_CONSTRAINTS.max_tokens.min,
            max: PERSONA_FIELD_CONSTRAINTS.max_tokens.max,
            step: PERSONA_FIELD_CONSTRAINTS.max_tokens.step,
            value: form.max_tokens ?? 2048,
            onChange: (e) => set("max_tokens", parseInt(e.target.value, 10) || 0),
            disabled,
            "aria-invalid": invalid("max_tokens")
          }
        ),
        /* @__PURE__ */ jsx2(FieldError, { error: errors.max_tokens })
      ] })
    ] }),
    showExamplesSummary && !hidden.has("examples") && (form.examples?.length ?? 0) > 0 ? /* @__PURE__ */ jsxs2("p", { className: "fi-persona-hint", children: [
      form.examples?.length,
      " ejemplo(s) configurado(s)"
    ] }) : null
  ] });
}

// src/persona-admin/PersonaCreateModal.tsx
import { useCallback as useCallback2, useEffect, useId as useId2, useRef, useState } from "react";
import { Sparkles, X } from "lucide-react";

// src/persona-admin/PersonaSheet.tsx
import { jsx as jsx3 } from "react/jsx-runtime";
var row = (node) => /* @__PURE__ */ jsx3("div", { className: "fi-admin-head-row", children: node });
function PersonaSheet({ header, footer, ...rest }) {
  usePersonaAdminStyle();
  return /* @__PURE__ */ jsx3(AdminSheet, { ...rest, className: FI_PERSONA_ROOT_CLASS, header: row(header), footer: footer ? row(footer) : void 0 });
}

// src/persona-admin/PersonaCreateModal.tsx
import { Fragment, jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
function startingValues(initialValues, modelOptions, voiceOptions) {
  const values = { ...DEFAULT_PERSONA_VALUES, ...initialValues };
  if (!initialValues?.model && modelOptions.length && !modelOptions.some((o) => o.value === values.model)) {
    values.model = modelOptions[0].value;
  }
  if (initialValues?.voice === void 0 && !voiceOptions.some((o) => o.value === values.voice)) {
    values.voice = null;
  }
  return values;
}
function PersonaCreateModal({
  open,
  onOpenChange,
  store,
  onCreated,
  modelOptions,
  voiceOptions = [],
  hiddenFields = [],
  initialValues,
  renderExtraFields,
  validateExtra,
  title = "Crear nueva persona",
  subtitle = "Define una nueva personalidad de IA",
  submitLabel = "Crear persona"
}) {
  const titleId = useId2();
  const startRef = useRef(() => startingValues(initialValues, modelOptions, voiceOptions));
  startRef.current = () => startingValues(initialValues, modelOptions, voiceOptions);
  const [values, setValues] = useState(() => startRef.current());
  const [errors, setErrors] = useState({});
  const [creating, setCreating] = useState(false);
  const [apiError, setApiError] = useState(null);
  useEffect(() => {
    if (open) {
      setValues(startRef.current());
      setErrors({});
      setApiError(null);
    }
  }, [open]);
  const close = useCallback2(() => {
    if (!creating) onOpenChange(false);
  }, [creating, onOpenChange]);
  const submit = useCallback2(async () => {
    const validation = validatePersonaCreate(values);
    if (!validation.success || !validation.data) {
      setErrors(validation.errors ?? {});
      return;
    }
    const extraError = validateExtra?.() ?? null;
    if (extraError) {
      setApiError(extraError);
      return;
    }
    setErrors({});
    setApiError(null);
    setCreating(true);
    try {
      const persona = await store.create(mapFormToCreateRequest(validation.data, hiddenFields));
      onCreated(persona);
      onOpenChange(false);
    } catch (err) {
      setApiError(errorMessage(err, "Error inesperado al crear la persona"));
    } finally {
      setCreating(false);
    }
  }, [values, validateExtra, store, hiddenFields, onCreated, onOpenChange]);
  const change = useCallback2((next) => {
    setValues(next);
    setErrors((prev) => Object.keys(prev).length ? {} : prev);
  }, []);
  if (!open) return null;
  return /* @__PURE__ */ jsx4(
    PersonaSheet,
    {
      onDismiss: close,
      labelledBy: titleId,
      header: /* @__PURE__ */ jsxs3(Fragment, { children: [
        /* @__PURE__ */ jsxs3("div", { children: [
          /* @__PURE__ */ jsxs3("h2", { id: titleId, className: "fi-persona-title", children: [
            /* @__PURE__ */ jsx4(Sparkles, { size: 20, "aria-hidden": "true" }),
            title
          ] }),
          /* @__PURE__ */ jsx4("p", { className: "fi-persona-subtitle", children: subtitle })
        ] }),
        /* @__PURE__ */ jsx4(AdminButton, { variant: "ghost", iconOnly: true, icon: X, onClick: close, disabled: creating, "aria-label": "Cerrar" })
      ] }),
      footer: /* @__PURE__ */ jsxs3(Fragment, { children: [
        /* @__PURE__ */ jsxs3("p", { className: "fi-persona-subtitle", children: [
          /* @__PURE__ */ jsx4("span", { className: "fi-persona-required", children: "*" }),
          " Campos requeridos"
        ] }),
        /* @__PURE__ */ jsxs3("div", { className: "fi-persona-actions", children: [
          /* @__PURE__ */ jsx4(AdminButton, { onClick: close, disabled: creating, children: "Cancelar" }),
          /* @__PURE__ */ jsx4(
            AdminButton,
            {
              variant: "primary",
              icon: Sparkles,
              loading: creating,
              disabled: creating,
              onClick: () => void submit(),
              children: creating ? "Creando..." : submitLabel
            }
          )
        ] })
      ] }),
      children: /* @__PURE__ */ jsxs3(
        "form",
        {
          className: "fi-persona-stack",
          onSubmit: (e) => {
            e.preventDefault();
            void submit();
          },
          children: [
            renderExtraFields?.(),
            /* @__PURE__ */ jsx4(
              PersonaForm,
              {
                value: values,
                onChange: change,
                mode: "create",
                modelOptions,
                voiceOptions,
                hiddenFields,
                disabled: creating,
                errors,
                showExamplesSummary: true
              }
            ),
            apiError ? /* @__PURE__ */ jsx4(AdminAlert, { children: apiError }) : null
          ]
        }
      )
    }
  );
}

// src/persona-admin/PersonaEditor.tsx
import { useCallback as useCallback3, useEffect as useEffect2, useId as useId4, useRef as useRef2, useState as useState3 } from "react";
import { Brain, FileText, List as List2, Loader2, Save, Settings, Trash2 as Trash22, X as X2, Zap as Zap2 } from "lucide-react";

// src/persona-admin/PersonaEditorTabs.tsx
import { useId as useId3, useState as useState2 } from "react";
import { List, Plus, Trash2, Zap } from "lucide-react";
import { jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
function PersonaPromptTab({ persona, onChange }) {
  const id = useId3();
  return /* @__PURE__ */ jsxs4("div", { className: "fi-persona-field", children: [
    /* @__PURE__ */ jsxs4("div", { className: "fi-persona-hint", children: [
      /* @__PURE__ */ jsx5(FieldLabel, { htmlFor: id, children: "System Prompt" }),
      /* @__PURE__ */ jsxs4("span", { children: [
        persona.system_prompt.length,
        " caracteres"
      ] })
    ] }),
    /* @__PURE__ */ jsx5(
      "textarea",
      {
        id,
        className: "fi-persona-input fi-persona-mono",
        rows: 22,
        value: persona.system_prompt,
        onChange: (e) => onChange({ system_prompt: e.target.value }),
        placeholder: "Eres un..."
      }
    )
  ] });
}
function outputText(output) {
  return typeof output === "string" ? output : JSON.stringify(output, null, 2);
}
function PersonaExamplesTab({ persona, onChange }) {
  const uid = useId3();
  const examples = persona.examples;
  const update = (index, field, value) => onChange({ examples: examples.map((ex, i) => i === index ? { ...ex, [field]: value } : ex) });
  return /* @__PURE__ */ jsxs4("div", { className: "fi-persona-stack", children: [
    /* @__PURE__ */ jsxs4("div", { className: "fi-persona-hint", children: [
      /* @__PURE__ */ jsxs4("h3", { className: "fi-persona-title", children: [
        "Few-shot examples (",
        examples.length,
        ")"
      ] }),
      /* @__PURE__ */ jsx5(AdminButton, { icon: Plus, onClick: () => onChange({ examples: [...examples, { input: "", output: "" }] }), children: "Agregar example" })
    ] }),
    examples.length === 0 ? /* @__PURE__ */ jsxs4("div", { className: "fi-persona-empty", children: [
      /* @__PURE__ */ jsx5(List, { size: 40, "aria-hidden": "true" }),
      /* @__PURE__ */ jsx5("p", { children: "No hay examples configurados" }),
      /* @__PURE__ */ jsx5("p", { children: "Agrega examples para mejorar la precisi\xF3n de la persona" })
    ] }) : examples.map((example, index) => /* @__PURE__ */ jsxs4("div", { className: "fi-persona-example", children: [
      /* @__PURE__ */ jsxs4("div", { className: "fi-persona-hint", children: [
        /* @__PURE__ */ jsxs4("strong", { children: [
          "Example ",
          index + 1
        ] }),
        /* @__PURE__ */ jsx5(
          AdminButton,
          {
            variant: "ghost",
            iconOnly: true,
            icon: Trash2,
            "aria-label": `Eliminar example ${index + 1}`,
            onClick: () => onChange({ examples: examples.filter((_, i) => i !== index) })
          }
        )
      ] }),
      /* @__PURE__ */ jsxs4("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsx5(FieldLabel, { htmlFor: `${uid}-in-${index}`, children: "Input" }),
        /* @__PURE__ */ jsx5(
          "textarea",
          {
            id: `${uid}-in-${index}`,
            className: "fi-persona-input fi-persona-mono",
            rows: 3,
            value: example.input,
            onChange: (e) => update(index, "input", e.target.value),
            placeholder: "Entrada de ejemplo..."
          }
        )
      ] }),
      /* @__PURE__ */ jsxs4("div", { className: "fi-persona-field", children: [
        /* @__PURE__ */ jsx5(FieldLabel, { htmlFor: `${uid}-out-${index}`, children: "Output" }),
        /* @__PURE__ */ jsx5(
          "textarea",
          {
            id: `${uid}-out-${index}`,
            className: "fi-persona-input fi-persona-mono",
            rows: 3,
            value: outputText(example.output),
            onChange: (e) => update(index, "output", e.target.value),
            placeholder: "Salida esperada..."
          }
        )
      ] })
    ] }, index))
  ] });
}
function PersonaTestTab({ personaId, store }) {
  const id = useId3();
  const [input, setInput] = useState2("");
  const [result, setResult] = useState2(null);
  const [testing, setTesting] = useState2(false);
  const [error, setError] = useState2(null);
  const run = async () => {
    if (!input.trim()) return;
    setTesting(true);
    setError(null);
    try {
      setResult(await store.test(personaId, input));
    } catch (err) {
      setError(errorMessage(err, "Error al probar la persona"));
    } finally {
      setTesting(false);
    }
  };
  return /* @__PURE__ */ jsxs4("div", { className: "fi-persona-stack", children: [
    /* @__PURE__ */ jsxs4("div", { children: [
      /* @__PURE__ */ jsx5("h3", { className: "fi-persona-title", children: "Probar persona" }),
      /* @__PURE__ */ jsx5("p", { className: "fi-persona-subtitle", children: "Prueba la persona con un input de ejemplo para ver c\xF3mo responde" })
    ] }),
    /* @__PURE__ */ jsxs4("div", { className: "fi-persona-field", children: [
      /* @__PURE__ */ jsx5(FieldLabel, { htmlFor: id, children: "Input de prueba" }),
      /* @__PURE__ */ jsx5(
        "textarea",
        {
          id,
          className: "fi-persona-input",
          rows: 6,
          value: input,
          onChange: (e) => setInput(e.target.value),
          placeholder: "Ingresa un caso de prueba..."
        }
      )
    ] }),
    /* @__PURE__ */ jsx5(AdminButton, { variant: "primary", icon: Zap, loading: testing, disabled: testing || !input.trim(), onClick: () => void run(), children: testing ? "Probando..." : "Probar persona" }),
    error ? /* @__PURE__ */ jsx5(AdminAlert, { children: error }) : null,
    result ? /* @__PURE__ */ jsxs4("div", { className: "fi-persona-stack", children: [
      /* @__PURE__ */ jsx5("h4", { className: "fi-persona-title", children: "Resultado" }),
      /* @__PURE__ */ jsx5("pre", { className: "fi-persona-pre", "data-testid": "persona-test-output", children: typeof result.output === "string" ? result.output : JSON.stringify(result.output, null, 2) }),
      /* @__PURE__ */ jsxs4("div", { className: "fi-persona-card-stats", children: [
        /* @__PURE__ */ jsxs4("div", { className: "fi-persona-row", children: [
          /* @__PURE__ */ jsx5("span", { children: "Latencia" }),
          /* @__PURE__ */ jsxs4("b", { children: [
            result.latency_ms.toFixed(0),
            "ms"
          ] })
        ] }),
        result.tokens_used !== void 0 ? /* @__PURE__ */ jsxs4("div", { className: "fi-persona-row", children: [
          /* @__PURE__ */ jsx5("span", { children: "Tokens" }),
          /* @__PURE__ */ jsx5("b", { children: result.tokens_used })
        ] }) : null,
        result.cost_usd !== void 0 ? /* @__PURE__ */ jsxs4("div", { className: "fi-persona-row", children: [
          /* @__PURE__ */ jsx5("span", { children: "Costo" }),
          /* @__PURE__ */ jsxs4("b", { children: [
            "$",
            result.cost_usd.toFixed(4)
          ] })
        ] }) : null
      ] })
    ] }) : null
  ] });
}

// src/persona-admin/PersonaEditor.tsx
import { Fragment as Fragment2, jsx as jsx6, jsxs as jsxs5 } from "react/jsx-runtime";
var TABS = [
  { value: "config", label: "Configuraci\xF3n", icon: Settings },
  { value: "prompt", label: "System Prompt", icon: FileText },
  { value: "examples", label: "Examples", icon: List2 },
  { value: "test", label: "Probar", icon: Zap2 }
];
var defaultDeleteConfirmMessage = (persona) => `\xBFEliminar la persona "${persona.name}"? Esta acci\xF3n no se puede deshacer.`;
function PersonaEditor({
  personaId,
  open,
  onClose,
  onSaved,
  store,
  modelOptions,
  voiceOptions,
  hiddenFields = [],
  onDeleted,
  confirm = defaultPersonaConfirm,
  deleteConfirmMessage = defaultDeleteConfirmMessage,
  locale = "es-MX"
}) {
  const titleId = useId4();
  const [persona, setPersona] = useState3(null);
  const [loading, setLoading] = useState3(true);
  const [busy, setBusy] = useState3(null);
  const [error, setError] = useState3(null);
  const [fieldErrors, setFieldErrors] = useState3({});
  const [tab, setTab] = useState3("config");
  const storeRef = useRef2(store);
  storeRef.current = store;
  useEffect2(() => {
    if (!open || !personaId) return;
    let alive = true;
    setLoading(true);
    setError(null);
    setTab("config");
    storeRef.current.get(personaId).then((data) => alive && setPersona(data)).catch((err) => alive && setError(errorMessage(err, "Error al cargar la persona"))).finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [open, personaId]);
  const patch = useCallback3((updates) => {
    setPersona((prev) => prev ? { ...prev, ...updates } : prev);
    setFieldErrors((prev) => Object.keys(prev).length ? {} : prev);
  }, []);
  const save = async () => {
    if (!persona) return;
    const validation = validatePersonaUpdate(mapPersonaToFormValues(persona));
    if (!validation.success || !validation.data) {
      const errors = validation.errors ?? {};
      setFieldErrors(errors);
      setError(Object.values(errors)[0] ?? "Revisa los campos");
      return;
    }
    setBusy("save");
    setError(null);
    try {
      const updated = await store.update(personaId, mapFormToUpdateRequest(validation.data, hiddenFields));
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Error al guardar la persona"));
    } finally {
      setBusy(null);
    }
  };
  const remove = async () => {
    if (!persona || !store.remove || !onDeleted) return;
    if (!await confirm(deleteConfirmMessage(persona))) return;
    setBusy("delete");
    setError(null);
    try {
      await store.remove(personaId);
      onDeleted(personaId);
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Error al eliminar la persona"));
    } finally {
      setBusy(null);
    }
  };
  if (!open) return null;
  const tabs = TABS.filter((t) => !(t.value === "examples" && hiddenFields.includes("examples")));
  const canDelete = Boolean(store.remove && onDeleted);
  return /* @__PURE__ */ jsx6(
    PersonaSheet,
    {
      placement: "side",
      onDismiss: onClose,
      labelledBy: titleId,
      header: /* @__PURE__ */ jsxs5(Fragment2, { children: [
        /* @__PURE__ */ jsxs5("div", { style: { minWidth: 0 }, children: [
          /* @__PURE__ */ jsxs5("h2", { id: titleId, className: "fi-persona-title", children: [
            /* @__PURE__ */ jsx6(Brain, { size: 22, "aria-hidden": "true" }),
            persona ? `Editar persona: ${persona.name}` : "Editar persona"
          ] }),
          persona?.version !== void 0 || persona?.last_updated ? /* @__PURE__ */ jsxs5("p", { className: "fi-persona-subtitle", children: [
            persona?.version !== void 0 ? `Versi\xF3n ${persona.version}` : null,
            persona?.last_updated ? ` \xB7 \xDAltima actualizaci\xF3n: ${new Date(persona.last_updated).toLocaleDateString(locale)}` : null
          ] }) : null
        ] }),
        /* @__PURE__ */ jsx6(AdminButton, { variant: "ghost", iconOnly: true, icon: X2, onClick: onClose, "aria-label": "Cerrar" }),
        persona ? /* @__PURE__ */ jsx6("div", { className: "fi-persona-tabs", role: "tablist", children: tabs.map((t) => /* @__PURE__ */ jsx6(
          AdminButton,
          {
            role: "tab",
            className: "fi-persona-tab",
            variant: "ghost",
            icon: t.icon,
            "aria-selected": tab === t.value,
            onClick: () => setTab(t.value),
            children: t.label
          },
          t.value
        )) }) : null
      ] }),
      footer: persona ? /* @__PURE__ */ jsxs5(Fragment2, { children: [
        /* @__PURE__ */ jsx6("div", { className: "fi-persona-actions", children: canDelete ? /* @__PURE__ */ jsx6(
          AdminButton,
          {
            variant: "danger",
            icon: Trash22,
            loading: busy === "delete",
            disabled: busy !== null,
            onClick: () => void remove(),
            children: "Eliminar"
          }
        ) : null }),
        /* @__PURE__ */ jsxs5("div", { className: "fi-persona-actions", children: [
          /* @__PURE__ */ jsx6(AdminButton, { onClick: onClose, disabled: busy !== null, children: "Cancelar" }),
          /* @__PURE__ */ jsx6(
            AdminButton,
            {
              variant: "primary",
              icon: Save,
              loading: busy === "save",
              disabled: busy !== null,
              onClick: () => void save(),
              children: "Guardar cambios"
            }
          )
        ] })
      ] }) : void 0,
      children: loading ? /* @__PURE__ */ jsx6("div", { className: "fi-persona-empty", "aria-busy": "true", children: /* @__PURE__ */ jsx6(Loader2, { size: 32, className: "fi-admin-spin", "aria-label": "Cargando" }) }) : /* @__PURE__ */ jsxs5("div", { className: "fi-persona-stack", children: [
        error ? /* @__PURE__ */ jsx6(AdminAlert, { children: error }) : null,
        persona && tab === "config" ? /* @__PURE__ */ jsx6(
          PersonaForm,
          {
            mode: "edit",
            personaId: persona.id,
            value: mapPersonaToFormValues(persona),
            onChange: (v) => patch(v),
            modelOptions,
            voiceOptions,
            hiddenFields,
            errors: fieldErrors,
            showSystemPrompt: false
          }
        ) : null,
        persona && tab === "prompt" ? /* @__PURE__ */ jsx6(PersonaPromptTab, { persona, onChange: patch }) : null,
        persona && tab === "examples" ? /* @__PURE__ */ jsx6(PersonaExamplesTab, { persona, onChange: patch }) : null,
        persona && tab === "test" ? /* @__PURE__ */ jsx6(PersonaTestTab, { personaId: persona.id, store }) : null
      ] })
    }
  );
}

// src/persona-admin/PersonaCard.tsx
import { Brain as Brain2, Edit, Trash2 as Trash23 } from "lucide-react";
import { Fragment as Fragment3, jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
function formatDate(iso, locale) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString(locale, { year: "numeric", month: "short", day: "numeric" });
}
function PersonaCard({
  persona,
  selected = false,
  onSelect,
  onEdit,
  onDelete,
  accentColor,
  hiddenFields = [],
  locale = "es-MX"
}) {
  usePersonaAdminStyle();
  const hidden = new Set(hiddenFields);
  const stats = persona.usage_stats;
  const style = accentColor ? { "--fi-persona-accent": accentColor, "--fi-admin-accent": accentColor } : void 0;
  const onKey = (e) => {
    if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onSelect?.();
    }
  };
  return /* @__PURE__ */ jsxs6(
    "article",
    {
      className: `${FI_PERSONA_ROOT_CLASS} fi-persona-card`,
      "data-selected": selected,
      style,
      tabIndex: 0,
      "aria-label": persona.name,
      onClick: onSelect,
      onKeyDown: onKey,
      children: [
        /* @__PURE__ */ jsxs6("div", { className: "fi-persona-card-head", children: [
          /* @__PURE__ */ jsxs6("div", { className: "fi-persona-card-id", children: [
            /* @__PURE__ */ jsx7("span", { className: "fi-persona-card-icon", children: /* @__PURE__ */ jsx7(Brain2, { size: 22, "aria-hidden": "true" }) }),
            /* @__PURE__ */ jsxs6("div", { style: { minWidth: 0 }, children: [
              /* @__PURE__ */ jsx7("h3", { className: "fi-persona-card-name", children: persona.name }),
              persona.version !== void 0 ? /* @__PURE__ */ jsxs6("p", { className: "fi-persona-subtitle", children: [
                "v",
                persona.version
              ] }) : null
            ] })
          ] }),
          /* @__PURE__ */ jsxs6("div", { className: "fi-persona-actions", children: [
            /* @__PURE__ */ jsx7(
              AdminButton,
              {
                variant: "ghost",
                iconOnly: true,
                icon: Edit,
                "aria-label": "Editar persona",
                onClick: (e) => {
                  e.stopPropagation();
                  onEdit();
                }
              }
            ),
            onDelete ? /* @__PURE__ */ jsx7(
              AdminButton,
              {
                variant: "ghost",
                iconOnly: true,
                icon: Trash23,
                "aria-label": "Eliminar persona",
                title: "Eliminar persona",
                onClick: (e) => {
                  e.stopPropagation();
                  onDelete();
                }
              }
            ) : null
          ] })
        ] }),
        /* @__PURE__ */ jsx7("p", { className: "fi-persona-card-desc", children: persona.description }),
        /* @__PURE__ */ jsxs6("dl", { className: "fi-persona-card-stats", style: { margin: 0 }, children: [
          /* @__PURE__ */ jsxs6("div", { className: "fi-persona-mini", children: [
            /* @__PURE__ */ jsx7("dt", { children: "Modelo" }),
            /* @__PURE__ */ jsx7("dd", { title: persona.model, children: persona.model })
          ] }),
          hidden.has("voice") ? null : /* @__PURE__ */ jsxs6("div", { className: "fi-persona-mini", children: [
            /* @__PURE__ */ jsx7("dt", { children: "Voz" }),
            /* @__PURE__ */ jsx7("dd", { children: persona.voice || "N/A" })
          ] }),
          hidden.has("temperature") ? null : /* @__PURE__ */ jsxs6("div", { className: "fi-persona-mini", children: [
            /* @__PURE__ */ jsx7("dt", { children: "Temperature" }),
            /* @__PURE__ */ jsx7("dd", { children: persona.temperature.toFixed(2) })
          ] }),
          hidden.has("max_tokens") ? null : /* @__PURE__ */ jsxs6("div", { className: "fi-persona-mini", children: [
            /* @__PURE__ */ jsx7("dt", { children: "Max tokens" }),
            /* @__PURE__ */ jsx7("dd", { children: persona.max_tokens.toLocaleString(locale) })
          ] })
        ] }),
        stats || persona.last_updated ? /* @__PURE__ */ jsxs6("div", { className: "fi-persona-card-foot", children: [
          stats ? /* @__PURE__ */ jsxs6(Fragment3, { children: [
            /* @__PURE__ */ jsxs6("div", { className: "fi-persona-row", children: [
              /* @__PURE__ */ jsx7("span", { children: "Invocaciones" }),
              /* @__PURE__ */ jsx7("b", { children: stats.total_invocations.toLocaleString(locale) })
            ] }),
            /* @__PURE__ */ jsxs6("div", { className: "fi-persona-row", children: [
              /* @__PURE__ */ jsx7("span", { children: "Latencia promedio" }),
              /* @__PURE__ */ jsx7("b", { children: stats.avg_latency_ms > 0 ? `${stats.avg_latency_ms.toFixed(0)}ms` : "N/A" })
            ] }),
            /* @__PURE__ */ jsxs6("div", { className: "fi-persona-row", children: [
              /* @__PURE__ */ jsx7("span", { children: "Costo promedio" }),
              /* @__PURE__ */ jsx7("b", { children: stats.avg_cost_usd > 0 ? `$${stats.avg_cost_usd.toFixed(4)}` : "N/A" })
            ] })
          ] }) : null,
          persona.last_updated ? /* @__PURE__ */ jsxs6("span", { children: [
            "Actualizado: ",
            formatDate(persona.last_updated, locale),
            persona.updated_by ? ` por ${persona.updated_by}` : ""
          ] }) : null
        ] }) : null
      ]
    }
  );
}

// src/persona-admin/usePersonaCollection.ts
import { useCallback as useCallback4, useEffect as useEffect3, useRef as useRef3, useState as useState4 } from "react";
function usePersonaCollection(store, { confirm = defaultPersonaConfirm, deleteConfirmMessage = defaultDeleteConfirmMessage } = {}) {
  const storeRef = useRef3(store);
  storeRef.current = store;
  const [personas, setPersonas] = useState4([]);
  const [loading, setLoading] = useState4(true);
  const [error, setError] = useState4(null);
  const [removeError, setRemoveError] = useState4(null);
  const reload = useCallback4(async () => {
    setLoading(true);
    setError(null);
    try {
      setPersonas(await storeRef.current.list());
    } catch (err) {
      setError(errorMessage(err, "Error al cargar las personas"));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect3(() => {
    void reload();
  }, [reload]);
  const upsert = useCallback4((persona) => {
    setPersonas(
      (prev) => prev.some((p) => p.id === persona.id) ? prev.map((p) => p.id === persona.id ? persona : p) : [...prev, persona]
    );
  }, []);
  const forget = useCallback4((personaId) => {
    setPersonas((prev) => prev.filter((p) => p.id !== personaId));
  }, []);
  const remove = useCallback4(
    async (persona) => {
      if (!await confirm(deleteConfirmMessage(persona))) return false;
      setRemoveError(null);
      try {
        await storeRef.current.remove(persona.id);
        forget(persona.id);
        return true;
      } catch (err) {
        setRemoveError(errorMessage(err, "Error al eliminar la persona"));
        return false;
      }
    },
    [confirm, deleteConfirmMessage, forget]
  );
  return {
    personas,
    loading,
    error,
    reload,
    upsert,
    forget,
    remove,
    removeError,
    clearRemoveError: useCallback4(() => setRemoveError(null), [])
  };
}
export {
  DEFAULT_PERSONA_VALUES,
  FI_PERSONA_ROOT_CLASS,
  PERSONA_FIELD_CONSTRAINTS,
  PERSONA_ID_PATTERN,
  PersonaCard,
  PersonaCreateModal,
  PersonaEditor,
  PersonaExamplesTab,
  PersonaForm,
  PersonaPromptTab,
  PersonaSheet,
  PersonaTestTab,
  defaultDeleteConfirmMessage,
  defaultPersonaConfirm,
  ensurePersonaAdminStyle,
  generateIdFromName,
  mapFormToCreateRequest,
  mapFormToUpdateRequest,
  mapPersonaToFormValues,
  personaCreateSchema,
  personaExampleSchema,
  personaUpdateSchema,
  usePersonaAdminStyle,
  usePersonaCollection,
  validatePersonaCreate,
  validatePersonaUpdate
};
//# sourceMappingURL=index.js.map