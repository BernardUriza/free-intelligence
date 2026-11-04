// DO NOT EDIT — generado desde contracts/copy.json
//
// El contrato es LA FUENTE, escrita a mano. core (copy.generated.ts) y este
// archivo derivan de él; ninguna superficie manda sobre la otra. El aviso de
// `deferred` se transcribió a mano el día que nació: así es como una frase
// termina diciendo dos cosas distintas en la web y en el teléfono.
//
//   pnpm --filter @free-intelligence/core gen:swift-copy
//   pnpm --filter @free-intelligence/core check:swift-copy

import Foundation

enum Copy {
    /// Título de un hilo sin mensaje de usuario usable (deriveConversationTitle).
    static let conversationDefaultTitle = "New chat"

    /// Aviso (no error) de un turno diferido: el motor sigue trabajando tras cerrar el stream.
    static func turnDeferredNotice(author: String) -> String {
        "\(author) sigue escribiendo. Su respuesta aparecerá aquí en cuanto termine."
    }

    /// El aviso cuando la relectura acotada del hilo se agotó sin que llegara la respuesta diferida.
    static let turnDeferredTimeout = "La respuesta tardó más de lo normal. Vuelve a abrir este chat para verla."

    /// Falla genérica del transporte o del motor, cuando no trae mensaje propio.
    static let turnFailed = "La respuesta falló. Intenta de nuevo."

    /// El watchdog de inactividad cerró el turno.
    static let turnTimeout = "La respuesta tardó demasiado. Intenta de nuevo."

    /// El turno cerró sin texto, sin reacción y sin deferred: el silencio es una falla.
    static let turnEmpty = "La respuesta llegó vacía. Intenta de nuevo."
}
