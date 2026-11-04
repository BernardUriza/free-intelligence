/**
 * SSE framing for the agent stream: cut a growing byte buffer into the `data:`
 * payloads that are complete, and hand back what is still arriving.
 *
 * A frame ends at a blank line; its `data:` lines join with `\n` (the SSE spec),
 * which for the server's one-line frames is the line itself. Every transport
 * (fetch in og118-web, URLSession on the iPhone) used to carry its own copy of
 * this cut; the shared fixture `contracts/fixtures/turno-real.sse` is what each
 * copy must read identically.
 *
 * @param buffer everything received so far that has not been consumed
 * @returns the complete payloads in order, and the unconsumed tail
 */
export function takeSseFrames(buffer: string): { payloads: string[]; rest: string } {
  const frames = buffer.split('\n\n');
  const rest = frames.pop() ?? '';
  const payloads: string[] = [];
  for (const frame of frames) {
    const data = frame
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim());
    if (data.length > 0) payloads.push(data.join('\n'));
  }
  return { payloads, rest };
}
