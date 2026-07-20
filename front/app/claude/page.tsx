import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { claudeFolders } from "../../lib/db.ts";
import { folderName, freshness } from "../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** The start: one link per folder with Claude inside. Each project_key is a
 *  casita; click it and read what was said there. */
export default async function ClaudePage() {
  const folders = await claudeFolders();

  return (
    <Shell active="~claude">
      <h1>claude</h1>
      <p className="sub">
        the memory, folder by folder — every conversation the mirror carried out
        of the body, read straight from <code>claude_session_store</code>.
      </p>
      {folders.length === 0 ? (
        <p className="empty">no conversations in the store yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>folder</th>
              <th>sessions</th>
              <th>entries</th>
              <th>last activity</th>
            </tr>
          </thead>
          <tbody>
            {folders.map((f) => (
              <tr key={f.project_key}>
                <td>
                  <Link href={`/claude/${encodeURIComponent(f.project_key)}`}>
                    📁 {folderName(f.project_key)}
                  </Link>
                </td>
                <td>{f.sessions}</td>
                <td>{f.entries}</td>
                <td>{freshness(f.mtime)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
