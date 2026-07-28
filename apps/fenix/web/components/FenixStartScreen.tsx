'use client';

/**
 * Las tres cosas que la papelería REALMENTE hace, medidas el 27-jul sobre 35
 * sesiones Cowork + 17 chats:
 *   1. Cotizar una lista escolar — 41% de los turnos traen foto.
 *   2. Consultar un precio suelto — el turno mediano son 74 caracteres.
 *   3. Hacer un documento (contratos de arrendamiento, escritos, etiquetas) —
 *      8 de 17 chats, y TODOS ocurrían fuera del proyecto porque el asistente
 *      sólo sabía cotizar. Aquí es un botón de primera clase.
 */

import { FileImage, Search, FileText } from 'lucide-react';

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
    <div className="fenix-start">
      <h1 className="fenix-start-title">Papelería Fénix</h1>
      <p className="fenix-start-sub">
        Los precios salen siempre de la lista maestra. Nunca de internet.
      </p>
      <div className="fenix-start-grid">
        {ACCIONES.map(({ icon: Icon, titulo, ayuda, prompt }) => (
          <button
            key={titulo}
            type="button"
            className="fenix-start-card fi-touch-target"
            onClick={() => onPick(prompt)}
          >
            <Icon aria-hidden className="fenix-start-icon" />
            <span className="fenix-start-card-title">{titulo}</span>
            <span className="fenix-start-card-help">{ayuda}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
