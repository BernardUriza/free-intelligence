'use client';

/**
 * Og118ElementCreateDialog — a new element from the UI, with no deploy
 * (OG118-ELEMENTOS-ALTA). The author picks an empty slot, names it, chooses the
 * engine and pastes (or loads) the persona's DNA; the server writes the persona to
 * the engine and the slot to the catalog in one call. On mobile it is a full sheet.
 */

import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from 'react';
import {
  ELEMENT_ENGINES,
  personaIdFor,
  type ElementEngineId,
  type Og118ElementDraft,
  type Og118EmptySlot,
} from '../lib/og118Element';

export interface Og118ElementCreateDialogProps {
  open: boolean;
  slots: Og118EmptySlot[];
  onClose: () => void;
  onCreate: (draft: Og118ElementDraft) => Promise<string>;
}

const FIELD =
  'w-full rounded-lg border border-slate-600 bg-slate-900/80 px-3 py-2 text-base text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 md:text-sm';
const LABEL = 'text-xs font-semibold uppercase tracking-wide text-slate-400';
const BUTTON = 'fi-touch-target min-h-[44px] rounded-lg px-4 text-sm font-semibold transition-colors';

export function Og118ElementCreateDialog({ open, slots, onClose, onCreate }: Og118ElementCreateDialogProps) {
  const titleId = useId();
  const firstField = useRef<HTMLSelectElement>(null);
  const [atomicNumber, setAtomicNumber] = useState<number>(0);
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [aliases, setAliases] = useState('');
  const [engine, setEngine] = useState<ElementEngineId>('claude');
  const [dna, setDna] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const slot = useMemo(() => slots.find((s) => s.atomicNumber === atomicNumber), [slots, atomicNumber]);

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (!slots.some((s) => s.atomicNumber === atomicNumber) && slots[0]) {
      setAtomicNumber(slots[0].atomicNumber);
      setDisplayName(slots[0].displayName);
    }
    firstField.current?.focus();
  }, [open, slots, atomicNumber]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !saving) onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, saving, onClose]);

  if (!open) return null;

  const pickSlot = (z: number) => {
    const next = slots.find((s) => s.atomicNumber === z);
    setAtomicNumber(z);
    if (next) setDisplayName(next.displayName);
  };

  const loadFile = async (file: File | undefined) => {
    if (file) setDna(await file.text());
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!slot || !dna.trim() || !displayName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onCreate({
        atomicNumber: slot.atomicNumber,
        displayName: displayName.trim(),
        personaId: personaIdFor(slot.slug),
        description: description.trim(),
        aliases: aliases.split(',').map((a) => a.trim()).filter(Boolean),
        engine,
        dna,
      });
      setDna('');
      setDescription('');
      setAliases('');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="og-element-create fixed inset-0 z-50 flex items-end justify-center bg-black/60 md:items-center">
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onSubmit={submit}
        className="flex max-h-[100dvh] w-full flex-col gap-3 overflow-y-auto border-slate-700 bg-slate-950 px-3 pt-4 pb-[max(1rem,env(safe-area-inset-bottom))] md:max-h-[90vh] md:w-[560px] md:rounded-2xl md:border md:px-5"
      >
        <h2 id={titleId} className="text-base font-semibold text-slate-100">
          Nuevo elemento
        </h2>
        {slots.length === 0 ? (
          <p className="text-sm text-slate-300">No quedan casillas vacías en la tabla.</p>
        ) : (
          <>
            <label className="flex flex-col gap-1">
              <span className={LABEL}>Casilla</span>
              <select
                ref={firstField}
                className={FIELD}
                value={atomicNumber}
                onChange={(e) => pickSlot(Number(e.target.value))}
              >
                {slots.map((s) => (
                  <option key={s.atomicNumber} value={s.atomicNumber}>
                    {`${s.atomicNumber} · ${s.symbol} · ${s.displayName}`}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className={LABEL}>Nombre</span>
              <input className={FIELD} value={displayName} maxLength={80} onChange={(e) => setDisplayName(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={LABEL}>Descripción (una línea, la ve el selector)</span>
              <input className={FIELD} value={description} maxLength={300} onChange={(e) => setDescription(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={LABEL}>Alias (separados por coma)</span>
              <input className={FIELD} value={aliases} onChange={(e) => setAliases(e.target.value)} />
            </label>
            <fieldset className="flex flex-col gap-1">
              <legend className={LABEL}>Motor</legend>
              <div className="flex flex-wrap gap-2">
                {ELEMENT_ENGINES.map((opt) => (
                  <label
                    key={opt.id}
                    className={`fi-touch-target flex min-h-[44px] cursor-pointer items-center gap-2 rounded-lg border px-3 text-sm ${
                      engine === opt.id ? 'border-emerald-400/60 bg-emerald-500/10 text-emerald-100' : 'border-slate-600 text-slate-200'
                    }`}
                  >
                    <input
                      type="radio"
                      name="element-engine"
                      value={opt.id}
                      checked={engine === opt.id}
                      onChange={() => setEngine(opt.id)}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="flex flex-col gap-1">
              <span className={LABEL}>Persona (el prompt completo)</span>
              <textarea
                className={`${FIELD} min-h-[180px] font-mono text-sm`}
                value={dna}
                onChange={(e) => setDna(e.target.value)}
                placeholder="Eres …"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className={LABEL}>…o cárgala de un archivo .md</span>
              <input
                type="file"
                accept=".md,.txt,text/markdown,text/plain"
                className="text-sm text-slate-300"
                onChange={(e) => void loadFile(e.target.files?.[0])}
              />
            </label>
          </>
        )}
        {error ? (
          <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className={`${BUTTON} text-slate-300 hover:bg-white/5`} onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button
            type="submit"
            className={`${BUTTON} bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50`}
            disabled={saving || !slot || !dna.trim() || !displayName.trim()}
          >
            {saving ? 'Creando…' : 'Crear elemento'}
          </button>
        </div>
      </form>
    </div>
  );
}
