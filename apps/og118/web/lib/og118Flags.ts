/**
 * og118 feature flags — the ONE module that reads a `NEXT_PUBLIC_*` switch.
 *
 * Nothing else in the web app touches `process.env` for a feature gate: a flag
 * spread over six files is a flag that gets half-flipped.
 *
 * ## NEXT_PUBLIC_OG118_PROYECTOS
 *
 * The Projects feature (workspaces with a document corpus), OFF by default.
 * Bernard stopped using it on 2026-08-29 and asked to HIDE it rather than delete
 * it, so the code stays intact and simply stops rendering and stops calling the
 * API.
 *
 * It is the frontend half of the server's `OG118_PROYECTOS` (see
 * `apps/og118/server/app.py`) and carries the SAME truthy vocabulary —
 * `"1" | "true" | "yes" | "on"`, case- and space-insensitive — so one mental
 * model covers both halves. With the server flag off, `GET /projects` is a real
 * 404 (the router is never mounted), which is exactly why the client must not
 * fire the request: a 404 per mount is console noise that looks like a bug.
 *
 * Read at CALL time, not at import, for the same reason the server does: a
 * module-level constant would force `vi.resetModules()` + a dynamic re-import to
 * exercise the other branch, and that leaks module state into whatever suite runs
 * next. Next replaces the `process.env.NEXT_PUBLIC_*` member expression with a
 * literal at build time, so the call still folds to a constant in the bundle and
 * the dead branch is still eliminated.
 */

function isOn(raw: string | undefined): boolean {
  return ['1', 'true', 'yes', 'on'].includes((raw ?? '0').trim().toLowerCase());
}

/** True when the Projects feature is switched on for this build. */
export function proyectosActivos(): boolean {
  return isOn(process.env.NEXT_PUBLIC_OG118_PROYECTOS);
}
