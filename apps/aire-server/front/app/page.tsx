import Link from "next/link";
import NicknameGame from "../components/NicknameGame.tsx";

/**
 * The one page a stranger may see. It is public on purpose, so it obeys the rule
 * that governs every unauthenticated route here: it discloses nothing about the
 * schema, the data, or the existence of either. It opens no database connection —
 * there is no import of `lib/db.ts` above, and there must never be one.
 *
 * Signed-in visitors never land here: the middleware sends them to `/console`.
 */

export const metadata = {
  title: "AIRE — the agent that does not forget",
  description:
    "An HTTP server that wraps the Claude Agent SDK and mirrors every session's transcript to Postgres.",
};

export default function Landing() {
  return (
    <div className="land">
      <h1>AIRE 🌬️</h1>
      <p className="tag">Artificial Intelligence Reflector Envelope</p>

      <p className="lede">
        Your agent forgets everything when its container dies. AIRE does not.
      </p>

      <NicknameGame />

      <p>
        It wraps the Claude Agent SDK behind HTTP and mirrors every session&apos;s
        transcript into Postgres as it happens. The log is the truth; the process
        that writes it is disposable. Kill the machine, ask again, and the
        conversation continues.
      </p>

      <p className="foot">
        <Link href="/console">console →</Link>
        <span>private · access is by invitation</span>
      </p>
    </div>
  );
}
