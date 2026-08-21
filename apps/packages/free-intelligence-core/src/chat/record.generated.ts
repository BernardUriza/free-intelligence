/* eslint-disable */
/**
 * DO NOT EDIT — generado desde contracts/conversation-record.schema.json
 *
 * El schema es LA FUENTE. Este archivo, el Swift de og118-ios y el modelo del
 * servidor derivan de él; ninguno manda sobre los otros. Correr:
 *   pnpm --filter @free-intelligence/core gen:record-types
 */

/**
 * El registro persistido de una conversación. ESTE ARCHIVO ES LA FUENTE: TypeScript, Swift y el modelo del servidor se derivan de aquí, ninguno manda sobre los otros. Escrito a mano a propósito — un contrato que vive como tipos de UN lenguaje obliga a los demás consumers a transcribirlo, y cada transcripción diverge: tipar `author` como string en vez del objeto canónico dejó toda conversación de la web vacía en el iPhone, y no modelar `images` hizo que guardar desde el teléfono las borrara.
 */
export interface ConversationRecord {
  /**
   * Id estable. Es también el session_id del hilo en el backend.
   */
  id: string;
  /**
   * Derivado del primer mensaje del usuario, salvo que titleCustom sea true.
   */
  title: string;
  /**
   * True cuando el usuario renombró. Un título custom NUNCA se re-deriva al persistir.
   */
  titleCustom?: boolean;
  /**
   * ISO 8601.
   */
  createdAt: string;
  /**
   * ISO 8601 del último cambio.
   */
  updatedAt: string;
  messages: PersistedMessage[];
  /**
   * Fragmento del último mensaje no vacío, para el sidebar.
   */
  preview: string;
  /**
   * ISO 8601. Ausente = no fijado. Timestamp y no booleano para que la sección ordene por último-fijado sin un contador aparte.
   */
  pinnedAt?: string;
  /**
   * ISO 8601. Ausente = activo.
   */
  archivedAt?: string;
  /**
   * Versión del registro, para migraciones hacia adelante.
   */
  schemaVersion: number;
}
/**
 * Un mensaje TAL COMO SE GUARDA. No es el ChatMessage vivo: `sanitizeConversationMessage` descarta `metadata`, `id` y `thinking` a propósito, así que este contrato tampoco los declara. Lo que sí sobrevive —autoría, imágenes, trace— sobrevive porque es contenido que el usuario vería desaparecer.
 */
export interface PersistedMessage {
  /**
   * De qué lado del hilo está el mensaje.
   */
  role: 'user' | 'assistant';
  /**
   * El texto. Puede ir vacío en un mensaje que sólo lleva imagen.
   */
  content: string;
  /**
   * ISO 8601.
   */
  timestamp?: string;
  author?: MessageAuthor;
  images?: MessageImage[];
  trace?: MessageTrace;
}
/**
 * QUIÉN habló — el hablante nombrado, no sólo el lado. Una burbuja de asistente sin autor atribuye la respuesta a la app misma, y eso es una mentira que el framework no debe poder expresar. Sólo `id` y `name` son load-bearing.
 */
export interface MessageAuthor {
  /**
   * Identificador estable del hablante (id de elemento, de persona, 'user').
   */
  id: string;
  /**
   * Nombre humano que se pinta ('Yodo', 'og118', 'Tú').
   */
  name: string;
  /**
   * Enriquecimiento opcional: token de avatar.
   */
  symbol?: string;
  /**
   * Enriquecimiento opcional: chip de procedencia.
   */
  engine?: string;
}
/**
 * Una imagen adjunta a un mensaje del usuario. Base64 por diseño: los shells son local-first, así que los bytes viajan dentro del mensaje en vez de referenciar un blob store que nadie corre.
 */
export interface MessageImage {
  /**
   * MIME de los bytes, p. ej. image/jpeg.
   */
  mediaType: string;
  /**
   * Bytes en base64 — SIN el prefijo data: URL.
   */
  data: string;
}
/**
 * La foto glass-box del turno agéntico ya terminado. El diferenciador es 'ver la ejecución, no sólo el resultado': sin esto, recargar una conversación pierde el plan y las herramientas que el turno vivo sí mostró. Todo es opcional — un turno conversacional simple dobla sin trace.
 */
export interface MessageTrace {
  plan?: AgentPlan;
  tools?: ToolCall[];
  sources?: string[];
  /**
   * El modelo que DE VERDAD produjo la respuesta. Vive aquí y no en metadata, que la persistencia descarta por diseño.
   */
  model?: string;
}
export interface AgentPlan {
  steps: PlanStep[];
  /**
   * Veredicto terminal del plan completo.
   */
  outcome?: 'completed' | 'failed' | 'cancelled';
}
export interface PlanStep {
  label: string;
  status: 'pending' | 'running' | 'done' | 'failed' | 'cancelled';
  summary?: string;
  error?: string;
  /**
   * Anotación libre de note_step.
   */
  note?: string;
}
export interface ToolCall {
  /**
   * Id estable del proveedor; ausente mientras está pendiente.
   */
  id?: string;
  /**
   * Identificador de la herramienta como la nombró el agente.
   */
  name: string;
  /**
   * Servidor/namespace de origen; ausente en las builtin.
   */
  server?: string;
  /**
   * Ausente = pendiente, false = ok, true = falló.
   */
  isError?: boolean;
}
