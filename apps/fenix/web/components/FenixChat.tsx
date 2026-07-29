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
import {
  useConversationLibrary,
  EphemeralConversationLibrary,
  RemoteConversationLibrary,
} from 'fi-glass/conversation';
import { conversationFileName, conversationToMarkdown } from '@free-intelligence/core';
import type { Expediente } from '@/lib/useExpedientes';
import { useFenixAgent } from '@/lib/useFenixAgent';
import { fenixHeaders } from '@/lib/fenixSesion';
import { FenixStartScreen } from './FenixStartScreen';
import { FenixSidebar, type Vista } from './FenixSidebar';
import { FenixClientes } from './FenixClientes';
import { FenixVisorExcel, type HojaVista } from './FenixVisorExcel';
import { FenixBarraPresupuesto } from './FenixBarraPresupuesto';
import { FenixEncabezado } from './FenixEncabezado';
import { FenixGuardarAntesDeIrse } from './FenixGuardarAntesDeIrse';
import { FenixUsuario } from './FenixUsuario';
import { useExpedientes } from '@/lib/useExpedientes';

const FENIX_AUTHOR = { id: 'fenix', name: 'Fénix', symbol: null, engine: null };
const API = process.env.NEXT_PUBLIC_FENIX_API ?? 'http://localhost:8119';

export function FenixChat() {
  const exp = useExpedientes();
  // Dos superficies, dos memorias.
  //
  // En el MOSTRADOR el historial es del NEGOCIO, no del navegador de quien abrió
  // la app. Con IndexedDB las cotizaciones vivían en la máquina donde se
  // escribieron: quien abriera fenix en otro dispositivo veía la papelería
  // vacía, y las 35 sesiones que ya existen en claude.ai no tendrían dónde
  // aterrizar. El store del servidor las hace visibles desde cualquier lado.
  //
  // En las PCs del CIBERCAFÉ guardar es el error, no la funcionalidad: son
  // turnos de veinte minutos en una máquina compartida, y cualquier memoria
  // —servidor o IndexedDB, que es del navegador y no de la persona— le enseña
  // al siguiente niño la conversación del anterior. La librería efímera muere
  // al cerrar la pestaña, que es exactamente la vida útil de esa sesión.
  const library = useMemo(
    () =>
      exp.admin
        ? new RemoteConversationLibrary({
            baseUrl: API,
            // Las dos credenciales, no sólo el bearer: `/conversations` ahora
            // exige el token del mostrador igual que los expedientes.
            headers: fenixHeaders,
          })
        : new EphemeralConversationLibrary(),
    [exp.admin],
  );
  const lib = useConversationLibrary(library);
  const agent = useFenixAgent(lib.activeId, exp.admin);
  const conversation = useAgentConversation(agent, {
    author: FENIX_AUTHOR,
    conversationId: lib.activeId,
    initialMessages: lib.activeMessages,
    onMessagesChange: lib.persist,
  });
  const [vista, setVista] = useState<Vista>('chats');
  const [porGuardar, setPorGuardar] = useState(false);
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

  // En el cibercafé empezar otra conversación BORRA la anterior, así que se
  // ofrece llevársela justo en ese momento. En el mostrador no: ahí el
  // historial vive en el servidor y nada se pierde.
  function nuevaConversacion() {
    if (!exp.admin && conversation.messages.length > 0) {
      setPorGuardar(true);
      return;
    }
    lib.newConversation();
  }

  function descargarConversacion() {
    const registro = {
      id: lib.activeId ?? 'conversacion',
      title: tituloAbierto || 'Conversación',
      createdAt: lib.activeRecord?.createdAt ?? new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      preview: '',
      schemaVersion: 1,
      messages: conversation.messages,
    };
    const texto = conversationToMarkdown(registro, {
      labels: { assistant: 'Fénix' },
      source: 'Computadoras públicas de Servicios Papeleros Fénix',
    });
    const url = URL.createObjectURL(new Blob([texto], { type: 'text/markdown;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = conversationFileName(registro);
    a.click();
    URL.revokeObjectURL(url);
  }

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
      // Sin barra en el cibercafé. No es que estorbe: es la única pieza que
      // sigue prometiendo un historial que ahí no existe — una columna vacía
      // donde el mostrador tiene 33 chats. Sin `sidebar`, el shell tampoco
      // pinta el toggle del drawer (fi-glass lo omite entero).
      sidebar={!exp.admin ? undefined : (shell) => (
        <FenixSidebar
          conversations={lib.conversations}
          expedientes={exp.expedientes}
          admin={exp.admin}
          modoAbierto={exp.modoAbierto}
          correoConocido={exp.correoConocido}
          onSesion={() => void exp.recargar()}
          activeId={lib.activeId}
          vista={vista}
          disabled={conversation.isStreaming}
          onVista={setVista}
          onNew={() => {
            setVista('chats');
            nuevaConversacion();
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
          {/* El encabezado dice de quién es la cotización abierta — dato del
              mostrador. En el cibercafé el título es la propia pregunta del
              niño: no informa nada y ocupa la franja superior del chat. */}
          {exp.admin && lib.activeId && (
            <FenixEncabezado titulo={tituloAbierto} expediente={expedienteAbierto} />
          )}
          <AgentConversationSurface
          conversation={{ ...conversation, newConversation: nuevaConversacion }}
          composerPlaceholder={
            exp.admin
              ? 'Manda la foto de la lista, o pregunta un precio…'
              : 'Pregunta lo que sea de tu tarea…'
          }
          newChatLabel={exp.admin ? 'Nueva cotización' : 'Empezar de nuevo'}
          // Sin barra, la afordancia de empezar otra tiene que vivir en el
          // composer — y fi-glass ya la trae, no hay que inventarla.
          showNewChatButton={!exp.admin}
          aboveComposer={
            presupuestoAbierto ? (
              <FenixBarraPresupuesto
                expediente={presupuestoAbierto}
                onVer={(e) => void abrirVisor(e)}
              />
            ) : null
          }
          emptyState={
            <FenixStartScreen
              admin={exp.admin}
              onPick={(prompt) => void conversation.send(prompt)}
            />
          }
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
      {/* La píldora vive al pie de la barra, y en el cibercafé no hay barra.
          Sin esto, una PC NUEVA del mostrador arranca en público y no tiene
          dónde pegar su token: el callejón sin salida que la barra tapaba.
          Discreta a propósito — quien la necesita la busca una sola vez. */}
      {!exp.admin && (
        <div className="fx-llave-suelta">
          <FenixUsuario
            admin={exp.admin}
            modoAbierto={exp.modoAbierto}
            correoConocido={exp.correoConocido}
            compacto
            onCambio={() => void exp.recargar()}
          />
        </div>
      )}

      {porGuardar && (
        <FenixGuardarAntesDeIrse
          turnos={conversation.messages.length}
          onDescargar={() => {
            descargarConversacion();
            setPorGuardar(false);
            lib.newConversation();
          }}
          onSeguirSinGuardar={() => {
            setPorGuardar(false);
            lib.newConversation();
          }}
          onCancelar={() => setPorGuardar(false)}
        />
      )}

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
