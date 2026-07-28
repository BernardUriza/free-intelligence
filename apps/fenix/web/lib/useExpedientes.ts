'use client';

import { useCallback, useEffect, useState } from 'react';
import { authHeaders } from './fenixToken';

const API = process.env.NEXT_PUBLIC_FENIX_API ?? 'http://localhost:8119';

export type EstadoExpediente = 'nueva' | 'cotizando' | 'bloqueada' | 'entregada' | 'cerrada';

export interface Expediente {
  id: string;
  conversacionId: string | null;
  alumno: string;
  escuela: string;
  grado: string;
  tutor: string;
  whatsapp: string;
  folio: string;
  estado: EstadoExpediente;
  total: number | null;
  notas: string;
  creado: string;
  actualizado: string;
}

/** Qué le falta a este expediente para poder entregarlo. */
export function pendientes(e: Expediente): string[] {
  const f: string[] = [];
  if (!e.alumno.trim()) f.push('nombre');
  if (!e.whatsapp.trim()) f.push('WhatsApp');
  if (!e.escuela.trim()) f.push('escuela');
  return f;
}

export function useExpedientes() {
  const [expedientes, setExpedientes] = useState<Expediente[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const recargar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/expedientes`, { headers: authHeaders() });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      setExpedientes(j.expedientes ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  const guardar = useCallback(
    async (datos: Partial<Expediente>) => {
      const r = await fetch(`${API}/expedientes`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(datos),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      // Se relee del servidor en vez de parchear el estado local: el servidor
      // normaliza (recorta espacios, valida el estado, sella `actualizado`), y
      // mostrar el borrador local haría creer que se guardó algo que no es.
      await recargar();
      return (await r.json()) as Expediente;
    },
    [recargar],
  );

  return { expedientes, cargando, error, guardar, recargar };
}
