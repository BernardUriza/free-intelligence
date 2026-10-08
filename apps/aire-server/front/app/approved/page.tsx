import Link from "next/link";

/**
 * Where the daemon sends Bernard after he clicks the link in his inbox. The
 * approval was already written, with a verified signature, before this page
 * rendered — this is a receipt, not the decision.
 *
 * Public, because a link in an email must open on whatever device is in hand
 * without a console password. It reads no database and states nothing it was not
 * handed in the URL, so a stranger visiting it directly learns exactly nothing.
 */

export const dynamic = "force-dynamic";

export const metadata = { title: "AIRE — approved" };

export default async function Approved({
  searchParams,
}: {
  searchParams: Promise<{ n?: string; bad?: string; revoked?: string }>;
}) {
  const { n, bad, revoked } = await searchParams;
  const name = (n ?? "").slice(0, 80);
  const gone = (revoked ?? "").slice(0, 80);

  return (
    <div className="land">
      <h1>AIRE 🌬️</h1>
      <p className="tag">Artificial Intelligence Reflector Envelope</p>

      {gone ? (
        <>
          <p className="lede">
            <b>{gone}</b> is out.
          </p>
          <p>
            Their key stopped working the moment you clicked. Approving them again
            issues a fresh one.
          </p>
        </>
      ) : bad || !name ? (
        <>
          <p className="lede">That link is no good.</p>
          <p>
            It was either tampered with or it expired — invitations last fourteen
            days. Nothing changed. If someone is still waiting, have them ask again
            from the front page.
          </p>
        </>
      ) : (
        <>
          <p className="lede">
            <b>{name}</b> is in.
          </p>
          <p>
            Their key is in your inbox, not on this page — a working credential in a
            URL would sit in your browser history and in this site&apos;s logs. AIRE
            keeps only its hash, so that mail is the one copy. It spends against a
            ceiling of its own, and the same mail carries the link that revokes it.
          </p>
        </>
      )}

      <p className="foot">
        <Link href="/console">console →</Link>
        <span>private · access is by invitation</span>
      </p>
    </div>
  );
}
