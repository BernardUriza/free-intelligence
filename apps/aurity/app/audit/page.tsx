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
    <div className="min-h-screen bg-slate-950">
      <PageHeader {...headerConfig} />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">

        {/* Filters */}
        <div className="bg-slate-800 rounded-lg p-4 mb-6 flex flex-col sm:flex-row gap-4">
          {/* Operation Filter */}
          <div className="flex-1">
            <label className="block text-sm font-medium fi-text mb-2">
              Operation Type
            </label>
            <Select value={selectedOperation} onValueChange={handleOperationFilter}>
              <SelectTrigger className="w-full">
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
          <div className="flex-1">
            <label className="block text-sm font-medium fi-text mb-2">
              Date Range
            </label>
            <Select value={dateRange} onValueChange={handleDateRangeFilter}>
              <SelectTrigger className="w-full">
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
          <div className="bg-red-900/20 border border-red-700 fi-text-error px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
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
          <div className="bg-slate-800 rounded-lg p-12 text-center">
            <p className="text-slate-400 text-lg">No audit logs found</p>
            <p className="text-slate-500 text-sm mt-2">
              Try adjusting your filters or check back later
            </p>
          </div>
        )}

        {/* Detail Modal */}
        {selectedLog && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            onClick={handleCloseDetail}
          >
            <div
              className="bg-slate-800 rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-bold text-slate-50">Event Detail</h2>
                <button
                  onClick={handleCloseDetail}
                  className="text-slate-400 hover:text-slate-200"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="fi-subtitle">Audit ID</div>
                  <div className="text-slate-100 font-mono text-sm">{selectedLog.audit_id}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Timestamp</div>
                  <div className="text-slate-100">{new Date(selectedLog.timestamp).toLocaleString()}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Operation</div>
                  <div className="text-slate-100">{selectedLog.operation}</div>
                </div>

                <div>
                  <div className="fi-subtitle">User</div>
                  <div className="text-slate-100">{selectedLog.user_id}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Endpoint</div>
                  <div className="text-slate-100 font-mono text-sm">{selectedLog.endpoint}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Status</div>
                  <div className={`inline-block px-2 py-1 rounded text-sm ${
                    selectedLog.status === "SUCCESS" ? "bg-green-900/30 fi-text-green" :
                    selectedLog.status === "FAILED" ? "bg-red-900/30 fi-text-error" :
                    "bg-yellow-900/30 text-yellow-400"
                  }`}>
                    {selectedLog.status}
                  </div>
                </div>

                <div>
                  <div className="fi-subtitle">Payload Hash</div>
                  <div className="text-slate-100 font-mono text-xs break-all">{selectedLog.payload_hash}</div>
                </div>

                <div>
                  <div className="fi-subtitle">Result Hash</div>
                  <div className="text-slate-100 font-mono text-xs break-all">{selectedLog.result_hash}</div>
                </div>

                {selectedLog.metadata && selectedLog.metadata !== "{}" && (
                  <div>
                    <div className="fi-subtitle mb-2">Metadata</div>
                    <pre className="bg-slate-900 fi-text p-3 rounded text-xs overflow-x-auto">
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
