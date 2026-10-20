# fi-glass

The **glassmorphism material (skin)** for Free Intelligence chat frontends —
glass-box agentic UI rendered as frosted surfaces. Depends only on
`@free-intelligence/core`. One build → N consumers (aurity, og118, …).

Subpath exports: `fi-glass` (root), `fi-glass/theme`, `fi-glass/theme.css`,
`fi-glass/messages`, `fi-glass/composer`, `fi-glass/voice`, `fi-glass/shell`,
`fi-glass/persona-selector`, `fi-glass/agent`.

---

## ⚠️ Tailwind is required for the visual primitives

This is the one coupling that isn't obvious from the type signatures, so read it
before you wire fi-glass into a fresh app.

`fi-glass/messages` (and the shell that renders it) emit **Tailwind utility
class strings** — `messageStyles` / `markdownStyles` are values like
`'group relative py-3 px-4'`, `'bg-white/[0.02]'`, `'text-slate-300'`. They are
**not** compiled CSS. fi-glass ships the class *strings* in its `dist`; your app
is what turns them into styles. So a consumer must:

1. **Have Tailwind** (v3 or v4) configured in the app.
2. **Tell Tailwind to scan fi-glass's `dist`.** Tailwind ignores `node_modules`,
   so fi-glass declares the globs itself in the `fi-glass/tailwind` export:
   spread them into your `content` instead of hand-writing a relative path.

### Tailwind v3 — `tailwind.config.js`

```js
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    ...require('fi-glass/tailwind').content,
  ],
};
```

`og118-web/app/__tests__/tailwindContract.test.ts` compiles og118's real config and
fails if a fi-glass-only utility stops being generated — copy it into a new consumer.

### Tailwind v4 — CSS `@source`

CSS cannot `require`, so point `@source` at the same directory the export names:

```css
@import 'tailwindcss';
@source '../../packages/fi-glass/dist';
```

### Theme tokens

The glassmorphism tokens (`--glass-blur`, `--glass-border`, …) come from the CSS,
imported via the package subpath — no build step:

```ts
import 'fi-glass/theme.css';
```

---

## Shell: `<ChatWidget>` vs `<ChatSurface>`

Two compositions over the same `ChatHook` spine. Pick by shape:

| | `<ChatWidget>` | `<ChatSurface>` |
|---|---|---|
| Shape | Floating bubble (FloatingButton when closed) + view modes | Full-page, chat-first (the chat IS the page) |
| Closed state | Yes (launcher) | None — mounts always open |
| Layout | Floats / minimizes / maximizes | Fills its parent (the page owns height) |
| Use it for | A chat dock in a corner of an app | A dedicated chat route, e.g. og118 `/` |

`ChatSurface` is not a fork: internally it is `<ChatWidget>` pinned to the
embedded + open + fullscreen view, reusing `ChatWidgetContainer`'s view-mode
math. It only removes the launcher.

```tsx
import { ChatSurface } from 'fi-glass/shell';

// A hello-chat: only the conversation essentials. Voice / upload / personas /
// response-mode are OFF because their handlers are omitted (feature-off by
// absence) — the toolbar hides them automatically.
export default function Page() {
  return (
    <div className="h-dvh">
      <ChatSurface
        chatHook={chat}
        message={message}
        onMessageChange={setMessage}
        onSend={send}
      />
    </div>
  );
}
```

### Optional capabilities (feature-off by absence)

`ChatWidgetProps` requires only `chatHook` + `message` / `onMessageChange` /
`onSend`. Everything else is optional, and **a control is shown only when its
handler is wired**:

- **Voice** — pass `onVoiceStart` / `onVoiceStop` (+ `voiceState`) to show the mic.
- **Upload** — pass `onAttach` (+ `uploadFile` / `uploadStatus` / `isUploadActive`).
- **Personas** — pass the `personaSelector` slot (+ `onPersonaChange` / `personaName`).
- **Response mode** — pass `onResponseModeToggle` (+ `responseMode`).
- **Clear / thinking / curl** — pass `onClearConversation` / `onShowThinkingToggle` / `onCopyCurl`.

Omit any of them and the corresponding toolbar control simply doesn't render —
no stubs, no dead buttons.

---

## Voice playback: `useAudioPlayer` / `<AudioPlayer>`

The voice stack is two halves. **Synthesis** turns text into an `AudioSource`
(`useVoice(adapter)` + `SpeakButton`); **playback** turns that source into sound.
Playback is the reusable foundation here — an app no longer re-wires its own
`<audio>`, play/stop, loading/error and object-URL cleanup.

Three layers, pick the one you need (all from `fi-glass/voice`):

- `createAudioPlayer(opts)` — headless engine (no React). Owns the element, the
  play/pause/stop state machine, and **revokes only the object URLs it created**
  (a `{ url }` source is left alone for streaming). Dependency-injected, so it
  unit-tests in node with a fake element — no DOM, no network.
- `useAudioPlayer(opts)` — React hook over the engine; disposes (and revokes) on
  unmount.
- `<AudioPlayer source={...} />` — minimal accessible controls (play/pause + stop,
  loading spinner, `role="alert"` error). Restyle via `className` props.

```tsx
import { useVoice, useAudioPlayer } from 'fi-glass/voice';

function Message({ text, adapter }) {
  const { generateAudio, audioUrl } = useVoice(adapter); // text -> AudioSource
  const player = useAudioPlayer({ onError: report });    // AudioSource -> sound

  // The hook owns cleanup; or drop in <AudioPlayer source={blob} /> directly.
  return <button onClick={() => generateAudio(text)}>Speak</button>;
}
```

Playback needs no adapter — it consumes an `AudioSource` (a `Blob` or `{ url }`),
so it works with any synthesis path.

---

## Agent panel: `<AgentPanel>`

Renders one reduced agentic turn (`AgentTurnState` from core's
`applyAgentEvent`): the plan checklist (with guard banner woven in), the live
tool-call steps, and sources. Each sub-panel self-hides when empty.

`PlanChecklist` renders the full plan lifecycle that core v1.1.0 exposes:
per-step `done` / `failed` / `cancelled` (struck) statuses, `note` annotations,
a `revised` / `re-planned` badge when the plan is amended mid-turn, and a
terminal `completed` / `failed` / `cancelled` outcome badge.
