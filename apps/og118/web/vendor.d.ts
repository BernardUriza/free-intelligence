// recordrtc is a fi-glass internal dep loaded lazily via dynamic import.
// It ships no TypeScript types; this declaration silences the error when
// og118-web resolves fi-glass source via tsconfig paths.
declare module 'recordrtc';
