"use client";

/**
 * Progress Monitor Component - Phase 6 (FI-ONBOARD-007)
 *
 * Real-time progress visualization with ASCII art
 * Mimics /api/workflows/aurity/sessions/{id}/monitor
 */

import { motion, AnimatePresence } from "framer-motion";
import { Clock, Zap, CheckCircle, XCircle, BarChart3 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ASCII_ART } from "@/lib/simulation-data";

export type TaskType = 'TRANSCRIPTION' | 'DIARIZATION' | 'SOAP_GENERATION' | 'ENCRYPTION';
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface TaskProgress {
  type: TaskType;
  status: TaskStatus;
  progress: number; // 0-100
  current_chunk?: number;
  total_chunks?: number;
  message?: string;
}

interface ProgressMonitorProps {
  tasks: TaskProgress[];
  currentMessage?: string;
}

/**
 * Get color scheme for task type
 */
const getTaskColor = (type: TaskType): string => {
  switch (type) {
    case 'TRANSCRIPTION':
      return 'fi-text-info';
    case 'DIARIZATION':
      return 'fi-text-purple';
    case 'SOAP_GENERATION':
      return 'fi-text-success';
    case 'ENCRYPTION':
      return 'fi-text-error';
  }
};

/**
 * Get background color for task status
 */
const getStatusBg = (status: TaskStatus): string => {
  switch (status) {
    case 'pending':
      return 'bg-slate-800/40';
    case 'in_progress':
      return 'bg-cyan-900/30 border-cyan-500/30';
    case 'completed':
      return 'bg-emerald-900/30 border-emerald-500/30';
    case 'error':
      return 'bg-red-900/30 border-red-500/30';
  }
};

/**
 * Get status icon
 */
const getStatusIcon = (status: TaskStatus): LucideIcon => {
  switch (status) {
    case 'pending':
      return Clock;
    case 'in_progress':
      return Zap;
    case 'completed':
      return CheckCircle;
    case 'error':
      return XCircle;
  }
};

/**
 * Render ASCII progress bar for chunks
 */
const renderChunkProgressBar = (current: number, total: number): JSX.Element => {
  const blocks = Array.from({ length: total }, (_, i) => {
    if (i < current) {
      return ASCII_ART.chunk_success;
    } else if (i === current) {
      return ASCII_ART.chunk_in_progress;
    } else {
      return ASCII_ART.chunk_pending;
    }
  });

  return (
    <div className="font-mono text-sm flex gap-1">
      {blocks.map((block, idx) => (
        <span
          key={idx}
          className={`${
            block === ASCII_ART.chunk_success
              ? 'fi-text-success'
              : block === ASCII_ART.chunk_in_progress
              ? 'fi-text-info animate-pulse'
              : 'text-slate-600'
          }`}
        >
          {block}
        </span>
      ))}
      <span className="text-slate-500 ml-2">
        {current}/{total}
      </span>
    </div>
  );
};

export function ProgressMonitor({ tasks, currentMessage }: ProgressMonitorProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between fi-border-bottom/50 pb-3">
        <h3 className="text-lg font-semibold text-slate-200 font-mono flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-cyan-400" />
          Progress Monitor
        </h3>
        <div className="flex items-center gap-2 fi-text-xs">
          <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
          <span>Live</span>
        </div>
      </div>

      {/* Current Message (if any) */}
      <AnimatePresence mode="wait">
        {currentMessage && (
          <motion.div
            key={currentMessage}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.3 }}
            className="p-3 bg-cyan-950/20 border border-cyan-700/30 rounded-lg"
          >
            <p className="text-sm text-cyan-300 font-mono flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-400" />
              {currentMessage}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Task Cards */}
      <div className="fi-stack-md">
        {tasks.map((task) => (
          <motion.div
            key={task.type}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
            className={`p-4 rounded-xl border-2 transition-all ${getStatusBg(task.status)}`}
          >
            {/* Task Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="fi-flex-gap-md">
                {(() => {
                  const StatusIcon = getStatusIcon(task.status);
                  const iconColor = task.status === 'pending' ? 'text-slate-400' :
                                   task.status === 'in_progress' ? 'text-yellow-400' :
                                   task.status === 'completed' ? 'text-emerald-400' : 'text-red-400';
                  return <StatusIcon className={`w-6 h-6 ${iconColor}`} />;
                })()}
                <div>
                  <p className={`font-semibold text-sm ${getTaskColor(task.type)}`}>
                    {task.type.replace(/_/g, ' ')}
                  </p>
                  <p className="fi-text-xs capitalize">
                    {task.status.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold fi-text">{task.progress}%</p>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="relative w-full h-2 bg-slate-800/60 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${task.progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className={`absolute h-full rounded-full ${
                  task.status === 'completed'
                    ? 'bg-emerald-500'
                    : task.status === 'in_progress'
                    ? 'bg-cyan-500'
                    : task.status === 'error'
                    ? 'bg-red-500'
                    : 'bg-slate-600'
                }`}
              />
            </div>

            {/* Chunk Progress (for TRANSCRIPTION) */}
            {task.type === 'TRANSCRIPTION' && task.current_chunk !== undefined && task.total_chunks && (
              <div className="mt-3 p-2 bg-slate-950/40 rounded-lg">
                {renderChunkProgressBar(task.current_chunk, task.total_chunks)}
              </div>
            )}

            {/* Task Message */}
            {task.message && (
              <div className="mt-3">
                <p className="fi-text-xs font-mono">{task.message}</p>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-6 p-4 bg-slate-900/60 border border-slate-700/50 rounded-xl">
        <p className="text-xs font-semibold fi-text mb-2">ASCII Legend:</p>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div className="fi-flex-gap">
            <span className="fi-text-success">{ASCII_ART.chunk_success}</span>
            <span className="text-slate-400">Completed chunk</span>
          </div>
          <div className="fi-flex-gap">
            <span className="fi-text-info">{ASCII_ART.chunk_in_progress}</span>
            <span className="text-slate-400">In progress</span>
          </div>
          <div className="fi-flex-gap">
            <span className="text-slate-600">{ASCII_ART.chunk_pending}</span>
            <span className="text-slate-400">Pending</span>
          </div>
          <div className="fi-flex-gap">
            <span className="text-slate-500">{ASCII_ART.separator}</span>
            <span className="text-slate-400">Separator</span>
          </div>
        </div>
      </div>
    </div>
  );
}
