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
      className={`pol-banner-root ${
        isVisible ? 'pol-banner-visible' : 'pol-banner-hidden'
      }`}
    >
      <div className="pol-banner-container">
        <div className="fi-flex-between">
          {/* Data Sovereignty Principles */}
          <div className="pol-banner-principles">
            {/* Local-First */}
            <div className="fi-flex-gap">
              <Shield className="pol-banner-icon fi-text-success" />
              <span className="pol-banner-label">
                100% Local
              </span>
              <span className="pol-banner-desc">
                No cloud dependencies
              </span>
            </div>

            {/* HIPAA Ready */}
            <div className="fi-flex-gap">
              <Lock className="pol-banner-icon fi-text-success" />
              <span className="pol-banner-label">
                HIPAA Ready
              </span>
              <span className="pol-banner-desc">
                AES-GCM-256
              </span>
            </div>

            {/* Immutable Storage */}
            <div className="fi-flex-gap">
              <Database className="pol-banner-icon fi-text-success" />
              <span className="pol-banner-label">
                Append-Only
              </span>
              <span className="pol-banner-desc">
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
            className="pol-banner-dismiss"
            title="Dismiss"
            aria-label="Dismiss banner"
          />
        </div>
      </div>
    </div>
  );
}
