/**
 * Bryntum Scheduler Pro - Type Definitions
 * 
 * CRITICAL: These types represent the contract between our application
 * and Bryntum SchedulerPro. They are derived from Bryntum's API documentation
 * and ensure type safety throughout our scheduling implementation.
 * 
 * @see https://bryntum.com/products/schedulerpro/docs/
 * @module BryntumTypes
 */

import type { LucideIcon } from 'lucide-react';

// ============================================================================
// Core Bryntum API Types
// ============================================================================

/**
 * Bryntum Event Record
 * Represents a single scheduled event/appointment in the timeline.
 */
export interface BryntumEvent {
  id: string | number;
  resourceId: string | number;
  startDate: Date | string;
  endDate: Date | string;
  name?: string;
  eventColor?: string;
  cls?: string;
  iconCls?: string;
  eventStyle?: 'plain' | 'border' | 'colored' | 'hollow' | 'line' | 'dashed';
  
  // Custom metadata (app-specific)
  [key: string]: unknown;
}

/**
 * Bryntum Resource (row in the scheduler)
 * Represents a resource that can have events assigned (e.g., doctor, room, chat channel)
 */
export interface BryntumResource {
  id: string | number;
  name: string;
  eventColor?: string;
  eventStyle?: string;
  image?: string;
  iconCls?: string;
  
  // Custom metadata
  [key: string]: unknown;
}

/**
 * Bryntum Event Store Configuration
 */
export interface BryntumEventStore {
  data: BryntumEvent[];
  listeners?: Record<string, (event: unknown) => void>;
}

/**
 * Bryntum Resource Store Configuration
 */
export interface BryntumResourceStore {
  data: BryntumResource[];
  listeners?: Record<string, (event: unknown) => void>;
}

/**
 * View Preset Header Configuration
 */
export interface ViewPresetHeader {
  unit: 'millisecond' | 'second' | 'minute' | 'hour' | 'day' | 'week' | 'month' | 'quarter' | 'year';
  dateFormat: string;
  align?: 'start' | 'center' | 'end';
}

/**
 * View Preset Configuration
 * Defines how time is displayed and navigated in the scheduler.
 */
export interface ViewPresetDefinition {
  base?: string;
  tickWidth?: number;
  tickHeight?: number;
  displayDateFormat?: string;
  shiftIncrement?: number;
  shiftUnit?: 'millisecond' | 'second' | 'minute' | 'hour' | 'day' | 'week' | 'month' | 'quarter' | 'year';
  timeResolution?: {
    unit: string;
    increment: number;
  };
  headers?: ViewPresetHeader[];
}

/**
 * Column Configuration
 */
export interface ColumnConfig {
  type?: string;
  text?: string;
  field?: string;
  width?: number;
  flex?: number;
  align?: 'left' | 'center' | 'right';
  renderer?: (params: { value: unknown; record: unknown }) => string;
  showImage?: boolean;
  editor?: unknown;
  hidden?: boolean;
  locked?: boolean;
  resizable?: boolean;
  sortable?: boolean;
}

/**
 * Feature: Event Tooltip Configuration
 */
export interface EventTooltipFeature {
  disabled?: boolean;
  template?: (data: { eventRecord: { data: Record<string, unknown> } }) => string;
  align?: string;
  anchorToTarget?: boolean;
}

/**
 * Feature: Event Drag Configuration
 */
export interface EventDragFeature {
  disabled?: boolean;
  constrainDragToResource?: boolean;
  constrainDragToTimeSlot?: boolean;
  showTooltip?: boolean;
  showExactDropPosition?: boolean;
}

/**
 * Feature: Event Resize Configuration
 */
export interface EventResizeFeature {
  disabled?: boolean;
  showTooltip?: boolean;
  showExactResizePosition?: boolean;
}

/**
 * Feature: Event Edit Configuration
 */
export interface EventEditFeature {
  disabled?: boolean;
  editorConfig?: unknown;
  items?: Record<string, unknown>;
  saveAndCloseOnEnter?: boolean;
  triggerEvent?: 'eventclick' | 'eventdblclick';
}

/**
 * Feature: Time Ranges Configuration
 */
export interface TimeRangesFeature {
  disabled?: boolean;
  showCurrentTimeLine?: boolean;
  showHeaderElements?: boolean;
  currentDateFormat?: string;
}

/**
 * Feature: Dependencies Configuration
 */
export interface DependenciesFeature {
  disabled?: boolean;
  allowCreate?: boolean;
  radius?: number;
}

/**
 * Feature: Event Context Menu Configuration
 */
export interface EventMenuFeature {
  disabled?: boolean;
  items?: Record<string, unknown>;
  processItems?: (params: { items: unknown; eventRecord: unknown }) => void;
}

/**
 * Feature: Event Drag Create Configuration
 * Allows creating new events by dragging on the schedule
 */
export interface EventDragCreateFeature {
  disabled?: boolean;
  showTooltip?: boolean;
  validatorFn?: (context: unknown) => boolean | string;
}

/**
 * All Scheduler Features
 */
/**
 * Feature: Non-Working Time Configuration
 * Visually distinguish and optionally restrict non-working hours
 */
export interface NonWorkingTimeFeature {
  disabled?: boolean;
  enableResizeToNonWorking?: boolean;
  enableDragToNonWorking?: boolean;
}

export interface SchedulerFeatures {
  eventDrag?: boolean | EventDragFeature;
  eventDragCreate?: boolean | EventDragCreateFeature;
  eventResize?: boolean | EventResizeFeature;
  eventEdit?: boolean | EventEditFeature;
  eventTooltip?: boolean | EventTooltipFeature;
  timeRanges?: boolean | TimeRangesFeature;
  dependencies?: boolean | DependenciesFeature;
  eventMenu?: boolean | EventMenuFeature;
  nonWorkingTime?: boolean | NonWorkingTimeFeature;
  resourceTimeRanges?: boolean;
  scheduleTooltip?: boolean;
  cellEdit?: boolean;
  cellMenu?: boolean;
  columnPicker?: boolean;
  columnReorder?: boolean;
  columnResize?: boolean;
  group?: boolean;
  sort?: boolean;
  stripe?: boolean;
  timeAxisHeaderMenu?: boolean;
  tree?: boolean;
}

/**
 * Scheduler Event Listeners
 */
export interface SchedulerListeners {
  eventClick?: (event: { eventRecord: { data: Record<string, unknown> } }) => void;
  eventDblClick?: (event: { eventRecord: { data: Record<string, unknown> } }) => void;
  eventContextMenu?: (event: { eventRecord: { data: Record<string, unknown> } }) => void;
  beforeEventEdit?: (event: { eventRecord: unknown }) => boolean;
  afterEventEdit?: (event: { eventRecord: unknown }) => void;
  beforeEventDrag?: (event: { eventRecords: unknown[] }) => boolean;
  afterEventDrop?: (event: { eventRecords: unknown[] }) => void;
  scheduleClick?: (event: { date: Date; resourceRecord: unknown }) => void;
  scheduleDblClick?: (event: { date: Date; resourceRecord: unknown }) => void;
}

/**
 * Complete Bryntum SchedulerPro Configuration
 */
export interface BryntumSchedulerConfig {
  // Container
  appendTo?: HTMLElement | string;
  
  // Time axis
  startDate?: Date | string;
  endDate?: Date | string;
  viewPreset?: string | ViewPresetDefinition;
  
  // Layout
  rowHeight?: number;
  barMargin?: number;
  width?: number | string;
  height?: number | string;
  
  // Data
  events?: BryntumEvent[] | BryntumEventStore;
  resources?: BryntumResource[] | BryntumResourceStore;
  columns?: ColumnConfig[];
  
  // Features
  features?: SchedulerFeatures;
  
  // Event listeners
  listeners?: SchedulerListeners;
  
  // Other configurations
  readOnly?: boolean;
  allowOverlap?: boolean;
  eventColor?: string;
  eventStyle?: 'plain' | 'border' | 'colored' | 'hollow' | 'line' | 'dashed';
  enableEventAnimations?: boolean;
  useInitialAnimation?: boolean;
  zoomOnMouseWheel?: boolean;
  zoomOnTimeAxisDoubleClick?: boolean;
  
  // Custom configs
  [key: string]: unknown;
}

/**
 * Bryntum SchedulerPro Instance (returned after instantiation)
 */
export interface BryntumSchedulerInstance {
  // Core properties
  startDate: Date;
  endDate: Date;
  viewPreset: string | ViewPresetDefinition;
  tickSize?: number;
  
  // Stores
  eventStore?: BryntumEventStore & {
    data: BryntumEvent[];
    add: (event: BryntumEvent | BryntumEvent[]) => void;
    remove: (event: BryntumEvent | BryntumEvent[]) => void;
    removeAll: () => void;
  };
  resourceStore?: BryntumResourceStore & {
    data: BryntumResource[];
  };
  
  // Zoom
  zoomLevel?: number;
  minZoomLevel?: number;
  maxZoomLevel?: number;

  // Methods
  destroy?: () => void;
  scrollToDate?: (date: Date, options?: { animate?: boolean; block?: string }) => void;
  scrollToNow?: (options?: { animate?: boolean }) => void;
  zoomIn?: (levels?: number) => void;
  zoomOut?: (levels?: number) => void;
  zoomToLevel?: (level: number) => void;
  zoomToSpan?: (config: { startDate: Date; endDate: Date }) => void;
  
  // Any other Bryntum properties
  [key: string]: unknown;
}

// ============================================================================
// Application-Specific Types
// ============================================================================

/**
 * View Mode for Timeline Scheduler
 */
export type ViewMode = 'day' | 'week' | 'month';

/**
 * View Preset Configuration with Navigation Logic
 * Extends Bryntum's ViewPresetDefinition with app-specific navigation
 */
export interface ViewPresetConfig {
  id: string;
  label: string;
  icon: LucideIcon;
  preset: ViewPresetDefinition;
  getDateRange: (date: Date) => { start: Date; end: Date };
  navigationUnit: 'day' | 'week' | 'month';
  dateFormat: Intl.DateTimeFormatOptions;
}

/**
 * Unified Event Type (from longitudinal memory API)
 * This is what we receive from the backend and transform into BryntumEvent
 * 
 * NOTE: This is an alias for MemoryEvent from @/lib/api/longitudinal-memory
 * We keep this alias for Bryntum-specific context, but the actual type
 * should be imported from the API client for consistency.
 */
export interface UnifiedEvent {
  id: string;
  timestamp: number; // Unix timestamp
  content: string;
  event_type: 'chat_user' | 'chat_assistant' | 'transcription';
  source: 'chat' | 'audio';
  session_id?: string | null;
  persona?: string | null;
  confidence?: number | null;
  language?: string | null;
  duration?: number | null; // For audio events
  chunk_number?: number | null;
  stt_provider?: string | null;
}

/**
 * Event Transformation Result
 * Represents a UnifiedEvent converted to Bryntum format
 */
export interface TransformedBryntumEvent extends BryntumEvent {
  content: string;
  event_type: string;
  timestamp: number;
  duration?: number;
  originalEvent: UnifiedEvent;
}

/**
 * Scheduler State
 */
export interface SchedulerState {
  isReady: boolean;
  viewMode: ViewMode;
  currentDate: Date;
  zoomLevel: number;
  selectedSession: string | null;
  searchQuery: string;
}

/**
 * Scheduler Actions
 */
export interface SchedulerActions {
  setViewMode: (mode: ViewMode) => void;
  navigateDate: (direction: 'prev' | 'next') => void;
  goToToday: () => void;
  jumpToLatestEvent: () => void;
  handleZoom: (direction: 'in' | 'out') => void;
  setSearchQuery: (query: string) => void;
  setSelectedSession: (sessionId: string | null) => void;
}

/**
 * Scheduler Callbacks
 */
export interface SchedulerCallbacks {
  onEventClick?: (event: UnifiedEvent) => void;
  onScheduleClick?: (date: Date, resource: BryntumResource) => void;
  onViewChange?: (mode: ViewMode) => void;
  onDateChange?: (date: Date) => void;
}
