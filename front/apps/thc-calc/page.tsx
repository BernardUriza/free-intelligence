import Link from "next/link";
import { ask, init } from "../aire.ts";
import { PERSONA } from "./persona.ts";

export const dynamic = "force-dynamic";

/**
 * Cannabímetro — a canary consumer of AIRE: a THC-intake calculator that asks
 * the daemon's LLM door to do the math. A `<form method="GET">` and a Server
 * Component render the result — NO client JavaScript, like the rest of the front.
 *
 * The consumer is ANOREXIC (the free-intelligence pattern): its fixed persona
 * lives in the casita (set once via `init`, stored as the casita's CLAUDE.md),
 * so each turn sends ONLY the changing values. Each calc is one `complete` turn
 * in `canary-thc`, visible as a conversation at `/claude`.
 */

const METHODS = ["fumado", "vaporizado", "comestible", "tintura"];
const PROJECT = "canary-thc";
const SESSION = "cannabimetro";

async function Result({ grams, thc, method }: { grams: string; thc: string; method: string }) {
  let text = "";
  let cost: number | null = null;
  let error = "";
  try {
    await init(PROJECT, PERSONA); // the persona lives in the casita, not the message
    const turn = await ask(PROJECT, SESSION, `${grams} g al ${thc}% THC, vía ${method}`);
    text = turn.text;
    cost = turn.costUsd;
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }
  if (error) return <p className="wrong">La puerta AIRE no respondió: {error}</p>;
  return (
    <div className="result">
      <pre>{text}</pre>
      <p className="sub">
        {cost != null ? `costo del turno: $${cost.toFixed(4)} · ` : ""}
        conversación en <Link href="/claude">/claude</Link>
      </p>
    </div>
  );
}

export default async function Cannabimetro({
  searchParams,
}: {
  searchParams: Promise<{ g?: string; thc?: string; metodo?: string }>;
}) {
  const { g, thc, metodo } = await searchParams;
  const method = METHODS.includes(metodo ?? "") ? metodo! : METHODS[0];
  const ready = Boolean(g && thc);

  return (
    <div className="gate">
      <form method="GET">
        <h1>🌿 Cannabímetro</h1>
        <p className="sub">Calcula tu consumo de THC — la matemática la hace la IA a través de AIRE.</p>
        <input name="g" type="number" step="0.1" min="0" placeholder="gramos de flor" defaultValue={g} required />
        <input name="thc" type="number" step="0.1" min="0" max="100" placeholder="% de THC" defaultValue={thc} required />
        <select name="metodo" defaultValue={method}>
          {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <button>Calcular</button>
      </form>
      {ready && <Result grams={g!} thc={thc!} method={method} />}
    </div>
  );
}
