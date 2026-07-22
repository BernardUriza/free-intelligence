import Link from "next/link";
import { ask } from "../aire.ts";

export const dynamic = "force-dynamic";

/**
 * Cannabímetro — a canary consumer of AIRE: a THC-intake calculator that asks
 * the daemon's LLM door to do the math and the context. A `<form method="GET">`
 * and a Server Component render the result — NO client JavaScript, like the rest
 * of the front. Each calculation is one `complete` turn in the `canary-thc`
 * casita, so it also shows up as a conversation at `/claude` and in the log.
 */

const METHODS = ["fumado", "vaporizado", "comestible", "tintura"];
const PROJECT = "canary-thc";
const SESSION = "cannabimetro";

function buildPrompt(grams: string, thc: string, method: string): string {
  return (
    `Eres un calculador de consumo de THC. Datos: ${grams} g de flor al ${thc}% de THC, ` +
    `consumidos por vía ${method}. Devuelve, breve y en español: (1) los mg de THC totales ` +
    `(gramos × %THC × 10), (2) la biodisponibilidad típica de ese método, (3) los mg de THC ` +
    `realmente absorbidos, y (4) una nota de seguridad de una línea. Sin rodeos.`
  );
}

async function Result({ grams, thc, method }: { grams: string; thc: string; method: string }) {
  let text = "";
  let cost: number | null = null;
  let error = "";
  try {
    const turn = await ask(PROJECT, SESSION, buildPrompt(grams, thc, method));
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
