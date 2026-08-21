import Link from "next/link";
import Shell from "../../../../components/Shell.tsx";
import { casitaClaudeMd } from "../../../../lib/artifacts.ts";
import { claudeTranscript } from "../../../../lib/db.ts";
import {
  CasitaPrompt, casitaDir, entryText, entryTools, folderName, freshness, Line,
} from "../../../../lib/claude.tsx";

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
  const [entries, claudeMd] = await Promise.all([
    claudeTranscript(projectKey, session),
    casitaClaudeMd(casitaDir(projectKey)),
  ]);
  const last = entries.length ? entries[entries.length - 1].mtime : "";

  return (
    <Shell active="~claude">
      <h1>📁 {folderName(projectKey)}</h1>
      <p className="sub">
        <Link href={`/claude/${encodeURIComponent(projectKey)}`}>← sessions</Link> ·{" "}
        <code>{session}</code> · {entries.length} entries · mirror {freshness(last)}
      </p>
      <CasitaPrompt text={claudeMd} />
      <div className="panel convo">
        {entries.map((row, i) => {
          const e = row.entry as { type?: string };
          const text = entryText(row.entry);
          const tools = entryTools(row.entry);
          if (e?.type === "user" && text) {
            return (
              <div key={i} className="turn-caller">
                <Line who="caller" text={text} />
              </div>
            );
          }
          if (e?.type === "assistant" && (text || tools.length)) {
            return (
              <div key={i}>
                {text && (
                  <div>
                    <Line who="model" text={text} />
                  </div>
                )}
                {tools.map((t, j) => (
                  <div key={j} className="chip-line">
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
