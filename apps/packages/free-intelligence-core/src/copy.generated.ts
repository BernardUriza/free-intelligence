// DO NOT EDIT — generado desde contracts/copy.json (pnpm gen:copy).
//
// Las frases que el substrato posee. Swift deriva del mismo contrato
// (Copy.generated.swift); ninguna superficie manda sobre la otra.

export const COPY = {
  /** Título de un hilo sin mensaje de usuario usable (deriveConversationTitle). */
  conversationDefaultTitle: 'New chat',
  /** Aviso (no error) de un turno diferido: el motor sigue trabajando tras cerrar el stream. */
  turnDeferredNotice: (author: string): string => '{author} sigue escribiendo. Su respuesta aparecerá aquí en cuanto termine.'.replace('{author}', author),
  /** El aviso cuando la relectura acotada del hilo se agotó sin que llegara la respuesta diferida. */
  turnDeferredTimeout: 'La respuesta tardó más de lo normal. Vuelve a abrir este chat para verla.',
  /** Falla genérica del transporte o del motor, cuando no trae mensaje propio. */
  turnFailed: 'La respuesta falló. Intenta de nuevo.',
  /** El watchdog de inactividad cerró el turno. */
  turnTimeout: 'La respuesta tardó demasiado. Intenta de nuevo.',
  /** El turno cerró sin texto, sin reacción y sin deferred: el silencio es una falla. */
  turnEmpty: 'La respuesta llegó vacía. Intenta de nuevo.',
} as const;
