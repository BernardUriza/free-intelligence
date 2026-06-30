# @free-intelligence/core

The **framework-agnostic contract layer** for Free Intelligence chat & agent
frontends. Pure TypeScript — no React, no DOM, no styling. It defines the
events a streaming agent emits and the reducers that fold them into UI state,
so any view layer (fi-glass, or your own) consumes one stable contract.

`@free-intelligence/core` is the data spine; [`fi-glass`](https://www.npmjs.com/package/fi-glass)
is the glassmorphism skin built on top of it.

## What's inside

| Export | What it is |
|---|---|
| `AgentStreamEvent` | The discriminated union an agent stream emits: `open`, `plan`, `step_started`, `step_done`, `tool_call`, `text`, `result`, `error`, `done` (+ plan lifecycle). |
| `applyAgentEvent` | Pure reducer: `(state, event) → state`. Folds a stream into an `AgentTurnState` (live text, plan checklist, tool calls, sources). |
| `initialAgentTurnState` | The empty turn state to seed the reducer. |
| `AgentHook` | The transport interface a consumer implements: `{ turn, isStreaming, send, reset, abort }`. |
| `ChatMessage`, `ConversationSummary` | Plain message / conversation shapes shared across the surface. |
| conversation helpers | Pure helpers for building and merging conversation transcripts. |

## Install

```bash
npm install @free-intelligence/core
# or, with the matching UI:
npm install @free-intelligence/core fi-glass
```

## Usage

Implement a transport that maps your backend's stream onto `AgentStreamEvent`,
then fold it with the reducer:

```ts
import {
  applyAgentEvent,
  initialAgentTurnState,
  type AgentStreamEvent,
} from '@free-intelligence/core';

let state = initialAgentTurnState();
for await (const raw of yourSSEStream()) {
  const event: AgentStreamEvent | null = mapToCore(raw); // your wire → core
  if (event) state = applyAgentEvent(state, event);      // pure, testable
}
```

The reducer is pure and has no side effects, so it's trivial to unit-test and
to drive any rendering layer. `fi-glass`'s `useAgentConversation` wraps exactly
this contract.

## License

See [LICENSE](./LICENSE).
