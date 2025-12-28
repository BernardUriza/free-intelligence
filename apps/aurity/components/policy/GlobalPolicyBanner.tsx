"use client";

/**
 * Data Sovereignty Banner
 * Inspired by Aurity Philosophy: Data Sovereignty, HIPAA, Local-first
 *
 * Communicates core principles: 100% Local, HIPAA Ready, Immutable Storage
 * Auto-dismisses after 5 seconds, resets on page navigation
 */

import { useState, useEffect } from "react";
import { Shield, Lock, Database, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function GlobalPolicyBanner() {
  const [dismissed, setDismissed] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  // Auto-dismiss after 5 seconds
  useEffect(() => {
    const fadeOutTimer = setTimeout(() => {
      setIsVisible(false); // Start fade-out animation
    }, 4500); // Start fade 500ms before removal

    const removeTimer = setTimeout(() => {
      setDismissed(true); // Remove from DOM
    }, 5000);

    // Cleanup timers on unmount
    return () => {
      clearTimeout(fadeOutTimer);
      clearTimeout(removeTimer);
    };
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(() => setDismissed(true), 300); // Wait for fade animation
  };

  if (dismissed) {
    return null;
  }

  return (
    <div
      className={`border-b backdrop-blur-sm bg-emerald-900/20 border-emerald-800/50 transition-opacity duration-300 ${
        isVisible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5">
        <div className="fi-flex-between">
          {/* Data Sovereignty Principles */}
          <div className="flex items-center gap-6">
            {/* Local-First */}
            <div className="fi-flex-gap">
              <Shield className="h-4 w-4 fi-text-success" />
              <span className="text-sm font-medium text-emerald-200">
                100% Local
              </span>
              <span className="text-xs text-emerald-300/60">
                No cloud dependencies
              </span>
            </div>

            {/* HIPAA Ready */}
            <div className="fi-flex-gap">
              <Lock className="h-4 w-4 fi-text-success" />
              <span className="text-sm font-medium text-emerald-200">
                HIPAA Ready
              </span>
              <span className="text-xs text-emerald-300/60">
                AES-GCM-256
              </span>
            </div>

            {/* Immutable Storage */}
            <div className="fi-flex-gap">
              <Database className="h-4 w-4 fi-text-success" />
              <span className="text-sm font-medium text-emerald-200">
                Append-Only
              </span>
              <span className="text-xs text-emerald-300/60">
                HDF5 immutable
              </span>
            </div>
          </div>

          {/* Dismiss Button */}
          <Button
            onClick={handleDismiss}
            variant="ghost"
            size="sm"
            icon={X}
            className="text-emerald-300 hover:bg-emerald-800/30"
            title="Dismiss"
            aria-label="Dismiss banner"
          />
        </div>
      </div>
    </div>
  );
}
