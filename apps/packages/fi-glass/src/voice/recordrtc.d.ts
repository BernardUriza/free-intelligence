// recordrtc ships no type declarations and is not on DefinitelyTyped in a form
// we depend on. fi-glass only touches it through a lazy `await import('recordrtc')`
// in makeRecorder.ts (already cast to `any`), so an ambient module declaration is
// enough to make the package type-check cleanly without pulling a new dependency.
// recordrtc itself is an OPTIONAL peer (see package.json peerDependenciesMeta):
// only apps that use the recorder engine need it installed at runtime.
declare module 'recordrtc';
