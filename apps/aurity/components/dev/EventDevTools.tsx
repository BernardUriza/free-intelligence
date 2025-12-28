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
  Pause,
  Play,
  RefreshCw,
  Trash2,
  X,
  Wifi,
  WifiOff,
} from "lucide-react";

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
const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7001";
const EVENT_COLORS: Record<string, string> = {
  TRANSCRIPTION_STARTED: "bg-green-500",
  TRANSCRIPTION_CHUNK_RECEIVED: "bg-blue-500",
  TRANSCRIPTION_ENDED: "bg-green-600",
  TRANSCRIPTION_FAILED: "bg-red-500",
  SOAP_GENERATION_STARTED: "bg-purple-500",
  SOAP_GENERATION_COMPLETED: "bg-purple-600",
  SESSION_FINALIZED: "bg-yellow-500",
  heartbeat: "bg-gray-400",
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

    const url = `${API_BASE}/api/workflows/events/sse/${sessionId}`;
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
      const res = await fetch(`${API_BASE}/api/workflows/events/metrics/summary`);
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error("Failed to fetch metrics:", err);
    }
  }, []);

  // Fetch projections
  const fetchProjections = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/workflows/events/projections`);
      if (res.ok) {
        const data = await res.json();
        setProjections(data);
      }
    } catch (err) {
      console.error("Failed to fetch projections:", err);
    }
  }, []);

  // Trigger replay
  const triggerReplay = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(`${API_BASE}/api/workflows/events/replay/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        alert(`Replay completed: ${data.event_count} events, ${data.replay_duration_ms}ms`);
      }
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
    "bottom-right": "bottom-4 right-4",
    "bottom-left": "bottom-4 left-4",
    "top-right": "top-4 right-4",
    "top-left": "top-4 left-4",
  };

  return (
    <div
      className={`fixed ${positionClasses[position]} z-50 font-mono text-xs`}
      style={{ maxWidth: isExpanded ? "480px" : "auto" }}
    >
      {/* Collapsed button */}
      {!isExpanded && (
        <Button
          onClick={() => setIsExpanded(true)}
          className="flex items-center gap-2 px-3 py-2 bg-gray-900 text-gray-100 rounded-lg shadow-lg hover:bg-gray-800 transition-colors"
          title="Open Event DevTools"
          variant="ghost"
          size="sm"
          type="button"
        >
          <Activity className="w-4 h-4" />
          <span>Events</span>
          {isConnected && <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />}
        </Button>
      )}

      {/* Expanded panel */}
      {isExpanded && (
        <div className="bg-gray-900 text-gray-100 rounded-lg shadow-2xl overflow-hidden border border-gray-700">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
            <div className="fi-flex-gap">
              <Activity className="w-4 h-4 fi-text-primary" />
              <span className="font-semibold">Event DevTools</span>
              {isConnected ? (
                <Wifi className="fi-icon-xs text-green-500" />
              ) : (
                <WifiOff className="fi-icon-xs text-red-500" />
              )}
            </div>
            <div className="fi-flex-gap-sm">
              <span className="text-gray-500">♥ {heartbeats}</span>
              <Button onClick={() => setIsPaused(!isPaused)} className="p-1 hover:bg-gray-700 rounded" title={isPaused ? "Resume" : "Pause"} variant="ghost" size="sm" type="button">
                {isPaused ? <Play className="fi-icon-xs" /> : <Pause className="fi-icon-xs" />}
              </Button>
              <Button onClick={() => setEvents([])} className="p-1 hover:bg-gray-700 rounded" title="Clear events" variant="ghost" size="sm" type="button">
                <Trash2 className="fi-icon-xs" />
              </Button>
              <Button onClick={() => setIsExpanded(false)} className="p-1 hover:bg-gray-700 rounded" title="Close" variant="ghost" size="sm" type="button">
                <X className="fi-icon-xs" />
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-700">
            {(["events", "metrics", "projections"] as const).map((tab) => (
              <Button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`px-4 py-2 capitalize ${
                  selectedTab === tab
                    ? "bg-gray-800 fi-text-primary border-b-2 border-blue-400"
                    : "text-gray-400 hover:text-gray-200"
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
          <div className="h-64 overflow-hidden">
            {/* Events Tab */}
            {selectedTab === "events" && (
              <div className="h-full flex flex-col">
                {/* Filter */}
                <div className="flex items-center gap-2 p-2 border-b border-gray-700">
                  <Filter className="fi-icon-xs text-gray-400" />
                  <input
                    type="text"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder="Filter events..."
                    className="flex-1 bg-transparent border-none outline-none text-gray-200 placeholder-gray-500"
                  />
                  {sessionId && (
                    <Button
                      onClick={triggerReplay}
                      className="flex items-center gap-1 px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded text-white"
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
                <div ref={eventsContainerRef} className="flex-1 overflow-y-auto p-2 space-y-1">
                  {filteredEvents.length === 0 ? (
                    <div className="text-gray-500 text-center py-8">
                      {sessionId ? "Waiting for events..." : "No session ID provided"}
                    </div>
                  ) : (
                    filteredEvents.map((event) => (
                      <div
                        key={event.event_id}
                        className="flex items-start gap-2 p-2 bg-gray-800 rounded hover:bg-gray-750"
                      >
                        <span
                          className={`w-2 h-2 mt-1 rounded-full ${
                            EVENT_COLORS[event.event_type] || "bg-gray-500"
                          }`}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="fi-flex-between">
                            <span className="fi-text-primary truncate">{event.event_type}</span>
                            <span className="text-gray-500 text-[10px]">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="text-gray-400 truncate text-[10px]">
                            {event.event_id.substring(0, 16)}...
                          </div>
                          {Object.keys(event.payload).length > 0 && (
                            <pre className="mt-1 text-[10px] text-gray-500 overflow-x-auto">
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
              <div className="p-3 space-y-3 overflow-y-auto h-full">
                {metrics ? (
                  <>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="bg-gray-800 p-2 rounded">
                        <div className="text-gray-400">Published</div>
                        <div className="text-lg fi-text-green">
                          {metrics.total_events_published}
                        </div>
                      </div>
                      <div className="bg-gray-800 p-2 rounded">
                        <div className="text-gray-400">Persisted</div>
                        <div className="text-lg fi-text-primary">
                          {metrics.total_events_persisted}
                        </div>
                      </div>
                      <div className="bg-gray-800 p-2 rounded">
                        <div className="text-gray-400">Failed</div>
                        <div className="text-lg fi-text-error">{metrics.total_events_failed}</div>
                      </div>
                    </div>

                    <div className="bg-gray-800 p-2 rounded">
                      <div className="text-gray-400 mb-2">Events by Type</div>
                      <div className="space-y-1">
                        {Object.entries(metrics.events_by_type).map(([type, count]) => (
                          <div key={type} className="flex justify-between">
                            <span className="text-gray-300">{type}</span>
                            <span className="fi-text-primary">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="text-gray-500 text-center">
                      Uptime: {Math.floor(metrics.uptime_seconds / 60)}m{" "}
                      {Math.floor(metrics.uptime_seconds % 60)}s
                    </div>
                  </>
                ) : (
                  <div className="text-gray-500 text-center py-8">Loading metrics...</div>
                )}
              </div>
            )}

            {/* Projections Tab */}
            {selectedTab === "projections" && (
              <div className="p-3 space-y-2 overflow-y-auto h-full">
                {projections.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">No projections registered</div>
                ) : (
                  projections.map((proj) => (
                    <div key={proj.name} className="bg-gray-800 p-2 rounded">
                      <div className="fi-flex-between">
                        <span className="fi-text-primary">{proj.name}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] ${
                            proj.status === "running"
                              ? "bg-green-900 fi-text-green"
                              : proj.status === "error"
                              ? "bg-red-900 fi-text-error"
                              : "bg-gray-700 text-gray-400"
                          }`}
                        >
                          {proj.status}
                        </span>
                      </div>
                      <div className="flex justify-between text-gray-400 mt-1">
                        <span>Events: {proj.events_processed}</span>
                        {proj.error_count > 0 && (
                          <span className="fi-text-error">Errors: {proj.error_count}</span>
                        )}
                      </div>
                      {proj.last_processed_at && (
                        <div className="text-gray-500 text-[10px] mt-1">
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
            <div className="px-3 py-1 bg-red-900/50 fi-text-error text-[10px]">{lastError}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default EventDevTools;
