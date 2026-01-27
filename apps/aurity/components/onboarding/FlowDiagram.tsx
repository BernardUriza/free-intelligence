"use client";

/**
 * Flow Diagram Component - Phase 5 (FI-ONBOARD-006)
 *
 * Animated visualization: Patient Form → HDF5 → Timeline
 */

import { motion } from "framer-motion";
import { FileText, Zap, Database, BarChart3, RefreshCw } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface FlowStep {
  id: number;
  icon: LucideIcon;
  label: string;
  description: string;
  color: string;
}

export function FlowDiagram() {
  const steps: FlowStep[] = [
    {
      id: 1,
      icon: FileText,
      label: "Patient Form",
      description: "Datos del paciente",
      color: "bg-blue-600/20 border-blue-600/40 text-blue-300",
    },
    {
      id: 2,
      icon: Zap,
      label: "Validation",
      description: "Validación en tiempo real",
      color: "bg-purple-600/20 border-purple-600/40 text-purple-300",
    },
    {
      id: 3,
      icon: Database,
      label: "HDF5 Storage",
      description: "/storage/corpus.h5",
      color: "bg-emerald-600/20 border-emerald-600/40 text-emerald-300",
    },
    {
      id: 4,
      icon: BarChart3,
      label: "Timeline",
      description: "Visualización de sesión",
      color: "bg-cyan-600/20 border-cyan-600/40 text-cyan-300",
    },
  ];

  return (
    <div className="fi-stack-xl">
      {/* Title */}
      <div className="text-center">
        <h3 className="fi-section-title flex items-center justify-center gap-2">
          <RefreshCw className="w-5 h-5" /> Flujo de Datos
        </h3>
        <p className="fi-text-xs">
          Desde el formulario hasta la visualización en timeline
        </p>
      </div>

      {/* Flow Steps */}
      <div className="relative">
        <div className="space-y-8">
          {steps.map((step, index) => (
            <div key={step.id} className="relative">
              {/* Connector Line */}
              {index < steps.length - 1 && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: "100%" }}
                  transition={{
                    duration: 0.6,
                    delay: index * 0.4,
                    ease: "easeInOut",
                  }}
                  className="absolute left-6 top-12 w-0.5 bg-gradient-to-b from-slate-600 to-transparent"
                  style={{ height: "3rem" }}
                />
              )}

              {/* Step Card */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: 0.5,
                  delay: index * 0.3,
                  ease: "easeOut",
                }}
                className="relative"
              >
                <div className={`p-4 border-2 rounded-xl ${step.color}`}>
                  <div className="fi-flex-gap-lg">
                    {/* Icon */}
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{
                        duration: 0.3,
                        delay: index * 0.3 + 0.2,
                        type: "spring",
                        stiffness: 200,
                      }}
                      className="flex-shrink-0 w-12 h-12 rounded-full bg-slate-900/60 flex items-center justify-center"
                    >
                      <step.icon className="w-6 h-6" strokeWidth={1.5} />
                    </motion.div>

                    {/* Content */}
                    <div className="flex-1">
                      <p className="font-semibold text-sm">{step.label}</p>
                      <p className="fi-text-xs mt-1">{step.description}</p>
                    </div>

                    {/* Step Number */}
                    <motion.div
                      initial={{ rotate: -180, opacity: 0 }}
                      animate={{ rotate: 0, opacity: 1 }}
                      transition={{
                        duration: 0.4,
                        delay: index * 0.3 + 0.3,
                      }}
                      className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-800/60 flex items-center justify-center text-xs font-bold fi-text border border-slate-700/50"
                    >
                      {step.id}
                    </motion.div>
                  </div>
                </div>
              </motion.div>
            </div>
          ))}
        </div>
      </div>

      {/* Additional Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 1.2 }}
        className="p-4 bg-slate-900/60 border border-slate-700/50 rounded-xl"
      >
        <p className="text-xs fi-text flex items-start gap-2">
          <Zap className="w-4 h-4 fi-text-success flex-shrink-0 mt-0.5" />
          <span><strong className="fi-text-success">Real-time:</strong> Cada cambio en el formulario
          actualiza inmediatamente el preview HDF5. La estructura se guarda localmente en tu navegador
          para esta demo.</span>
        </p>
      </motion.div>
    </div>
  );
}
