/**
 * fi-glass/identity — partition local-first stores by the authenticated user.
 *
 * The naming-convention SSOT every shell uses to scope a browser store (IndexedDB
 * database, localStorage key) to the signed-in account, so accounts that share a
 * device do not see each other's data. Used by the conversation + audio-queue
 * hooks here and by consumer-local stores (e.g. a projects list) alike.
 */

export { scopedStoreName } from './scopedStore';
