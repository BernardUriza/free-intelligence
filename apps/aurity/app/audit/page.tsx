/**
 * Free Intelligence - Audit Log Page
 *
 * /audit route - read-only view of system audit logs with filtering.
 *
 * File: apps/aurity/app/audit/page.tsx
 * Card: FI-UI-FEAT-206
 * Created: 2025-10-30
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { AuditTable } from "../../components/audit/AuditTable";
import { PageHeader } from '@/components/layout/PageHeader';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { auditHeader } from "@/config/page-headers";
import { getAuditLogs, getAuditOperations } from "../../lib/api/audit";
import type { AuditLogEntry, AuditOperation } from "../../types/audit";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [operations, setOperations] = useState<AuditOperation[]>([]);
  const [selectedOperation, setSelectedOperation] = useState<string>("ALL");
  const [dateRange, setDateRange] = useState<string>("24h");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);

  const limit = 100;

  // Callbacks declared before useEffect that uses them
  const loadOperations = useCallback(async () => {
    try {
      const response = await getAuditOperations();
      setOperations(response.operations);
    } catch (err) {
      console.error("Failed to load operations:", err);
    }
  }, []);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getAuditLogs({
        limit,
        operation: selectedOperation === "ALL" ? undefined : selectedOperation,
      });
      setLogs(response.logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [limit, selectedOperation]);

  useEffect(() => {
    loadOperations();
    loadLogs();
  }, [selectedOperation, dateRange, loadOperations, loadLogs]);

  const handleOperationFilter = (operation: string) => {
    setSelectedOperation(operation);
  };

  const handleDateRangeFilter = (range: string) => {
    setDateRange(range);
  };

  const handleSelectLog = (log: AuditLogEntry) => {
    setSelectedLog(log);
  };

  const handleCloseDetail = () => {
    setSelectedLog(null);
  };

  const headerConfig = auditHeader({
    logsCount: logs.length,
    selectedOperation,
  })

  return (
    <div className="aud-page">
      <PageHeader {...headerConfig} />

      <div className="aud-content">

        {/* Filters */}
        <div className="aud-filters">
          {/* Operation Filter */}
          <div className="aud-filter-col">
            <label className="aud-filter-label">
              Operation Type
            </label>
            <Select value={selectedOperation} onValueChange={handleOperationFilter}>
              <SelectTrigger className="aud-filter-select">
                <SelectValue placeholder="All Operations" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Operations</SelectItem>
                {operations.map((op) => (
                  <SelectItem key={op.value} value={op.value}>
                    {op.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Date Range Filter */}
          <div className="aud-filter-col">
            <label className="aud-filter-label">
              Date Range
            </label>
            <Select value={dateRange} onValueChange={handleDateRangeFilter}>
              <SelectTrigger className="aud-filter-select">
                <SelectValue placeholder="Last 24 hours" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="24h">Last 24 hours</SelectItem>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="custom">Custom range</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="aud-error">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="aud-loading">
            <div className="aud-loading-spinner"></div>
          </div>
        )}

        {/* Audit Table */}
        {!loading && logs.length > 0 && (
          <AuditTable
            logs={logs}
            onSelectLog={handleSelectLog}
            selectedLog={selectedLog}
          />
        )}

        {/* Empty State */}
        {!loading && logs.length === 0 && (
          <div className="aud-empty">
            <p className="aud-empty-title">No audit logs found</p>
            <p className="aud-empty-subtitle">
              Try adjusting your filters or check back later
            </p>
          </div>
        )}

        {/* Detail Modal */}
        {selectedLog && (
          <div
            className="aud-modal-overlay"
            onClick={handleCloseDetail}
          >
            <div
              className="aud-modal"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="aud-modal-header">
                <h2 className="aud-modal-title">Event Detail</h2>
                <button
                  onClick={handleCloseDetail}
                  className="aud-modal-close"
                >
                  ✕
                </button>
              </div>

              <div className="aud-modal-body">
                <div>
                  <div className="fi-subtitle">Audit ID</div>
                  <div className="aud-detail-value-mono">{selectedLog.audit_id}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Timestamp</div>
                  <div className="aud-detail-value">{new Date(selectedLog.timestamp).toLocaleString()}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Operation</div>
                  <div className="aud-detail-value">{selectedLog.operation}</div>
                </div>

                <div>
                  <div className="fi-subtitle">User</div>
                  <div className="aud-detail-value">{selectedLog.user_id}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Endpoint</div>
                  <div className="aud-detail-value-mono">{selectedLog.endpoint}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Status</div>
                  <div className={
                    selectedLog.status === "SUCCESS" ? "aud-status-success" :
                    selectedLog.status === "FAILED" ? "aud-status-failed" :
                    "aud-status-warning"
                  }>
                    {selectedLog.status}
                  </div>
                </div>

                <div>
                  <div className="fi-subtitle">Payload Hash</div>
                  <div className="aud-detail-value-hash">{selectedLog.payload_hash}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Result Hash</div>
                  <div className="aud-detail-value-hash">{selectedLog.result_hash}</div>
                </div>

                {selectedLog.metadata && selectedLog.metadata !== "{}" && (
                  <div>
                    <div className="aud-metadata-label">Metadata</div>
                    <pre className="aud-metadata-pre">
                      {JSON.stringify(JSON.parse(selectedLog.metadata), null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
