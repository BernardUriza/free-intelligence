import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { claudeFolders } from "../../lib/db.ts";
import { folderName, humanBytes, When } from "../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** The start: one link per folder with Claude inside. Each project_key is a
 *  casita; click it and read what was said there. */
export default async function ClaudePage() {
  const folders = await claudeFolders();
  const sessions = folders.reduce((n, f) => n + f.sessions, 0);

  return (
    <Shell active="~claude">
      <h1>conversations</h1>
      <p className="sub">
        The memory, folder by folder — {folders.length} casita
        {folders.length === 1 ? "" : "s"}, {sessions.toLocaleString("en-US")} session
        {sessions === 1 ? "" : "s"} the mirror carried out of the body, read straight from{" "}
        <code>claude_session_store</code>.
      </p>
      {folders.length === 0 ? (
        <div className="panel">
          <p className="empty">no conversations in the store yet.</p>
        </div>
      ) : (
        <div className="panel">
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>folder</th>
                  <th className="num">sessions</th>
                  <th className="num">entries</th>
                  <th className="num">weight</th>
                  <th>last activity</th>
                </tr>
              </thead>
              <tbody>
                {folders.map((f) => (
                  <tr key={f.project_key}>
                    <td className="name">
                      <Link href={`/claude/${encodeURIComponent(f.project_key)}`}>
                        📁 {folderName(f.project_key)}
                      </Link>
                    </td>
                    <td className="num">{f.sessions}</td>
                    <td className="num">{f.entries}</td>
                    <td className="num">{humanBytes(f.weight_bytes)}</td>
                    <td>
                      <When mtime={f.mtime} />
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
