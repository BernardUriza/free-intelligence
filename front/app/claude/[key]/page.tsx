import Link from "next/link";
import Shell from "../../../components/Shell.tsx";
import { claudeSessions } from "../../../lib/db.ts";
import { folderName, freshness, sessionTitle } from "../../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** One folder's sessions, newest first — titled by the ai-title the SDK wrote
 *  into the transcript when one exists (a consumer replaying history opens
 *  every prompt with the same preamble, so first-prompt would title them all
 *  "Conversation so far:"), else by their first prompt. */
export default async function FolderPage({ params }: { params: Promise<{ key: string }> }) {
  const { key } = await params;
  const projectKey = decodeURIComponent(key);
  const sessions = await claudeSessions(projectKey);

  return (
    <Shell active="~claude">
      <h1>📁 {folderName(projectKey)}</h1>
      <p className="sub">
        <Link href="/claude">← all folders</Link> · <code>{projectKey}</code>
      </p>
      {sessions.length === 0 ? (
        <p className="empty">no sessions in this folder.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>session</th>
              <th>entries</th>
              <th>last activity</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.session_id}>
                <td>
                  <Link href={`/claude/${encodeURIComponent(projectKey)}/${s.session_id}`}>
                    ▸ {s.ai_title ?? sessionTitle(s.first_user)}
                  </Link>
                </td>
                <td>{s.entries}</td>
                <td>{freshness(s.mtime)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
