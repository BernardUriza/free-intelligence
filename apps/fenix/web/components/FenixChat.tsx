'use client';

/**
 * FenixChat — el shell de fenix.
 *
 * La tesis de producto contra og118: UN SOLO LUGAR, sin laberinto. og118 le pide
 * al usuario elegir proyecto, elemento, persona y conversación antes de trabajar;
 * la auditoría del 27-jul mostró que ese laberinto es real (35 sesiones Cowork +
 * 17 chats sueltos, 8 de ellos fuera del proyecto porque nadie supo dónde iban).
 * fenix precarga el corpus, no ofrece selector de persona y arranca con las tres
 * cosas que la papelería de verdad hace.
 *
 * Lo que fenix NO escribe (lo hereda de fi-glass): transcript visible, mensaje
 * optimista del usuario, fold del turno del asistente, AgentPanel en vivo,
 * persistencia en IndexedDB, adjuntar imágenes, y el drawer responsive. Ése es
 * el experimento: medir cuánto queda para el consumer cuando el framework hace
 * su trabajo. Ver .claude/EXPERIMENTO.md.
 */

import { useMemo } from 'react';
import { AgentConversationSurface, AgentWorkspaceShell, useAgentConversation } from 'fi-glass/agent';
import { useConversationLibrary, RemoteConversationLibrary } from 'fi-glass/conversation';
import { useFenixAgent } from '@/lib/useFenixAgent';
import { authHeaders } from '@/lib/fenixToken';
import { FenixStartScreen } from './FenixStartScreen';
import { FenixSidebar } from './FenixSidebar';

const FENIX_AUTHOR = { id: 'fenix', name: 'Fénix', symbol: null, engine: null };
const API = process.env.NEXT_PUBLIC_FENIX_API ?? 'http://localhost:8119';

export function FenixChat() {
  // El historial es del NEGOCIO, no del navegador de quien abrió la app. Con
  // IndexedDB, las cotizaciones vivían en la máquina donde se escribieron: quien
  // abriera fenix en otro dispositivo veía la papelería vacía, y las 35 sesiones
  // que ya existen en claude.ai no tendrían dónde aterrizar. El store del
  // servidor las hace visibles desde cualquier lado y migrables de una vez.
  const library = useMemo(
    () => new RemoteConversationLibrary({ baseUrl: API, headers: authHeaders }),
    [],
  );
  const lib = useConversationLibrary(library);
  const agent = useFenixAgent(lib.activeId);
  const conversation = useAgentConversation(agent, {
    author: FENIX_AUTHOR,
    conversationId: lib.activeId,
    initialMessages: lib.activeMessages,
    onMessagesChange: lib.persist,
  });

  return (
    <AgentWorkspaceShell
      responsive
      toggleLabel="Cotizaciones"
      sidebar={(shell) => (
        <FenixSidebar
          conversations={lib.conversations}
          activeId={lib.activeId}
          disabled={conversation.isStreaming}
          onNew={() => {
            lib.newConversation();
            shell.close();
          }}
          onSwitch={(id) => {
            void lib.switchConversation(id).catch((e) => console.error('[fenix] switch failed', e));
            shell.close();
          }}
          onDelete={(id) =>
            void lib.deleteConversation(id).catch((e) => console.error('[fenix] delete failed', e))
          }
          onRename={(id, title) =>
            void lib.renameConversation(id, title).catch((e) => console.error('[fenix] rename failed', e))
          }
        />
      )}
      conversation={
        <AgentConversationSurface
          conversation={{ ...conversation, newConversation: lib.newConversation }}
          composerPlaceholder="Manda la foto de la lista, o pregunta un precio…"
          newChatLabel="Nueva cotización"
          showNewChatButton={false}
          emptyState={<FenixStartScreen onPick={(prompt) => void conversation.send(prompt)} />}
          imageAttachments
          // HALLAZGO-4: fi-glass TRAE los estilos del composer (.glass-chat-composer,
          // .glass-chat-composer-input) pero NO se los aplica solo — son opt-in vía
          // estas props. Un consumer que no lo sepa renderiza un textarea blanco con
          // texto blanco: invisible. El default del framework es "roto"; lo correcto
          // sólo se descubre leyendo Og118AgentChat.tsx:342 y :375.
          composerBoxClassName="glass-chat-composer"
          composerTextareaClassName="glass-chat-composer-input"
        />
      }
    />
  );
}
