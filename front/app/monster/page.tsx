import Shell from "../../components/Shell.tsx";
import { graph } from "../../lib/db.ts";
import { H, shape, W } from "../../lib/monster.ts";

export const dynamic = "force-dynamic";

/** The monster, served next to the tables it derives from. Postgres does the
 *  counting; this page does the geometry. The SVG is server-rendered markup — no
 *  charting library, no client JavaScript. */
export default async function MonsterPage() {
  const g = await graph();

  if (g.nodes.length === 0) {
    return (
      <Shell active="~monster">
        <h1>the monster 🌬️</h1>
        <p className="sub">
          <code>aire_log</code> is empty — no monster yet.
        </p>
      </Shell>
    );
  }

  const { nodes, edges } = shape(g);
  const transitions = [...g.edges].sort((a, b) => b.count - a.count);

  return (
    <Shell active="~monster">
      <h1>the monster 🌬️</h1>
      <p className="sub">
        Directly-follows graph of <code>aire_log</code> — {g.total.toLocaleString("en-US")}{" "}
        events, {g.span}. A node is an event type; an edge means “this followed that”,
        fatter = more often. Postgres does the counting; this page only draws it.
        {g.windowed && (
          <>
            <br />
            Reading the <b>last {g.scanned.toLocaleString("en-US")} lines</b> of the log, not
            all of it — the figure of a system now, not its average since the beginning of
            time.
          </>
        )}
      </p>

      <div className="panel">
        <figure>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            width={W}
            height={H}
            role="img"
            aria-label="Directly-follows graph of AIRE's event log"
          >
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="9"
                markerHeight="9"
                orient="auto-start-reverse"
                markerUnits="userSpaceOnUse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" />
              </marker>
            </defs>

            {edges.map((e) => (
              <path
                key={e.key}
                className="edge"
                d={e.path}
                strokeWidth={e.width.toFixed(1)}
                markerEnd="url(#arrow)"
              >
                <title>{`${e.from} → ${e.to}: ${e.count}×`}</title>
              </path>
            ))}

            {edges
              .filter((e) => e.showLabel)
              .map((e) => (
                <text
                  key={`l-${e.key}`}
                  className="edge-label"
                  x={e.labelX.toFixed(1)}
                  y={e.labelY.toFixed(1)}
                >
                  {e.count}
                </text>
              ))}

            {nodes.map((n) => (
              <g
                key={n.name}
                className="node"
                style={{ ["--c-light" as string]: n.light, ["--c-dark" as string]: n.dark }}
              >
                <circle cx={n.x.toFixed(1)} cy={n.y.toFixed(1)} r={n.r.toFixed(1)}>
                  <title>{`${n.name}: ${n.count} events`}</title>
                </circle>
                <text
                  className="node-label"
                  textAnchor={n.anchor}
                  x={n.lx.toFixed(1)}
                  y={n.ly.toFixed(1)}
                >
                  {n.name}
                </text>
                <text
                  className="node-count"
                  textAnchor={n.anchor}
                  x={n.lx.toFixed(1)}
                  y={(n.ly + 13).toFixed(1)}
                >
                  {n.count}
                </text>
              </g>
            ))}
          </svg>
        </figure>
      </div>

      <details className="panel">
        <summary>Every transition, as a table</summary>
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>from</th>
                <th>to</th>
                <th>count</th>
              </tr>
            </thead>
            <tbody>
              {transitions.map((e) => (
                <tr key={`${e.from}->${e.to}`}>
                  <td>{e.from}</td>
                  <td>{e.to}</td>
                  <td>{e.count.toLocaleString("en-US")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Shell>
  );
}
