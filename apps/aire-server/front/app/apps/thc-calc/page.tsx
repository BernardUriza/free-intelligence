// Thin route: the canary consumers live in `front/apps/` (Bernard's layout);
// Next.js routes from `app/`, so each app is re-exported here as its URL.
// `dynamic` must be declared in the route file itself (Next can't re-export it).
export const dynamic = "force-dynamic";
export { default } from "../../../apps/thc-calc/page.tsx";
