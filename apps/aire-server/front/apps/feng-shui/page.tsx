import Link from "next/link";
import { ask, init } from "../aire.ts";
import { PERSONA } from "./persona.ts";

export const dynamic = "force-dynamic";

/**
 * El Maestro — a canary consumer of AIRE: a Feng Shui sage that arranges your
 * furniture and DRAWS the layouts. The LLM returns SVG floor plans (like the
 * monster, SVG is server-rendered markup — NO client JS). The persona lives in
 * the casita (set once via `init`), so each turn sends only the room's details.
 */

const TYPES = ["recámara", "sala", "oficina", "comedor"];
const PROJECT = "canary-feng";
const SESSION = "maestro";

/** Strip anything executable before we inline the LLM's SVG server-side. */
function safeSvg(svg: string): string {
  return svg
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<foreignObject[\s\S]*?<\/foreignObject>/gi, "")
    .replace(/\son\w+="[^"]*"/gi, "");
}

/** Split the reply into prose + SVG segments, in order. */
function segments(text: string): { svg: boolean; content: string }[] {
  const out: { svg: boolean; content: string }[] = [];
  const re = /<svg[\s\S]*?<\/svg>/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push({ svg: false, content: text.slice(last, m.index).trim() });
    out.push({ svg: true, content: safeSvg(m[0]) });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ svg: false, content: text.slice(last).trim() });
  return out.filter((s) => s.content);
}

async function Plans({ room }: { room: string }) {
  let segs: { svg: boolean; content: string }[] = [];
  let cost: number | null = null;
  let error = "";
  try {
    await init(PROJECT, PERSONA);
    const turn = await ask(PROJECT, SESSION, room);
    segs = segments(turn.text);
    cost = turn.costUsd;
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }
  if (error) return <p className="wrong">El maestro no respondió: {error}</p>;
  return (
    <div className="result">
      {segs.map((s, i) =>
        s.svg ? (
          <div key={i} className="plano" dangerouslySetInnerHTML={{ __html: s.content }} />
        ) : (
          <pre key={i}>{s.content}</pre>
        ),
      )}
      <p className="sub">
        {cost != null ? `costo del turno: $${cost.toFixed(4)} · ` : ""}
        conversación en <Link href="/claude">/claude</Link>
      </p>
    </div>
  );
}

export default async function Maestro({
  searchParams,
}: {
  searchParams: Promise<{ tipo?: string; medidas?: string; muebles?: string; aberturas?: string }>;
}) {
  const { tipo, medidas, muebles, aberturas } = await searchParams;
  const kind = TYPES.includes(tipo ?? "") ? tipo! : TYPES[0];
  const ready = Boolean(medidas && muebles);
  const room = `${kind} de ${medidas}. Muebles: ${muebles}. Puerta y ventana: ${aberturas ?? "no especificado"}.`;

  return (
    <div className="gate wide">
      <form method="GET">
        <h1>☯ El Maestro de Feng Shui</h1>
        <p className="sub">Describe tu cuarto y el sabio acomoda los muebles — y te los dibuja.</p>
        <select name="tipo" defaultValue={kind}>
          {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input name="medidas" placeholder="medidas (ej. 4x3 metros)" defaultValue={medidas} required />
        <input name="muebles" placeholder="muebles (ej. cama, buró, escritorio, ropero)" defaultValue={muebles} required />
        <input name="aberturas" placeholder="puerta y ventana (ej. puerta al sur, ventana al este)" defaultValue={aberturas} />
        <button>Consultar al maestro</button>
      </form>
      {ready && <Plans room={room} />}
    </div>
  );
}
