'use client';

/**
 * Las tres cosas que la papelería REALMENTE hace, medidas el 27-jul sobre 33
 * sesiones Cowork + 17 chats:
 *   1. Cotizar una lista escolar — 41% de los turnos traen foto.
 *   2. Consultar un precio suelto — el turno mediano son 74 caracteres.
 *   3. Hacer un documento (contratos, escritos, etiquetas) — 8 de 17 chats, y
 *      TODOS ocurrían fuera del proyecto porque el asistente sólo sabía
 *      cotizar. Aquí es un botón de primera clase.
 */

import Image from 'next/image';
import { FileImage, FileText, Search } from 'lucide-react';

const ACCIONES = [
  {
    icon: FileImage,
    titulo: 'Cotizar una lista',
    ayuda: 'Manda la foto y te regreso el presupuesto con descuento',
    prompt: 'Voy a mandarte la foto de una lista de útiles para cotizar.',
  },
  {
    icon: Search,
    titulo: 'Consultar un precio',
    ayuda: 'De la lista maestra, sin descuento',
    prompt: 'Dame el precio de lista (sin descuento) de: ',
  },
  {
    icon: FileText,
    titulo: 'Hacer un documento',
    ayuda: 'Contrato, escrito o etiquetas en Word',
    prompt: 'Necesito hacer un documento en Word. Te paso las fotos del original.',
  },
];

export function FenixStartScreen({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="fx-inicio">
      <Image
        className="fx-inicio-logo"
        src="/branding/logo-full.png"
        alt="Fénix — Papelería · Cotizaciones"
        width={420}
        height={235}
        priority
      />
      <p className="fx-inicio-sub">
        Los precios salen siempre de la lista maestra. Nunca de internet.
      </p>
      <div className="fx-inicio-grid">
        {ACCIONES.map(({ icon: Icon, titulo, ayuda, prompt }) => (
          <button
            key={titulo}
            type="button"
            className="fx-accion fi-touch-target"
            onClick={() => onPick(prompt)}
          >
            <span className="fx-accion-ico" aria-hidden>
              <Icon />
            </span>
            <span className="fx-accion-titulo">{titulo}</span>
            <span className="fx-accion-ayuda">{ayuda}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
