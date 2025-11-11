# Chunk Monitoring Dashboard - Professional Observability

**Date**: 2025-11-10
**Component**: `apps/aurity/components/ChunkBreakdown.tsx`
**Page**: `apps/aurity/app/test-chunks/page.tsx`
**Version**: 2.0 (Complete redesign)

---

## 🎯 Overview

Professional-grade chunk monitoring dashboard with advanced observability features, inspired by modern APM tools (Datadog, Grafana, New Relic). Provides real-time insights into audio chunk processing, transcription quality, and system performance.

### Key Improvements Over v1.0

| Feature | v1.0 (Basic) | v2.0 (Professional) |
|---------|--------------|---------------------|
| **Metrics** | None | 4 real-time KPIs with trends |
| **Tracing** | None | Timeline visualization with span analysis |
| **Latency Tracking** | None | Performance.now() + 20-point history |
| **UI Design** | Basic list | Datadog-inspired dashboard |
| **Status Indicators** | Simple icons | Color-coded badges (✓/⚠/✗) |
| **Expandable Details** | No | Yes (click to expand metadata) |
| **Error Handling** | Basic message | Professional error card with retry |
| **Loading State** | Plain text | Spinner animation + message |
| **Empty State** | Simple text | Illustrated empty state with icon |
| **Theme** | Dark only | Dark (default) + light mode ready |
| **Auto-refresh** | Basic | Configurable intervals (1s-10s) |

---

## 📊 Features

### 1. Real-Time Metrics Dashboard

Four KPI cards with live updates and trend indicators:

**Total Chunks**
- Count of all chunks processed
- Icon: Activity (pulse)
- Color: Blue

**Success Rate**
- Percentage of chunks with valid transcripts
- Trend: ↑ (>80%), → (50-80%), ↓ (<50%)
- Icon: CheckCircle
- Color: Green

**Avg Latency**
- Average API response time (last 20 requests)
- Trend: ↑ (<100ms), → (100-300ms), ↓ (>300ms)
- Icon: Zap
- Color: Yellow
- Calculation: `performance.now()` before/after fetch

**Total Duration**
- Sum of all chunk durations
- Icon: Clock
- Color: Purple

### 2. Timeline Trace Visualization

Distributed tracing-style timeline showing:
- **Visual spans**: Each chunk as a horizontal bar
- **Color coding**: Green (valid transcript), Yellow (empty)
- **Proportional width**: Chunk duration relative to total
- **Position**: Start timestamp aligned on timeline
- **Hover tooltip**: Chunk number + timestamp range
- **Toggle button**: Eye icon to show/hide tracing

### 3. Chunk Details with Expandable Metadata

**Collapsed state (default):**
- Chunk number (#00, #01, etc.)
- Status badge (✓ Valid / ⚠ Empty / ✗ Invalid)
- Duration + Language
- Transcript preview (2 lines max, clamped)
- Play button

**Expanded state (click chevron):**
- Full transcript in monospace font
- Metadata grid (4 cells):
  - Audio Hash (SHA256, truncated)
  - Timestamp Range (start → end)
  - Created At (localized datetime)
  - Language (uppercase)

### 4. Professional Status Badges

**✓ Valid** (Green)
- Has transcript AND duration > 0
- `bg-green-500/20 text-green-400 border-green-500/30`

**⚠ Empty** (Yellow)
- Has duration but NO transcript
- `bg-yellow-500/20 text-yellow-400 border-yellow-500/30`

**✗ Invalid** (Red)
- NO duration (corrupted/failed)
- `bg-red-500/20 text-red-400 border-red-500/30`

### 5. Enhanced Error Handling

**Error card features:**
- AlertTriangle icon
- HTTP status code + message
- Retry button with hover effect
- Red border + dark red background

### 6. Audio Playback

- Play/Pause button per chunk
- Active state: Blue background + shadow glow
- Stops previous audio automatically
- Error handling for 404/network failures

### 7. Controls & Configuration

**Session ID input:**
- Full-width monospace font
- Focus ring (blue 500/50)
- Placeholder text

**Auto-refresh:**
- Checkbox toggle
- Live indicator in header (green pulse)
- Configurable intervals: 1s, 2s, 5s, 10s

**Manual refresh:**
- RefreshCw button in header
- Resets latency tracking

**Tracing toggle:**
- Eye/EyeOff icon button
- Shows/hides timeline visualization

---

## 🎨 Design System

### Color Palette

**Status Colors:**
```typescript
Green (Success):  bg-green-500/20, text-green-400, border-green-500/30
Yellow (Warning): bg-yellow-500/20, text-yellow-400, border-yellow-500/30
Red (Error):      bg-red-500/20, text-red-400, border-red-500/30
Blue (Active):    bg-blue-500, text-white, shadow-blue-500/50
```

**Background Layers:**
```typescript
Primary:   bg-slate-950 (page background)
Card:      bg-slate-800/50 border-slate-700
Nested:    bg-slate-900 (inside cards)
Hover:     hover:bg-slate-700 / hover:border-slate-600
```

**Text Hierarchy:**
```typescript
Heading:   text-2xl font-bold text-slate-50
Subtitle:  text-sm text-slate-400
Label:     text-xs uppercase tracking-wide text-slate-400
Body:      text-sm text-slate-300
Mono:      font-mono text-slate-300
```

### Icons (Lucide React)

```typescript
Activity        - Total chunks, created_at
CheckCircle2    - Success rate, valid status
Zap             - Latency metric
Clock           - Duration, timestamp
Radio           - Empty state icon
FileAudio       - Audio/language indicator
Hash            - Audio hash display
TrendingUp/Down - Metric trends
AlertTriangle   - Error state
RefreshCw       - Manual refresh
Eye/EyeOff      - Toggle tracing
ChevronDown/Right - Expand/collapse
Play/Pause      - Audio controls
```

### Spacing & Layout

**Grid:**
- Metrics: `grid-cols-2 lg:grid-cols-4 gap-4`
- Metadata: `grid-cols-2 gap-3`

**Padding:**
- Cards: `p-4` or `p-5` (controls)
- Nested sections: `p-3`
- Buttons: `px-3 py-2`

**Gaps:**
- Icon+text: `gap-2`
- Horizontal layouts: `gap-3` or `gap-4`
- Vertical stacks: `space-y-3` or `space-y-4`

---

## 📐 Architecture

### State Management

```typescript
// Core data
const [chunks, setChunks] = useState<Chunk[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

// UI state
const [playingChunk, setPlayingChunk] = useState<number | null>(null);
const [expandedChunks, setExpandedChunks] = useState<Set<number>>(new Set());
const [showTracing, setShowTracing] = useState(true);

// Performance tracking
const [latencyHistory, setLatencyHistory] = useState<number[]>([]);
const [lastFetchTime, setLastFetchTime] = useState<number>(0);

// Audio reference
const audioRef = useRef<HTMLAudioElement | null>(null);
```

### Data Flow

```
User Action
    ↓
fetchChunks()
    ↓
performance.now() (start)
    ↓
fetch API
    ↓
performance.now() (end)
    ↓
Calculate latency
    ↓
Update state (chunks, latencyHistory, lastFetchTime)
    ↓
useMemo calculates metrics
    ↓
Component re-renders with new data
```

### Performance Optimizations

1. **useMemo for metrics** - Prevents recalculation on every render
2. **Set for expandedChunks** - O(1) lookup for expansion state
3. **Latency history cap** - Keep last 20 only (`.slice(-19)`)
4. **Conditional rendering** - Timeline only when `showTracing=true`
5. **Single audio ref** - Reuse same Audio element, stop previous

### API Integration

**Endpoint:**
```
GET /internal/transcribe/sessions/{sessionId}/chunks
```

**Response:**
```json
{
  "chunks": [
    {
      "chunk_number": 0,
      "transcript": "Hello world",
      "language": "en",
      "duration": 3.124,
      "audio_hash": "sha256_hash_here",
      "timestamp_start": 0.0,
      "timestamp_end": 3.124,
      "created_at": "2025-11-10T12:34:56.789Z"
    }
  ],
  "total": 1,
  "session_id": "session_20251110_123456"
}
```

**Audio endpoint:**
```
GET /internal/transcribe/sessions/{sessionId}/chunks/{chunkNumber}/audio
```

---

## 🚀 Usage

### Basic Usage

```tsx
import { ChunkBreakdown } from "@/components/ChunkBreakdown";

<ChunkBreakdown
  sessionId="session_20251110_123456"
  autoRefresh={true}
  refreshInterval={2000}
  darkMode={true}
  apiBaseUrl="http://localhost:7001"
/>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `sessionId` | `string` | **required** | Session ID to fetch chunks for |
| `autoRefresh` | `boolean` | `false` | Enable automatic refresh |
| `refreshInterval` | `number` | `2000` | Refresh interval in milliseconds |
| `darkMode` | `boolean` | `true` | Dark theme (light theme planned) |
| `apiBaseUrl` | `string` | `"http://localhost:7001"` | Backend API base URL |

### Advanced: Custom Refresh Intervals

```tsx
// Ultra-fast (1s) - for active recording
<ChunkBreakdown
  sessionId={sessionId}
  autoRefresh={true}
  refreshInterval={1000}
/>

// Slow (10s) - for completed sessions
<ChunkBreakdown
  sessionId={sessionId}
  autoRefresh={true}
  refreshInterval={10000}
/>

// Manual only
<ChunkBreakdown
  sessionId={sessionId}
  autoRefresh={false}
/>
```

---

## 🧪 Testing

### Manual Testing Checklist

**✅ Data Loading:**
- [ ] Loads chunks on mount
- [ ] Shows loading spinner
- [ ] Handles 404 (session not found)
- [ ] Handles 500 (server error)
- [ ] Retry button works on error

**✅ Metrics:**
- [ ] Total chunks count accurate
- [ ] Success rate calculates correctly
- [ ] Latency displays in ms
- [ ] Total duration sums all chunks
- [ ] Trends show correct arrow (↑/→/↓)

**✅ Timeline:**
- [ ] Shows all chunks as horizontal bars
- [ ] Chunk positions align with timestamps
- [ ] Widths proportional to duration
- [ ] Colors match status (green/yellow)
- [ ] Tooltip shows on hover
- [ ] Eye button toggles visibility

**✅ Chunk Details:**
- [ ] Status badge correct (✓/⚠/✗)
- [ ] Expand/collapse works
- [ ] Transcript shows correctly
- [ ] Metadata displays all 4 fields
- [ ] Audio hash truncated
- [ ] Timestamps formatted
- [ ] Created_at localized
- [ ] Language uppercase

**✅ Audio Playback:**
- [ ] Play button starts audio
- [ ] Pause button stops audio
- [ ] Active state shows blue glow
- [ ] Stops previous audio automatically
- [ ] Handles 404 gracefully
- [ ] Audio ends automatically

**✅ Auto-Refresh:**
- [ ] Respects autoRefresh prop
- [ ] Uses correct interval
- [ ] Stops on unmount
- [ ] Updates latency history
- [ ] Updates metrics live

**✅ Performance:**
- [ ] No lag with 20+ chunks
- [ ] Smooth expand/collapse animations
- [ ] Fast metric recalculation
- [ ] Minimal re-renders

### Automated Testing (Future)

```typescript
// Vitest + React Testing Library
describe("ChunkBreakdown", () => {
  it("renders loading state", () => {
    render(<ChunkBreakdown sessionId="test" />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("calculates success rate correctly", () => {
    const chunks = [
      { ...validChunk, transcript: "hello" },
      { ...validChunk, transcript: "" },
    ];
    render(<ChunkBreakdown sessionId="test" chunks={chunks} />);
    expect(screen.getByText("50.0%")).toBeInTheDocument();
  });

  // TODO: Add more tests
});
```

---

## 📚 References

### Inspiration

**Datadog APM:**
- Metric cards with trends
- Timeline trace visualization
- Color-coded status indicators

**Grafana:**
- Grid layout for metrics
- Expandable panels
- Dark theme aesthetics

**New Relic:**
- Performance tracking
- Latency histograms
- Error rate monitoring

### Dependencies

```json
{
  "lucide-react": "^0.263.1",  // Icons
  "react": "^18.2.0",
  "next": "16.0.1"              // Framework
}
```

### Related Files

- **Backend API**: `backend/api/internal/transcribe/router.py`
- **Test Page**: `apps/aurity/app/test-chunks/page.tsx`
- **Home Link**: `apps/aurity/components/SlimIndexHub.tsx:151-165`
- **RecordRTC Fix**: `apps/aurity/lib/recording/makeRecorder.ts:95`

---

## 🔮 Future Enhancements

### Planned Features

1. **Audio Waveform Visualization**
   - Use Web Audio API to extract waveform
   - Display inline mini-waveform for each chunk
   - Click to scrub/seek

2. **Advanced Metrics**
   - P50/P95/P99 latency percentiles
   - Error rate over time (sparkline)
   - Chunk size distribution histogram
   - Transcription accuracy score (if available)

3. **Export Capabilities**
   - Export session to JSON
   - Download all chunks as ZIP
   - Generate PDF report with metrics

4. **Real-Time Collaboration**
   - WebSocket connection for live updates
   - Show other users viewing same session
   - Real-time cursor positions

5. **Advanced Filtering**
   - Filter by status (valid/empty/invalid)
   - Search transcripts (fuzzy search)
   - Date range picker
   - Language filter

6. **EBML Header Validation**
   - Client-side header parsing
   - Display codec info (Opus, PCM, etc.)
   - Show segment structure
   - Validate header integrity

7. **Network Waterfall**
   - Show API request timing breakdown
   - DNS → Connection → TLS → Request → Response
   - Identify bottlenecks

8. **Alerts & Notifications**
   - Toast notification on new chunks
   - Browser notification permission
   - Sound alert on errors
   - Slack/Discord webhooks

---

## 🐛 Known Issues

1. **Timeline overflow with 50+ chunks**
   - **Impact**: Vertical scrolling gets unwieldy
   - **Workaround**: Virtualized scrolling (react-window)
   - **Planned fix**: v2.1

2. **Audio playback blocked by browser policy**
   - **Impact**: Play button fails on first click
   - **Workaround**: User gesture required (reload page)
   - **Note**: Chromium autoplay policy

3. **Latency spikes on first request**
   - **Impact**: High latency shown initially
   - **Cause**: Cold start + DNS resolution
   - **Workaround**: Ignore first measurement

---

## 📝 Changelog

### v2.0 (2025-11-10) - Complete Redesign

**Added:**
- 4 real-time KPI metrics with trend indicators
- Timeline trace visualization
- Latency tracking with performance.now()
- Expandable chunk details
- Professional status badges (✓/⚠/✗)
- Enhanced error handling with retry
- Loading spinner animation
- Illustrated empty state
- Toggle tracing button
- Manual refresh button
- Hover effects on all interactive elements

**Changed:**
- Complete UI redesign (Datadog-inspired)
- Dark slate theme (950/900/800/700)
- Typography hierarchy (2xl heading → xs labels)
- Spacing system (gap-2 to gap-4)
- Icon set (lucide-react, 15+ icons)

**Improved:**
- Performance (useMemo for metrics)
- Accessibility (proper labels, focus rings)
- Responsiveness (grid-cols-2 lg:grid-cols-4)
- Code organization (StatusBadge, MetricCard, TimelineView components)

**Removed:**
- Basic list layout
- Simple text labels
- Inline status icons (replaced with badges)

### v1.0 (2025-11-09) - Initial Release

**Added:**
- Basic chunk list
- Play/pause audio
- Transcript display
- Auto-refresh capability

---

## 🎓 Development Notes

### Component Design Patterns

1. **Composition over props**
   - StatusBadge, MetricCard, TimelineView as internal components
   - Easier to test and maintain

2. **Controlled vs Uncontrolled**
   - Controlled: Audio playback, expansion state
   - Uncontrolled: Audio element itself

3. **Data fetching**
   - Fetch on mount + auto-refresh
   - No external state management (useState only)
   - Could migrate to React Query for caching

4. **Styling approach**
   - Tailwind utility classes only
   - No CSS modules or styled-components
   - Dark mode via className conditionals

### Performance Considerations

- **Metrics calculation**: O(n) where n = chunk count
- **Timeline rendering**: O(n) divs + CSS transforms
- **Latency history**: Fixed size (20), O(1) operations
- **Re-renders**: Optimized with useMemo, minimal

### Accessibility

- **Keyboard navigation**: Tab through buttons
- **Focus indicators**: Blue ring on focus
- **ARIA labels**: "Play chunk 0", "Retry loading"
- **Screen reader**: Status badges announce "Valid", "Empty", etc.
- **Color contrast**: WCAG AA compliant (4.5:1 minimum)

---

**Last Updated**: 2025-11-10
**Maintainer**: Aurity Team
**License**: Internal Use Only
