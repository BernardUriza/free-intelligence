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

import { useMemo, useState } from 'react';
import { AgentConversationSurface, AgentWorkspaceShell, useAgentConversation } from 'fi-glass/agent';
import { useConversationLibrary, RemoteConversationLibrary } from 'fi-glass/conversation';
import type { Expediente } from '@/lib/useExpedientes';
import { useFenixAgent } from '@/lib/useFenixAgent';
import { authHeaders } from '@/lib/fenixToken';
import { FenixStartScreen } from './FenixStartScreen';
import { FenixSidebar, type Vista } from './FenixSidebar';
import { FenixClientes } from './FenixClientes';
import { FenixVisorExcel, type HojaVista } from './FenixVisorExcel';
import { FenixBarraPresupuesto } from './FenixBarraPresupuesto';
import { FenixEncabezado } from './FenixEncabezado';
import { useExpedientes } from '@/lib/useExpedientes';

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
  const [vista, setVista] = useState<Vista>('chats');
  const exp = useExpedientes();
  // El visor del presupuesto. Se guarda el expediente abierto para poder
  // descargar exactamente lo que se está viendo.
  const [verExcel, setVerExcel] = useState<Expediente | null>(null);
  const [hoja, setHoja] = useState<HojaVista | null>(null);
  const [hojaCargando, setHojaCargando] = useState(false);
  const [hojaError, setHojaError] = useState<string | null>(null);

  const datosDe = (e: Expediente) => ({
    alumno: e.alumno, escuela: e.escuela, grado: e.grado, tutor: e.tutor,
    items: e.items ?? [], forrado: e.forrado ?? [],
    opcionales: e.opcionales ?? [], fuera: e.fuera ?? [],
  });

  // El expediente de la conversación abierta, si ya tiene renglones. Es lo que
  // permite ofrecer el Excel SIN salir del chat donde se cotizó.
  const presupuestoAbierto = exp.expedientes.find(
    (e) => e.conversacionId === lib.activeId && (e.items?.length ?? 0) > 0,
  );
  // El expediente de la conversación abierta, tenga renglones o no: el
  // encabezado debe decir de quién es aunque todavía no se haya cotizado.
  const expedienteAbierto = exp.expedientes.find((e) => e.conversacionId === lib.activeId);
  const tituloAbierto =
    lib.conversations.find((c) => c.id === lib.activeId)?.title ?? null;

  async function abrirVisor(e: Expediente) {
    setVerExcel(e);
    setHoja(null);
    setHojaError(null);
    setHojaCargando(true);
    try {
      setHoja(await exp.vistaExcel(datosDe(e)));
    } catch (err) {
      setHojaError(err instanceof Error ? err.message : String(err));
    } finally {
      setHojaCargando(false);
    }
  }

  return (
    <>
    <AgentWorkspaceShell
      responsive
      toggleLabel="Fénix"
      sidebar={(shell) => (
        <FenixSidebar
          conversations={lib.conversations}
          expedientes={exp.expedientes}
          admin={exp.admin}
          activeId={lib.activeId}
          vista={vista}
          disabled={conversation.isStreaming}
          onVista={setVista}
          onNew={() => {
            setVista('chats');
            lib.newConversation();
            shell.close();
          }}
          onSwitch={(id) => {
            setVista('chats');
            void lib.switchConversation(id).catch((e) => console.error('[fenix] switch failed', e));
            shell.close();
          }}
          onDelete={(id) =>
            void lib.deleteConversation(id).catch((e) => console.error('[fenix] delete failed', e))
          }
        />
      )}
      conversation={
        vista === 'clientes' && exp.admin ? (
          <FenixClientes
            expedientes={exp.expedientes}
            cargando={exp.cargando}
            error={exp.error}
            onGuardar={exp.guardar}
            onExcel={(e) => void abrirVisor(e)}
            onAbrirChat={(id) => {
              setVista('chats');
              void lib.switchConversation(id).catch((e) => console.error('[fenix] switch failed', e));
            }}
          />
        ) : (
        <div className="fx-conv">
          {lib.activeId && (
            <FenixEncabezado titulo={tituloAbierto} expediente={expedienteAbierto} />
          )}
          <AgentConversationSurface
          conversation={{ ...conversation, newConversation: lib.newConversation }}
          composerPlaceholder="Manda la foto de la lista, o pregunta un precio…"
          newChatLabel="Nueva cotización"
          showNewChatButton={false}
          aboveComposer={
            presupuestoAbierto ? (
              <FenixBarraPresupuesto
                expediente={presupuestoAbierto}
                onVer={(e) => void abrirVisor(e)}
              />
            ) : null
          }
          emptyState={<FenixStartScreen onPick={(prompt) => void conversation.send(prompt)} />}
          imageAttachments
          // El textarea ya NO necesita `composerTextareaClassName`: el arreglo
          // subió a fi-glass y el componente aplica su propia clase. Esta línea
          // era el hallazgo H2 y ahora sobra — que es exactamente lo que debía
          // pasar al consolidar en el framework.
          composerBoxClassName="glass-chat-composer"
          />
        </div>
        )
      }
    />
      {verExcel && (
        <FenixVisorExcel
          hoja={hoja}
          cargando={hojaCargando}
          error={hojaError}
          onCerrar={() => setVerExcel(null)}
          onDescargar={() => exp.descargarExcel(datosDe(verExcel))}
        />
      )}
    </>
  );
}
