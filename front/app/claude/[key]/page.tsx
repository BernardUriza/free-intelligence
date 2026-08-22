import Link from "next/link";
import Shell from "../../../components/Shell.tsx";
import { casitaClaudeMd } from "../../../lib/artifacts.ts";
import { claudeSessions } from "../../../lib/db.ts";
import {
  CasitaPrompt, casitaDir, Crumbs, folderName, sessionTitle, When,
} from "../../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** One folder's sessions, newest first — titled by the ai-title the SDK wrote
 *  into the transcript when one exists (a consumer replaying history opens
 *  every prompt with the same preamble, so first-prompt would title them all
 *  "Conversation so far:"), else by their first prompt. */
export default async function FolderPage({ params }: { params: Promise<{ key: string }> }) {
  const { key } = await params;
  const projectKey = decodeURIComponent(key);
  const [sessions, claudeMd] = await Promise.all([
    claudeSessions(projectKey),
    casitaClaudeMd(casitaDir(projectKey)),
  ]);

  return (
    <Shell active="~claude">
      <Crumbs
        trail={[{ label: "conversations", href: "/claude" }, { label: folderName(projectKey) }]}
      />
      <h1>📁 {folderName(projectKey)}</h1>
      <p className="sub">
        {sessions.length} session{sessions.length === 1 ? "" : "s"} in this casita ·{" "}
        <code>{projectKey}</code>
      </p>
      <CasitaPrompt text={claudeMd} />
      {sessions.length === 0 ? (
        <div className="panel">
          <p className="empty">no sessions in this folder.</p>
        </div>
      ) : (
        <div className="panel">
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>session</th>
                  <th className="num">entries</th>
                  <th>last activity</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.session_id}>
                    <td className="said name">
                      <Link href={`/claude/${encodeURIComponent(projectKey)}/${s.session_id}`}>
                        {s.ai_title ?? sessionTitle(s.first_user)}
                      </Link>
                    </td>
                    <td className="num">{s.entries}</td>
                    <td>
                      <When mtime={s.mtime} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Shell>
  );
}
