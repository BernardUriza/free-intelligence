"use client";

/**
 * og118's PersonaStore for fi-glass/persona-admin: an element born from the UI is
 * a persona whose id is its slug. The slot and the aliases come from the create
 * sheet's extra fields; the engine travels as the persona's `model`.
 */

import type {
  Persona,
  PersonaCreateRequest,
  PersonaOption,
  PersonaStore,
  PersonaTestResponse,
  PersonaUpdateRequest,
} from "fi-glass/persona-admin";
import {
  ELEMENT_ENGINES,
  type ElementEngineId,
  type Og118Element,
  type Og118EmptySlot,
} from "./og118Element";
import { authHeaders } from "./og118Token";

const API = process.env.NEXT_PUBLIC_OG118_API ?? "http://localhost:8118";

export const ELEMENT_ENGINE_OPTIONS: PersonaOption[] = ELEMENT_ENGINES.map(
  (e) => ({ value: e.id, label: e.label }),
);

export interface ElementPersonaRead {
  slug: string;
  displayName: string;
  description: string | null;
  aliases: string[];
  provider: string | null;
  model: string | null;
  dna: string;
  version?: number | null;
}

export interface ElementCreateContext {
  slot: () => Og118EmptySlot | undefined;
  aliases: () => string[];
}

function engineFor(id: string) {
  return ELEMENT_ENGINES.find((e) => e.id === id) ?? ELEMENT_ENGINES[0];
}

export function engineIdOf(
  provider: string | null | undefined,
): ElementEngineId {
  return (
    ELEMENT_ENGINES.find((e) => e.provider === provider)?.id ??
    ELEMENT_ENGINES[0].id
  );
}

export function splitAliases(text: string): string[] {
  return text
    .split(",")
    .map((a) => a.trim())
    .filter(Boolean);
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = body?.detail;
    const text =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((d) => d?.msg)
              .filter(Boolean)
              .join("; ")
          : "";
    throw new Error(text || `HTTP ${res.status}`);
  }
  return body as T;
}

function toPersona(read: ElementPersonaRead): Persona {
  return {
    id: read.slug,
    name: read.displayName,
    description: read.description ?? "",
    system_prompt: read.dna,
    model: engineIdOf(read.provider),
    temperature: 0.7,
    max_tokens: 2048,
    examples: [],
    version: read.version ?? undefined,
  };
}

function cardFrom(el: Og118Element): Persona {
  return {
    id: el.slug,
    name: el.displayName,
    description: el.description ?? "",
    system_prompt: "",
    model: el.engine ?? "",
    temperature: 0.7,
    max_tokens: 2048,
    examples: [],
  };
}

export function createOg118ElementStore(
  context: ElementCreateContext,
): PersonaStore {
  const reads = new Map<string, ElementPersonaRead>();

  const get = async (slug: string): Promise<Persona> => {
    const read = await call<ElementPersonaRead>(
      `/elements/${encodeURIComponent(slug)}/persona`,
    );
    reads.set(slug, read);
    return toPersona(read);
  };

  return {
    async list() {
      const [{ editable = [] }, { elements = [] }] = await Promise.all([
        call<{ editable?: string[] }>("/elements/slots"),
        call<{ elements?: Og118Element[] }>("/elements"),
      ]);
      const mine = new Set(editable);
      return elements.filter((e) => mine.has(e.slug)).map(cardFrom);
    },
    get,
    async create(req: PersonaCreateRequest) {
      const slot = context.slot();
      if (!slot) throw new Error("Elige una casilla vacía.");
      const engine = engineFor(req.model ?? "");
      await call("/elements", {
        method: "POST",
        body: JSON.stringify({
          atomicNumber: slot.atomicNumber,
          displayName: req.name,
          personaId: req.id,
          description: req.description || null,
          aliases: context.aliases(),
          provider: engine.provider,
          model: engine.model,
          dna: req.system_prompt,
        }),
      });
      return get(slot.slug);
    },
    async update(slug: string, req: PersonaUpdateRequest) {
      if (!reads.has(slug)) await get(slug);
      const current = reads.get(slug)!;
      const engine = req.model
        ? engineFor(req.model)
        : engineFor(engineIdOf(current.provider));
      await call(`/elements/${encodeURIComponent(slug)}`, {
        method: "PUT",
        body: JSON.stringify({
          displayName: req.name ?? current.displayName,
          description: req.description ?? current.description,
          aliases: current.aliases,
          provider: engine.provider,
          model: engine.model,
          dna: req.system_prompt ?? current.dna,
        }),
      });
      return get(slug);
    },
    async remove(slug: string) {
      await call(`/elements/${encodeURIComponent(slug)}`, { method: "DELETE" });
      reads.delete(slug);
    },
    async test(slug: string, input: string): Promise<PersonaTestResponse> {
      const r = await call<{ output: string; latency_ms: number }>(
        `/elements/${encodeURIComponent(slug)}/test`,
        {
          method: "POST",
          body: JSON.stringify({ input }),
        },
      );
      return { output: r.output, latency_ms: r.latency_ms };
    },
  };
}
