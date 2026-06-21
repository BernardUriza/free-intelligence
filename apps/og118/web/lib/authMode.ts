/**
 * Auth mode flag — the single source for "is Auth0 login active?" across the
 * frontend. Default `bearer` keeps the legacy paste-token path so nothing changes
 * until the build flips to `auth0` (the cutover). Read once at module load.
 */
export const OG118_AUTH_MODE = (process.env.NEXT_PUBLIC_OG118_AUTH_MODE ?? 'bearer') as
  | 'bearer'
  | 'auth0';

export const isAuth0Mode = OG118_AUTH_MODE === 'auth0';
