# FI-VIEWER Module

**Free Intelligence Interaction Viewer**

> Split-view interaction viewer with markdown rendering, syntax highlighting, and metadata panel

## Features

### ✅ Implemented

- **Split View Layout**: Prompt on left, response on right
- **Markdown Rendering**: Full GFM (GitHub Flavored Markdown) support
- **Syntax Highlighting**: Code blocks with `rehype-highlight`
- **Expandable Metadata Panel**: Session, thread, model, timestamps, tokens, duration
- **Prev/Next Navigation**: Navigate between interactions in a session
- **Copy to Clipboard**: One-click copy for prompt or response
- **Export Individual**: Export single interaction as JSON
- **Responsive Design**: Tailwind CSS with dark mode
- **TypeScript**: Full type safety

## Architecture

```
fi-viewer/
├── components/
│   ├── InteractionViewer.tsx    # Main component (split view + navigation)
│   ├── MarkdownViewer.tsx       # Markdown renderer with syntax highlighting
│   ├── MetadataPanel.tsx        # Expandable metadata sidebar
│   └── index.ts                 # Public exports
├── hooks/
│   └── useInteractions.ts       # React hook for data fetching
├── types/
│   └── interaction.ts           # TypeScript interfaces
├── index.ts                     # Module entry point
└── README.md                    # This file
```

## Usage

### Basic Usage

```tsx
import { InteractionViewer } from '@/aurity/modules/fi-viewer';

const interaction = {
  interaction_id: '550e8400-e29b-41d4-a716-446655440000',
  session_id: 'session_20241028_123456',
  prompt: '# Test Prompt\n\nWith **markdown**',
  response: '# Response\n\nWith `code`',
  model: 'claude-3-5-sonnet-20241022',
  timestamp: '2024-10-28T12:34:56-06:00',
  tokens: 256,
};

<InteractionViewer
  interaction={interaction}
  showMetadata={true}
  onNavigatePrev={() => console.log('prev')}
  onNavigateNext={() => console.log('next')}
  onCopy={(content) => console.log('copied:', content)}
  onExport={(interaction) => console.log('export:', interaction)}
/>
```

### Using with Hook

```tsx
import { InteractionViewer } from '@/aurity/modules/fi-viewer';
import { useInteractions } from '@/aurity/modules/fi-viewer/hooks/useInteractions';

function MyComponent() {
  const {
    currentInteraction,
    hasNext,
    hasPrev,
    navigateNext,
    navigatePrev,
  } = useInteractions({
    sessionId: 'session_20241028_123456',
    autoFetch: true,
  });

  if (!currentInteraction) return <div>Loading...</div>;

  return (
    <InteractionViewer
      interaction={currentInteraction}
      onNavigatePrev={hasPrev ? navigatePrev : undefined}
      onNavigateNext={hasNext ? navigateNext : undefined}
    />
  );
}
```

## API Reference

### `<InteractionViewer />`

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `interaction` | `Interaction` | ✅ | The interaction to display |
| `showMetadata` | `boolean` | ❌ | Show metadata panel (default: true) |
| `onNavigatePrev` | `() => void` | ❌ | Handler for prev button |
| `onNavigateNext` | `() => void` | ❌ | Handler for next button |
| `onCopy` | `(content: string) => void` | ❌ | Handler for copy action |
| `onExport` | `(interaction: Interaction) => void` | ❌ | Handler for export action |
| `className` | `string` | ❌ | Additional CSS classes |

### `useInteractions(options)`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `sessionId` | `string` | - | Filter by session ID |
| `limit` | `number` | 100 | Max interactions to fetch |
| `offset` | `number` | 0 | Pagination offset |
| `autoFetch` | `boolean` | true | Auto-fetch on mount |

**Returns:**

| Field | Type | Description |
|-------|------|-------------|
| `interactions` | `Interaction[]` | All fetched interactions |
| `currentInteraction` | `Interaction \| null` | Current interaction |
| `currentIndex` | `number` | Current index (0-based) |
| `loading` | `boolean` | Loading state |
| `error` | `Error \| null` | Error state |
| `hasNext` | `boolean` | Can navigate next |
| `hasPrev` | `boolean` | Can navigate prev |
| `navigateNext` | `() => void` | Navigate to next |
| `navigatePrev` | `() => void` | Navigate to prev |
| `goToIndex` | `(index: number) => void` | Jump to index |
| `refresh` | `() => Promise<void>` | Refresh data |

## Demo Page

Visit `/viewer` to see the InteractionViewer in action:

```bash
cd apps/aurity
pnpm dev
# Open http://localhost:9000/viewer
```

## Backend Integration

The viewer integrates with Free Intelligence backend via `/api/interactions`:

```typescript
GET /api/interactions?session_id=<id>&limit=100&offset=0
```

**Response:**

```json
{
  "interactions": [
    {
      "interaction_id": "uuid",
      "session_id": "session_20241028_123456",
      "prompt": "...",
      "response": "...",
      "model": "claude-3-5-sonnet-20241022",
      "timestamp": "2024-10-28T12:34:56-06:00",
      "tokens": 256
    }
  ],
  "total": 100,
  "limit": 100,
  "offset": 0
}
```

Backend must be running on port 7000 (default) or set `FI_BACKEND_URL` env var.

## Dependencies

- `react-markdown` - Markdown rendering
- `remark-gfm` - GitHub Flavored Markdown
- `rehype-highlight` - Syntax highlighting
- `highlight.js` - Code highlighting themes

## Styling

Uses Tailwind CSS with dark mode:

- `bg-gray-900` - Main background
- `bg-gray-800` - Panels
- `text-gray-200` - Text
- `prose prose-invert` - Markdown styles

Custom CSS classes:

- `.interaction-viewer` - Main container
- `.split-view` - Split layout
- `.prompt-panel` / `.response-panel` - Left/right panels
- `.metadata-sidebar` - Metadata sidebar
- `.markdown-viewer` - Markdown content
- `.code-block` - Code blocks

## Future Enhancements

- [ ] Thread view (group interactions by thread_id)
- [ ] Search/filter interactions
- [ ] Diff view (compare interactions)
- [ ] Timeline view (chronological visualization)
- [ ] Export as Markdown/PDF
- [ ] Bookmarks/favorites
- [ ] Tags/labels
- [ ] Full-text search
- [ ] Embedding visualization

## License

**Proprietary** - Part of Free Intelligence project
© 2025 Bernard Uriza Orozco

---

**Module**: FI-VIEWER
**Version**: 0.1.0
**Status**: ✅ Production Ready
**Card**: FI-UI-FEAT-002
**Sprint**: SPR-2025W44
