// Ambient declarations for deps that ship no TypeScript types.
// recordrtc is loaded lazily via dynamic import in useDurableRecording.ts
// and immediately typed as `any` — this declaration silences the
// "implicitly has an 'any' type" error when consumers compile fi-glass source.
declare module 'recordrtc';
