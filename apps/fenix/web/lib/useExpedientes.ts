'use client';

import { useCallback, useEffect, useState } from 'react';
import { fenixHeaders } from './fenixSesion';

const API = process.env.NEXT_PUBLIC_FENIX_API ?? 'http://localhost:8119';

export type EstadoExpediente = 'nueva' | 'cotizando' | 'bloqueada' | 'entregada' | 'cerrada';

export interface RenglonExpediente {
  descripcion: string;
  cantidad: number;
  precio: number;
}

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
  descuento: number;
  totalDeclarado: number | null;
  desgloseIncompleto: boolean;
  items: RenglonExpediente[];
  forrado: RenglonExpediente[];
  opcionales: RenglonExpediente[];
  fuera: string[];
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
  // El rol decide qué superficie existe. Se pregunta al servidor y no se
  // adivina en el cliente: ocultar un botón no protege un dato, la puerta está
  // en la API. Esto sólo evita pintar una vista que respondería 404.
  const [admin, setAdmin] = useState(false);
  const [modoAbierto, setModoAbierto] = useState(false);
  const [correoConocido, setCorreoConocido] = useState(true);

  const recargar = useCallback(async () => {
    try {
      const rol = await fetch(`${API}/expedientes/rol`, { headers: fenixHeaders() });
      const datos = rol.ok ? await rol.json() : { admin: false };
      const esAdmin = Boolean(datos.admin);
      setAdmin(esAdmin);
      setModoAbierto(Boolean(datos.modoAbierto));
      setCorreoConocido(datos.correoConocido !== false);
      if (!esAdmin) {
        setExpedientes([]);
        setError(null);
        return;
      }
      const r = await fetch(`${API}/expedientes`, { headers: fenixHeaders() });
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
        headers: { 'Content-Type': 'application/json', ...fenixHeaders() },
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

  /**
   * Descarga el presupuesto en .xlsx.
   *
   * Lo genera el SERVIDOR: al modelo se le bloquea Bash/Write por seguridad
   * (ToolPolicy.companion) y, verificado en runtime, ante "genera el Excel"
   * termina entregando una tabla en el chat — que no es lo que se manda por
   * WhatsApp. El modelo pone los datos; el formato lo pone la plantilla.
   */
  const descargarExcel = useCallback(async (datos: Record<string, unknown>) => {
    const r = await fetch(`${API}/expedientes/excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...fenixHeaders() },
      body: JSON.stringify(datos),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const blob = await r.blob();
    const nombre =
      r.headers.get('Content-Disposition')?.match(/filename="(.+?)"/)?.[1] ?? 'Presupuesto.xlsx';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    a.click();
    URL.revokeObjectURL(url);
    return nombre;
  }, []);

  /** La hoja parseada del MISMO archivo que se descarga, para el visor. */
  const vistaExcel = useCallback(async (datos: Record<string, unknown>) => {
    const r = await fetch(`${API}/expedientes/excel/vista`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...fenixHeaders() },
      body: JSON.stringify(datos),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }, []);

  return { expedientes, admin, modoAbierto, correoConocido, cargando, error, guardar, recargar, descargarExcel, vistaExcel };
}
