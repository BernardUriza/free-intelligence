import Shell from "../../components/Shell.tsx";
import { logLines } from "../../lib/db.ts";
import { buildGraph, H, shape, span, splitEdge, W } from "../../lib/monster.ts";

export const dynamic = "force-dynamic";

/** The monster, served next to the tables it derives from. The SVG is rendered on
 *  the server — inline markup, no charting library, no client JavaScript. */
export default async function MonsterPage() {
  const lines = await logLines();

  if (lines.length === 0) {
    return (
      <Shell active="~monster">
        <h1>The monster 🌬️</h1>
        <p className="sub">
          <code>aire_log</code> is empty — no monster yet.
        </p>
      </Shell>
    );
  }

  const graph = buildGraph(lines);
  const { nodes, edges } = shape(graph);
  const transitions = [...graph.edges.entries()].sort((a, b) => b[1] - a[1]);

  return (
    <Shell active="~monster">
      <h1>The monster 🌬️</h1>
      <p className="sub">
        Directly-follows graph of <code>aire_log</code> — {graph.total.toLocaleString("en-US")}{" "}
        events, {span(lines)}. A node is an event type; an edge means “this followed that”,
        fatter = more often. The truth lives in Postgres; this page is a waiter.
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
                <text className="node-label" x={n.x.toFixed(1)} y={(n.y + n.r + 16).toFixed(1)}>
                  {n.name}
                </text>
                <text className="node-count" x={n.x.toFixed(1)} y={(n.y + n.r + 30).toFixed(1)}>
                  {n.count}
                </text>
              </g>
            ))}
          </svg>
        </figure>
      </div>

      <details>
        <summary>Every transition, as a table</summary>
        <div className="panel" style={{ marginTop: 8 }}>
          <table>
            <thead>
              <tr>
                <th>from</th>
                <th>to</th>
                <th>count</th>
              </tr>
            </thead>
            <tbody>
              {transitions.map(([key, count]) => {
                const [from, to] = splitEdge(key);
                return (
                  <tr key={key}>
                    <td>{from}</td>
                    <td>{to}</td>
                    <td>{count.toLocaleString("en-US")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </Shell>
  );
}
