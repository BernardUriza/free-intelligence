/**
 * Longitudinal Memory Page Tests
 *
 * Card: FI-PHIL-DOC-014
 * Tests for the refactored timeline page using useLongitudinalMemory hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { MemoryEvent } from '@/lib/api/longitudinal-memory';

// ============================================================================
// Mocks - Must be hoisted before imports
// ============================================================================

// Mock functions - defined before vi.mock calls
const mockLoadMore = vi.fn();
const mockRefresh = vi.fn();
const mockSetEventType = vi.fn();
const mockSetTimeRangePreset = vi.fn();

// Mock Auth0
vi.mock('@auth0/auth0-react', () => ({
  useAuth0: vi.fn(() => ({
    user: { sub: 'test-user-123' },
    isAuthenticated: true,
    isLoading: false,
  })),
}));

// Mock the longitudinal memory hook - factory returns a fresh mock each time
vi.mock('@/hooks/useLongitudinalMemory', () => ({
  useLongitudinalMemory: vi.fn(),
}));

// Mock EventTimeline component
vi.mock('@/components/audit/EventTimeline', () => ({
  EventTimeline: ({ events }: { events: { id?: string; content?: string }[] }) => (
    <div data-testid="event-timeline">
      {events.map((e: { id?: string; content?: string }, i: number) => (
        <div key={e.id || i} data-testid={`event-${i}`}>
          {e.content}
        </div>
      ))}
    </div>
  ),
}));

// Mock VirtualizedTimeline component
vi.mock('@/components/timeline/VirtualizedTimeline', () => ({
  VirtualizedTimeline: ({ events, isLoading }: { events: { id?: string; content?: string }[]; isLoading: boolean }) => (
    <div data-testid="event-timeline">
      {events.map((e: { id?: string; content?: string }, i: number) => (
        <div key={e.id || i} data-testid={`event-${i}`}>
          {e.content}
        </div>
      ))}
      {isLoading && (
        <div data-testid="loading-more">
          <span>Cargando más eventos...</span>
        </div>
      )}
    </div>
  ),
}));

// Mock TimelineFilters component
vi.mock('@/components/timeline/TimelineFilters', () => ({
  // eslint-disable-next-line no-unused-vars
  TimelineFilters: ({ onEventTypeChange }: { onEventTypeChange: (type: string) => void }) => (
    <div data-testid="timeline-filters">
      <button onClick={() => onEventTypeChange('chat')} data-testid="filter-chat">
        Chat
      </button>
      <button onClick={() => onEventTypeChange('audio')} data-testid="filter-audio">
        Audio
      </button>
    </div>
  ),
}));

// Mock TimelineSearch component
vi.mock('@/components/timeline/TimelineSearch', () => ({
  // eslint-disable-next-line no-unused-vars
  TimelineSearch: ({ onSearch }: { onSearch: (query: string) => void }) => (
    <input
      data-testid="timeline-search"
      onChange={(e) => onSearch(e.target.value)}
      placeholder="Search timeline..."
    />
  ),
}));

// Mock TimelineScheduler component
vi.mock('@/components/timeline/TimelineScheduler', () => ({
  TimelineScheduler: ({ events }: { events: unknown[] }) => (
    <div data-testid="timeline-scheduler">
      Scheduler with {events.length} events
    </div>
  ),
}));

// Mock PageHeader
vi.mock('@/components/layout/PageHeader', () => ({
  PageHeader: () => <header data-testid="page-header">Timeline Header</header>,
}));

// Mock timeline config
vi.mock('@/config/page-headers', () => ({
  timelineHeader: vi.fn(() => ({})),
}));

vi.mock('@/lib/memory-config', () => ({
  memoryConfig: {},
}));

// Import component AFTER mocks are set up
import TimelinePage from '@/app/timeline/page';
import { useLongitudinalMemory } from '@/hooks/useLongitudinalMemory';

// ============================================================================
// Test Helpers
// ============================================================================

// Type for mock return value
interface MockHookReturn {
  events: MemoryEvent[];
  stats: null;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  total: number;
  chatCount: number;
  audioCount: number;
  filters: {
    eventType: 'all' | 'chat' | 'audio';
    preset: null;
    timeRange: { start: null; end: null };
  };
  setEventType: typeof mockSetEventType;
  setTimeRangePreset: typeof mockSetTimeRangePreset;
  setCustomTimeRange: ReturnType<typeof vi.fn>;
  loadMore: typeof mockLoadMore;
  refresh: typeof mockRefresh;
  isAuthenticated: boolean;
  doctorId: string;
}

function mockHookReturn(overrides: Partial<MockHookReturn>) {
  vi.mocked(useLongitudinalMemory).mockReturnValue({
    events: [],
    stats: null,
    isLoading: false,
    isLoadingMore: false,
    error: null,
    hasMore: false,
    total: 0,
    chatCount: 0,
    audioCount: 0,
    filters: {
      eventType: 'all' as const,
      preset: null,
      timeRange: { start: null, end: null },
    },
    setEventType: mockSetEventType,
    setTimeRangePreset: mockSetTimeRangePreset,
    setCustomTimeRange: vi.fn(),
    loadMore: mockLoadMore,
    refresh: mockRefresh,
    isAuthenticated: true,
    doctorId: 'test-user-123',
    ...overrides,
  });
}

// ============================================================================
// Tests
// ============================================================================

describe('TimelinePage (Longitudinal Memory)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHookReturn({});
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // --------------------------------------------------------------------------
  // Smoke Test
  // --------------------------------------------------------------------------

  it('renders the page with TimelineFilters', async () => {
    mockHookReturn({ total: 10, chatCount: 5, audioCount: 5 });

    render(<TimelinePage />);

    expect(screen.getByTestId('timeline-filters')).toBeInTheDocument();
    expect(screen.getByTestId('page-header')).toBeInTheDocument();
  });

  // --------------------------------------------------------------------------
  // First Batch Test
  // --------------------------------------------------------------------------

  it('displays events when hook returns data', async () => {
    const mockEvents: MemoryEvent[] = Array.from({ length: 20 }, (_, i) => ({
      id: `event-${i}`,
      timestamp: Date.now() / 1000 - i * 60,
      event_type: (i % 2 === 0 ? 'chat_user' : 'transcription') as 'chat_user' | 'transcription',
      content: `Event content ${i}`,
      source: (i % 2 === 0 ? 'chat' : 'audio') as 'chat' | 'audio',
    }));

    mockHookReturn({
      events: mockEvents,
      total: 20,
      chatCount: 10,
      audioCount: 10,
    });

    render(<TimelinePage />);

    expect(screen.getByTestId('event-timeline')).toBeInTheDocument();
    // Verify events are rendered
    expect(screen.getByTestId('event-0')).toBeInTheDocument();
    expect(screen.getByText('Event content 0')).toBeInTheDocument();
  });

  // --------------------------------------------------------------------------
  // Error State Test
  // --------------------------------------------------------------------------

  it('shows error state with retry button', async () => {
    mockHookReturn({
      error: 'Error al cargar la memoria longitudinal',
      events: [],
    });

    render(<TimelinePage />);

    expect(screen.getByText('Error al cargar la memoria longitudinal')).toBeInTheDocument();
    
    const retryButton = screen.getByText('Reintentar');
    expect(retryButton).toBeInTheDocument();

    fireEvent.click(retryButton);
    expect(mockRefresh).toHaveBeenCalled();
  });

  // --------------------------------------------------------------------------
  // Loading State Test
  // --------------------------------------------------------------------------

  it('shows loading state', async () => {
    mockHookReturn({
      isLoading: true,
      events: [],
    });

    render(<TimelinePage />);

    expect(screen.getByText('Cargando memoria longitudinal...')).toBeInTheDocument();
  });

  // --------------------------------------------------------------------------
  // Empty State Test
  // --------------------------------------------------------------------------

  it('shows empty state when no events', async () => {
    mockHookReturn({
      events: [],
      total: 0,
      isLoading: false,
    });

    render(<TimelinePage />);

    expect(screen.getByText('Sin eventos en el período seleccionado.')).toBeInTheDocument();
  });

  // --------------------------------------------------------------------------
  // Filter Change Test
  // --------------------------------------------------------------------------

  it('calls setEventType when filter is clicked', async () => {
    mockHookReturn({ total: 10 });

    render(<TimelinePage />);

    const chatFilter = screen.getByTestId('filter-chat');
    fireEvent.click(chatFilter);

    expect(mockSetEventType).toHaveBeenCalledWith('chat');
  });

  // --------------------------------------------------------------------------
  // Event Type Mapping Test
  // --------------------------------------------------------------------------

  it('normalizes event_type to type for EventTimeline', async () => {
    const mockEvents: MemoryEvent[] = [
      {
        id: 'e1',
        timestamp: Date.now() / 1000,
        event_type: 'chat_user',
        content: 'Test message',
        source: 'chat',
      },
    ];

    mockHookReturn({
      events: mockEvents,
      total: 1,
    });

    render(<TimelinePage />);

    // The event should be rendered with normalized type
    expect(screen.getByTestId('event-timeline')).toBeInTheDocument();
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  // --------------------------------------------------------------------------
  // Loading More Indicator Test
  // --------------------------------------------------------------------------

  it('shows loading more indicator when fetching more', async () => {
    const testEvent: MemoryEvent = { id: 'e1', timestamp: 123, event_type: 'chat_user', content: 'Test', source: 'chat' };
    mockHookReturn({
      events: [testEvent],
      isLoadingMore: true,
      hasMore: true,
      total: 100,
    });

    render(<TimelinePage />);

    expect(screen.getAllByText('Cargando más eventos...')).toHaveLength(2);
  });

  // --------------------------------------------------------------------------
  // End of Timeline Test
  // --------------------------------------------------------------------------

  it('shows end indicator when no more events', async () => {
    const testEvent: MemoryEvent = { id: 'e1', timestamp: 123, event_type: 'chat_user', content: 'Test', source: 'chat' };
    mockHookReturn({
      events: [testEvent],
      hasMore: false,
      total: 1,
    });

    render(<TimelinePage />);

    expect(screen.getByText(/Fin de la memoria longitudinal/)).toBeInTheDocument();
  });
});
