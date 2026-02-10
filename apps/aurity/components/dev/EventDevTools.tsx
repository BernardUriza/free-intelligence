"use client";

/**
 * Event DevTools - Developer panel for Event Sourcing debugging
 *
 * Features:
 * - Real-time SSE stream visualization
 * - Event filtering by type
 * - Lag indicator
 * - Projection state viewer
 * - Replay trigger button
 *
 * Usage:
 *   import { EventDevTools } from "@/components/dev/EventDevTools";
 *   <EventDevTools sessionId="session-123" />
 *
 * Note: Only shown in development mode
 */

import React, { useEffect, useState, useCallback, useRef } from "react";
import { Button } from '@/components/ui/button';
import {
  Activity,
  Filter,
  Heart,
  Pause,
  Play,
  RefreshCw,
  Trash2,
  X,
  Wifi,
  WifiOff,
} from "lucide-react";
import { api, getBackendUrl } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

// Types
interface EventData {
  event_id: string;
  event_type: string;
  aggregate_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

interface HeartbeatData {
  type: "heartbeat";
  count: number;
  timestamp: string;
}

interface MetricsSummary {
  total_events_published: number;
  total_events_persisted: number;
  total_events_failed: number;
  events_by_type: Record<string, number>;
  uptime_seconds: number;
}

interface ProjectionInfo {
  name: string;
  status: string;
  events_processed: number;
  last_processed_at: string | null;
  error_count: number;
}

// Props
interface EventDevToolsProps {
  sessionId?: string;
  defaultExpanded?: boolean;
  position?: "bottom-right" | "bottom-left" | "top-right" | "top-left";
}

// Constants
const API_BASE = getBackendUrl();
const EVENT_COLORS: Record<string, string> = {
  TRANSCRIPTION_STARTED: "evt-dot-green",
  TRANSCRIPTION_CHUNK_RECEIVED: "evt-dot-blue",
  TRANSCRIPTION_ENDED: "evt-dot-green-dark",
  TRANSCRIPTION_FAILED: "evt-dot-red",
  SOAP_GENERATION_STARTED: "evt-dot-purple",
  SOAP_GENERATION_COMPLETED: "evt-dot-purple-dark",
  SESSION_FINALIZED: "evt-dot-yellow",
  heartbeat: "evt-dot-gray",
};

export function EventDevTools({
  sessionId,
  defaultExpanded = false,
  position = "bottom-right",
}: EventDevToolsProps) {
  // State
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [events, setEvents] = useState<EventData[]>([]);
  const [heartbeats, setHeartbeats] = useState(0);
  const [filter, setFilter] = useState<string>("");
  const [selectedTab, setSelectedTab] = useState<"events" | "metrics" | "projections">("events");
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [projections, setProjections] = useState<ProjectionInfo[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);

  // Refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsContainerRef = useRef<HTMLDivElement>(null);

  // Only show in development
  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  // Connect to SSE stream
  const connect = useCallback(() => {
    if (!sessionId || isPaused) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = `${API_BASE}${ROUTES.workflowEvents}/sse/${sessionId}`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
      setLastError(null);
    };

    eventSource.addEventListener("event", (e) => {
      try {
        const data = JSON.parse(e.data) as EventData;
        setEvents((prev) => [...prev.slice(-99), data]);

        // Auto-scroll to bottom
        if (eventsContainerRef.current) {
          eventsContainerRef.current.scrollTop = eventsContainerRef.current.scrollHeight;
        }
      } catch (err) {
        console.error("Failed to parse event:", err);
      }
    });

    eventSource.addEventListener("heartbeat", (e) => {
      try {
        const data = JSON.parse(e.data) as HeartbeatData;
        setHeartbeats(data.count);
      } catch (err) {
        console.error("Failed to parse heartbeat:", err);
      }
    });

    eventSource.addEventListener("error", (e) => {
      setLastError("Connection error");
      console.error("SSE error:", e);
    });

    eventSource.onerror = () => {
      setIsConnected(false);
    };

    eventSourceRef.current = eventSource;
  }, [sessionId, isPaused]);

  // Disconnect SSE
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Fetch metrics
  const fetchMetrics = useCallback(async () => {
    try {
      const data = await api.get<MetricsSummary>(`${ROUTES.workflowEvents}/metrics/summary`);
      setMetrics(data);
    } catch (err) {
      console.error("Failed to fetch metrics:", err);
    }
  }, []);

  // Fetch projections
  const fetchProjections = useCallback(async () => {
    try {
      const data = await api.get<ProjectionInfo[]>(`${ROUTES.workflowEvents}/projections`);
      setProjections(data);
    } catch (err) {
      console.error("Failed to fetch projections:", err);
    }
  }, []);

  // Trigger replay
  const triggerReplay = useCallback(async () => {
    if (!sessionId) return;

    try {
      const data = await api.get<{ event_count: number; replay_duration_ms: number }>(
        `${ROUTES.workflowEvents}/replay/${sessionId}`
      );
      alert(`Replay completed: ${data.event_count} events, ${data.replay_duration_ms}ms`);
    } catch (err) {
      console.error("Failed to trigger replay:", err);
    }
  }, [sessionId]);

  // Effects
  useEffect(() => {
    if (isExpanded && sessionId && !isPaused) {
      connect();
    } else {
      disconnect();
    }

    return () => disconnect();
  }, [isExpanded, sessionId, isPaused, connect, disconnect]);

  useEffect(() => {
    if (isExpanded && selectedTab === "metrics") {
      fetchMetrics();
      const interval = setInterval(fetchMetrics, 5000);
      return () => clearInterval(interval);
    }
  }, [isExpanded, selectedTab, fetchMetrics]);

  useEffect(() => {
    if (isExpanded && selectedTab === "projections") {
      fetchProjections();
      const interval = setInterval(fetchProjections, 10000);
      return () => clearInterval(interval);
    }
  }, [isExpanded, selectedTab, fetchProjections]);

  // Filter events
  const filteredEvents = events.filter((e) => {
    if (!filter) return true;
    return e.event_type.toLowerCase().includes(filter.toLowerCase());
  });

  // Position classes
  const positionClasses = {
    "bottom-right": "evt-pos-bottom-right",
    "bottom-left": "evt-pos-bottom-left",
    "top-right": "evt-pos-top-right",
    "top-left": "evt-pos-top-left",
  };

  return (
    <div
      className={`evt-container ${positionClasses[position]}`}
      style={{ maxWidth: isExpanded ? "480px" : "auto" }}
    >
      {/* Collapsed button */}
      {!isExpanded && (
        <Button
          onClick={() => setIsExpanded(true)}
          className="evt-collapsed-btn"
          title="Open Event DevTools"
          variant="ghost"
          size="sm"
          type="button"
        >
          <Activity className="evt-icon-sm" />
          <span>Events</span>
          {isConnected && <span className="evt-connected-dot" />}
        </Button>
      )}

      {/* Expanded panel */}
      {isExpanded && (
        <div className="evt-panel">
          {/* Header */}
          <div className="evt-header">
            <div className="fi-flex-gap">
              <Activity className="evt-icon-sm fi-text-primary" />
              <span className="evt-title">Event DevTools</span>
              {isConnected ? (
                <Wifi className="fi-icon-xs evt-wifi-on" />
              ) : (
                <WifiOff className="fi-icon-xs evt-wifi-off" />
              )}
            </div>
            <div className="fi-flex-gap-sm">
              <span className="evt-heartbeat"><Heart className="evt-icon-xs" strokeWidth={1.5} aria-hidden="true" />{heartbeats}</span>
              <Button onClick={() => setIsPaused(!isPaused)} className="evt-header-btn" title={isPaused ? "Resume" : "Pause"} variant="ghost" size="sm" type="button">
                {isPaused ? <Play className="fi-icon-xs" /> : <Pause className="fi-icon-xs" />}
              </Button>
              <Button onClick={() => setEvents([])} className="evt-header-btn" title="Clear events" variant="ghost" size="sm" type="button">
                <Trash2 className="fi-icon-xs" />
              </Button>
              <Button onClick={() => setIsExpanded(false)} className="evt-header-btn" title="Close" variant="ghost" size="sm" type="button">
                <X className="fi-icon-xs" />
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <div className="evt-tabs-row">
            {(["events", "metrics", "projections"] as const).map((tab) => (
              <Button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`evt-tab ${
                  selectedTab === tab
                    ? "evt-tab-active"
                    : "evt-tab-inactive"
                }`}
                variant="ghost"
                size="sm"
                type="button"
                title={tab}
              >
                {tab}
              </Button>
            ))}
          </div>

          {/* Content */}
          <div className="evt-content">
            {/* Events Tab */}
            {selectedTab === "events" && (
              <div className="evt-events-col">
                {/* Filter */}
                <div className="evt-filter-row">
                  <Filter className="fi-icon-xs evt-filter-icon" />
                  <input
                    type="text"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder="Filter events..."
                    className="evt-filter-input"
                  />
                  {sessionId && (
                    <Button
                      onClick={triggerReplay}
                      className="evt-replay-btn"
                      variant="ghost"
                      size="sm"
                      type="button"
                    >
                      <RefreshCw className="fi-icon-xs" />
                      Replay
                    </Button>
                  )}
                </div>

                {/* Event list */}
                <div ref={eventsContainerRef} className="evt-event-list">
                  {filteredEvents.length === 0 ? (
                    <div className="evt-empty-msg">
                      {sessionId ? "Waiting for events..." : "No session ID provided"}
                    </div>
                  ) : (
                    filteredEvents.map((event) => (
                      <div
                        key={event.event_id}
                        className="evt-event-row"
                      >
                        <span
                          className={`evt-dot ${
                            EVENT_COLORS[event.event_type] || "evt-dot-default"
                          }`}
                        />
                        <div className="evt-event-body">
                          <div className="fi-flex-between">
                            <span className="evt-event-type">{event.event_type}</span>
                            <span className="evt-event-time">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="evt-event-id">
                            {event.event_id.substring(0, 16)}...
                          </div>
                          {Object.keys(event.payload).length > 0 && (
                            <pre className="evt-event-payload">
                              {JSON.stringify(event.payload, null, 1)}
                            </pre>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Metrics Tab */}
            {selectedTab === "metrics" && (
              <div className="evt-metrics-body">
                {metrics ? (
                  <>
                    <div className="evt-metrics-grid">
                      <div className="evt-metric-card">
                        <div className="evt-metric-label">Published</div>
                        <div className="evt-metric-value-lg fi-text-green">
                          {metrics.total_events_published}
                        </div>
                      </div>
                      <div className="evt-metric-card">
                        <div className="evt-metric-label">Persisted</div>
                        <div className="evt-metric-value-lg fi-text-primary">
                          {metrics.total_events_persisted}
                        </div>
                      </div>
                      <div className="evt-metric-card">
                        <div className="evt-metric-label">Failed</div>
                        <div className="evt-metric-value-lg fi-text-error">{metrics.total_events_failed}</div>
                      </div>
                    </div>

                    <div className="evt-metric-card">
                      <div className="evt-by-type-title">Events by Type</div>
                      <div className="evt-by-type-list">
                        {Object.entries(metrics.events_by_type).map(([type, count]) => (
                          <div key={type} className="evt-by-type-row">
                            <span className="evt-by-type-name">{type}</span>
                            <span className="fi-text-primary">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="evt-uptime">
                      Uptime: {Math.floor(metrics.uptime_seconds / 60)}m{" "}
                      {Math.floor(metrics.uptime_seconds % 60)}s
                    </div>
                  </>
                ) : (
                  <div className="evt-empty-msg">Loading metrics...</div>
                )}
              </div>
            )}

            {/* Projections Tab */}
            {selectedTab === "projections" && (
              <div className="evt-projections-body">
                {projections.length === 0 ? (
                  <div className="evt-empty-msg">No projections registered</div>
                ) : (
                  projections.map((proj) => (
                    <div key={proj.name} className="evt-proj-card">
                      <div className="fi-flex-between">
                        <span className="fi-text-primary">{proj.name}</span>
                        <span
                          className={`evt-proj-status ${
                            proj.status === "running"
                              ? "evt-proj-running"
                              : proj.status === "error"
                              ? "evt-proj-error"
                              : "evt-proj-idle"
                          }`}
                        >
                          {proj.status}
                        </span>
                      </div>
                      <div className="evt-proj-details">
                        <span>Events: {proj.events_processed}</span>
                        {proj.error_count > 0 && (
                          <span className="fi-text-error">Errors: {proj.error_count}</span>
                        )}
                      </div>
                      {proj.last_processed_at && (
                        <div className="evt-proj-timestamp">
                          Last: {new Date(proj.last_processed_at).toLocaleTimeString()}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          {lastError && (
            <div className="evt-error-bar">{lastError}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default EventDevTools;
