import Link from "next/link";
import Shell from "../../../../components/Shell.tsx";
import { claudeTranscript } from "../../../../lib/db.ts";
import { entryText, entryTools, folderName, freshness } from "../../../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** The transcript, read like a Claude Code session: › prompts, ⏺ replies,
 *  tool chips. The view is a cache — reload and it repaints from the log. */
export default async function SessionPage({
  params,
}: {
  params: Promise<{ key: string; session: string }>;
}) {
  const { key, session } = await params;
  const projectKey = decodeURIComponent(key);
  const entries = await claudeTranscript(projectKey, session);
  const last = entries.length ? entries[entries.length - 1].mtime : "";

  return (
    <Shell active="~claude">
      <h1>📁 {folderName(projectKey)}</h1>
      <p className="sub">
        <Link href={`/claude/${encodeURIComponent(projectKey)}`}>← sessions</Link> ·{" "}
        <code>{session}</code> · {entries.length} entries · mirror {freshness(last)}
      </p>
      <div className="panel" style={{ display: "grid", gap: "0.9rem", padding: "1rem" }}>
        {entries.map((row, i) => {
          const e = row.entry as { type?: string };
          const text = entryText(row.entry);
          const tools = entryTools(row.entry);
          if (e?.type === "user" && text) {
            return (
              <div key={i} style={{ opacity: 0.85 }}>
                <span style={{ color: "#7aa2f7" }}>›</span>{" "}
                <span style={{ whiteSpace: "pre-wrap" }}>{text}</span>
              </div>
            );
          }
          if (e?.type === "assistant" && (text || tools.length)) {
            return (
              <div key={i}>
                {text && (
                  <div>
                    <span style={{ color: "#9ece6a" }}>⏺</span>{" "}
                    <span style={{ whiteSpace: "pre-wrap" }}>{text}</span>
                  </div>
                )}
                {tools.map((t, j) => (
                  <div key={j} style={{ fontSize: "0.85em", opacity: 0.7, marginLeft: "1.2rem" }}>
                    <code>
                      [{t.name}
                      {t.summary ? ` ${t.summary}` : ""}]
                    </code>
                  </div>
                ))}
              </div>
            );
          }
          return null;
        })}
      </div>
    </Shell>
  );
}
