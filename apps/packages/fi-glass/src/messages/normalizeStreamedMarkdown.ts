/**
 * normalizeStreamedMarkdown — repair chunk-boundary glue in streamed LLM output
 * before markdown rendering (B3-FIGLASS-9).
 *
 * The staging audit showed an assistant reply rendering "…las herramientas
 * necesarias.## Respuesta sobre…" — the backend concatenated the pre-tool text
 * and the post-tool response without a newline, so the ATX heading never starts
 * a line and CommonMark (correctly) treats it as paragraph text.
 *
 * This is a NORMALIZER, not a parser: one conservative repair, applied only
 * outside fenced code blocks.
 *
 * Repair rule: a heading marker (`#{1,6} `) glued directly onto sentence-ending
 * punctuation gets a blank line inserted before it. Requiring the punctuation
 * (no whitespace in between) is what keeps false positives out:
 *  - `C# is nice`      → untouched (letter before `#`)
 *  - `issue #123`      → untouched (no space after `#`)
 *  - `use the # key`   → untouched (whitespace before `#`)
 *  - `fin.## Título`   → `fin.\n\n## Título` (the streaming-glue case)
 */

/** Split keeping fences as odd segments. An unterminated fence (streaming!) runs to the end. */
const FENCE_SPLIT = /(```[\s\S]*?(?:```|$))/;

/** Sentence punctuation immediately followed by an ATX heading marker. */
const GLUED_HEADING = /([.!?:;,)\]"'»…])(#{1,6} )/g;

export function normalizeStreamedMarkdown(content: string): string {
  if (!content.includes('#')) return content;
  return content
    .split(FENCE_SPLIT)
    .map((segment, i) =>
      i % 2 === 1 ? segment : segment.replace(GLUED_HEADING, '$1\n\n$2'),
    )
    .join('');
}
