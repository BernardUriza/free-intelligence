"use client";

/**
 * Og118ElementAdmin — og118's elements on fi-glass/persona-admin. og118 adds only
 * what is its own: the empty slot of the periodic table, the aliases, the AIRE
 * engines; the forms, the editor and the mobile sheet are the framework's.
 */

import { useId, useMemo, useRef, useState } from "react";
import { X } from "lucide-react";
import {
  PersonaCard,
  PersonaCreateModal,
  PersonaEditor,
  PersonaSheet,
  usePersonaCollection,
  type PersonaHideableField,
} from "fi-glass/persona-admin";
import { personaIdFor, type Og118EmptySlot } from "../lib/og118Element";
import {
  ELEMENT_ENGINE_OPTIONS,
  createOg118ElementStore,
  splitAliases,
} from "../lib/og118ElementStore";

export type Og118ElementAdminMode = "create" | "manage" | null;

export interface Og118ElementAdminProps {
  mode: Og118ElementAdminMode;
  onClose: () => void;
  slots: Og118EmptySlot[];
  /** After a create, edit or delete; a created element's slug comes along to select it. */
  onChanged: (createdSlug?: string) => void;
}

const HIDDEN: PersonaHideableField[] = [
  "voice",
  "temperature",
  "max_tokens",
  "examples",
];

const deleteMessage = (persona: { name: string }) =>
  `¿Borrar el elemento "${persona.name}"? Su casilla vuelve a quedar vacía.`;

export function Og118ElementAdmin({
  mode,
  onClose,
  slots,
  onChanged,
}: Og118ElementAdminProps) {
  const [atomicNumber, setAtomicNumber] = useState<number | null>(null);
  const [aliases, setAliases] = useState("");
  const slot = slots.find((s) => s.atomicNumber === atomicNumber) ?? slots[0];
  const slotRef = useRef(slot);
  slotRef.current = slot;
  const aliasesRef = useRef(aliases);
  aliasesRef.current = aliases;

  const store = useMemo(
    () =>
      createOg118ElementStore({
        slot: () => slotRef.current,
        aliases: () => splitAliases(aliasesRef.current),
      }),
    [],
  );

  return (
    <>
      {/* Keyed by slot: picking another slot restarts the form on that slot's name and id. */}
      <PersonaCreateModal
        key={slot?.atomicNumber ?? 0}
        open={mode === "create"}
        onOpenChange={(open) => {
          if (!open) {
            setAliases("");
            onClose();
          }
        }}
        store={store}
        onCreated={(persona) => onChanged(persona.id)}
        modelOptions={ELEMENT_ENGINE_OPTIONS}
        hiddenFields={HIDDEN}
        initialValues={
          slot
            ? {
                id: personaIdFor(slot.slug),
                name: slot.displayName,
                model: "claude",
              }
            : { model: "claude" }
        }
        title="Nuevo elemento"
        subtitle="Una casilla vacía de la tabla, con su persona y su motor."
        submitLabel="Crear elemento"
        validateExtra={() =>
          slot ? null : "No quedan casillas vacías en la tabla."
        }
        renderExtraFields={() => (
          <div className="fi-persona-grid">
            <div className="fi-persona-field">
              <label className="fi-persona-label" htmlFor="og-element-slot">
                Casilla<span className="fi-persona-required">*</span>
              </label>
              <select
                id="og-element-slot"
                className="fi-persona-input"
                value={slot?.atomicNumber ?? ""}
                onChange={(e) => setAtomicNumber(Number(e.target.value))}
              >
                {slots.map((s) => (
                  <option key={s.atomicNumber} value={s.atomicNumber}>
                    {`${s.atomicNumber} · ${s.symbol} · ${s.displayName}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="fi-persona-field">
              <label className="fi-persona-label" htmlFor="og-element-aliases">
                Alias (separados por coma)
              </label>
              <input
                id="og-element-aliases"
                className="fi-persona-input"
                value={aliases}
                onChange={(e) => setAliases(e.target.value)}
              />
            </div>
          </div>
        )}
      />
      {mode === "manage" ? (
        <Og118ElementManager
          store={store}
          onClose={onClose}
          onChanged={() => onChanged()}
        />
      ) : null}
    </>
  );
}

function Og118ElementManager({
  store,
  onClose,
  onChanged,
}: {
  store: ReturnType<typeof createOg118ElementStore>;
  onClose: () => void;
  onChanged: () => void;
}) {
  const titleId = useId();
  const collection = usePersonaCollection(store, {
    deleteConfirmMessage: deleteMessage,
  });
  const [editingId, setEditingId] = useState<string | null>(null);

  return (
    <>
      <PersonaSheet
        onDismiss={onClose}
        labelledBy={titleId}
        placement="side"
        header={
          <div className="fi-persona-row">
            <h2 id={titleId} className="fi-persona-title">
              Tus elementos
            </h2>
            <button
              type="button"
              className="fi-persona-btn fi-touch-target"
              data-variant="ghost"
              data-icon-only=""
              aria-label="Cerrar"
              onClick={onClose}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        }
      >
        <div className="fi-persona-stack">
          {collection.error ? (
            <p className="fi-persona-alert" role="alert">
              {collection.error}
            </p>
          ) : null}
          {collection.removeError ? (
            <p className="fi-persona-alert" role="alert">
              {collection.removeError}
            </p>
          ) : null}
          {!collection.loading &&
          !collection.error &&
          collection.personas.length === 0 ? (
            <p className="fi-persona-empty">
              Todavía no creas elementos desde la app.
            </p>
          ) : null}
          {collection.personas.map((persona) => (
            <PersonaCard
              key={persona.id}
              persona={persona}
              hiddenFields={HIDDEN}
              onEdit={() => setEditingId(persona.id)}
              onDelete={() =>
                void collection.remove(persona).then((removed) => {
                  if (removed) onChanged();
                })
              }
            />
          ))}
        </div>
      </PersonaSheet>
      {editingId ? (
        <PersonaEditor
          personaId={editingId}
          open
          onClose={() => setEditingId(null)}
          onSaved={(persona) => {
            collection.upsert(persona);
            onChanged();
          }}
          onDeleted={(id) => {
            collection.forget(id);
            setEditingId(null);
            onChanged();
          }}
          deleteConfirmMessage={deleteMessage}
          store={store}
          modelOptions={ELEMENT_ENGINE_OPTIONS}
          hiddenFields={HIDDEN}
        />
      ) : null}
    </>
  );
}
