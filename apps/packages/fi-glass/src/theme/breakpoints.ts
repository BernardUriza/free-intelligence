/**
 * fi-glass · the mobile breakpoint, in ONE place (B3-FIGLASS-TOKEN-LAYER-1).
 *
 * `768px` was written SEVEN times across four different styling layers — the
 * touch-target sheet, the density sheet, the workspace shell's drawer query, the
 * surface layout hook, and three static stylesheets — coordinated only by prose
 * comments ("the 768px breakpoint matches the shell's drawer/mobile query"). A
 * comment is not a constraint: any one of those could drift and the others would
 * keep claiming, in English, that they agreed.
 *
 * WHY THIS IS A TS CONSTANT AND NOT A CSS CUSTOM PROPERTY: a media query cannot
 * read one. `@media (max-width: var(--fi-mobile))` is invalid CSS — custom
 * properties resolve during computed-value time, long after the at-rule is
 * evaluated. So the breakpoint physically cannot live in the token sheet with
 * the rest; the JS-generated sheets interpolate this constant instead, and the
 * three hand-written `.css` files are held to it by `breakpoints.test.ts`,
 * which parses them and fails on any `max-width` that disagrees.
 */

/** The mobile breakpoint in CSS px. Below/at this width the UI is a phone. */
export const FI_MOBILE_BREAKPOINT_PX = 768;

/** The canonical mobile media query. Feed it to `useMediaQuery` or a `@media`. */
export const FI_MOBILE_QUERY = `(max-width: ${FI_MOBILE_BREAKPOINT_PX}px)`;

/**
 * The coarse-pointer OR narrow-viewport query — "this is a touch surface".
 * Used by the touch-target minimums, which must also fire on a large tablet
 * that is wide but has no fine pointer.
 */
export const FI_TOUCH_QUERY = `(pointer: coarse), ${FI_MOBILE_QUERY}`;
