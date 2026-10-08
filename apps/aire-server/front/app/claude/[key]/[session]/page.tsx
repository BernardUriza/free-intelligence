import Shell from "../../../../components/Shell.tsx";
import { casitaClaudeMd } from "../../../../lib/artifacts.ts";
import { claudeTranscript } from "../../../../lib/db.ts";
import {
  CasitaPrompt, casitaDir, Crumbs, entryText, entryTools, folderName, Md,
  sessionTitle, ToolChips, Turn, When,
} from "../../../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** The transcript, read like a Claude Code session — and drawn with the SAME
 *  card the gateway uses, so a conversation looks like a conversation whichever
 *  door mirrored it. It was a flat wall of `pre-wrap` text until 2026-08-22,
 *  while the good renderer sat one import away. The view is a cache: reload and
 *  it repaints from the log. */
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

  const titled = entries.find((r) => (r.entry as { type?: string })?.type === "ai-title");
  const firstUser = entries.find((r) => (r.entry as { type?: string })?.type === "user");
  const title =
    (titled?.entry as { aiTitle?: string })?.aiTitle ??
    (firstUser ? sessionTitle(firstUser.entry) : session);

  return (
    <Shell active="~claude">
      <Crumbs
        trail={[
          { label: "conversations", href: "/claude" },
          { label: folderName(projectKey), href: `/claude/${encodeURIComponent(projectKey)}` },
          { label: title },
        ]}
      />
      <h1>{title}</h1>
      <p className="sub">
        <code>{session}</code> · {entries.length} entries · mirrored <When mtime={last} />
      </p>
      <CasitaPrompt text={claudeMd} />

      <div className="thread">
        {entries.map((row, i) => {
          const e = row.entry as { type?: string };
          const text = entryText(row.entry);
          const tools = entryTools(row.entry);
          if (e?.type === "user" && text) {
            return (
              <Turn key={i} who="caller">
                <Md text={text} />
              </Turn>
            );
          }
          if (e?.type === "assistant" && (text || tools.length)) {
            return (
              <Turn key={i} who="model">
                {text && <Md text={text} />}
                <ToolChips tools={tools} />
              </Turn>
            );
          }
          return null;
        })}
      </div>
    </Shell>
  );
}
