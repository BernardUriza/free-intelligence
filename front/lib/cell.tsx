/** How a Postgres value becomes a table cell. jsonb arrives as an object, a
 *  timestamptz as a Date, a bigint as a string — each is shown as itself, and
 *  NULL is shown as NULL rather than as an empty cell that could be an empty
 *  string. The full value rides in `title` so a clipped row is still readable. */
export function Cell({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <td className="null">NULL</td>;
  }

  let text: string;
  if (value instanceof Date) {
    text = value.toISOString().replace("T", " ").slice(0, 19);
  } else if (typeof value === "object") {
    text = JSON.stringify(value);
  } else {
    text = String(value);
  }

  const clipped = text.length > 300 ? text.slice(0, 300) + "…" : text;
  return <td title={text.slice(0, 600)}>{clipped}</td>;
}
