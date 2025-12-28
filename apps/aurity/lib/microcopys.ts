/**
 * Microcopys - Free Intelligence
 *
 * Card: FI-UX-STR-001
 * Axiom: Humano = App en Beta
 *
 * All UI copy in a single source of truth.
 * Technical but friendly tone, no corporate fluff.
 */

export const MICROCOPYS = {
  /** Onboarding flow */
  onboarding: {
    welcome: {
      title: "Welcome to Free Intelligence",
      subtitle: "Local-first knowledge management.\nYour data stays on your machine.",
      cta: "Get Started",
    },
    identity: {
      title: "What should we call you?",
      placeholder: "Email or username",
      helper: "No password needed. This identifies your sessions.",
      cta: "Continue",
    },
    firstSession: {
      title: "Your First Session",
      description: "Sessions group related thoughts.\nThink of them as conversation threads.",
      namePlaceholder: "Session name",
      promptPlaceholder: "What's your first thought?",
      cta: "Create Session",
    },
    exportTest: {
      title: "Export Your Data",
      description: "Free Intelligence is local-first.\nYou can export anytime, in any format.",
      formats: {
        json: "JSON (readable, portable)",
        hdf5: "HDF5 (binary, efficient)",
        markdown: "Markdown (human-readable)",
      },
      cta: "Export",
    },
    complete: {
      title: "You're all set!",
      description: "Your first session is ready.\nView it in Timeline or create more.",
      ctaPrimary: "Go to Timeline",
      ctaSecondary: "New Session",
    },
  },

  /** Timeline UI */
  timeline: {
    empty: "No sessions yet.\n\nCreate your first session to start tracking thoughts.",
    loading: "Loading sessions...",
    sessionCard: {
      pinned: "⭐ Pinned",
      lastUpdated: (hours: number) => `Last updated ${hours} hours ago`,
      interactions: (count: number) => `${count} interaction${count !== 1 ? "s" : ""}`,
    },
    actions: {
      expand: "Expand",
      collapse: "Collapse",
      export: "Export",
      verify: "Verify",
      delete: "Delete",
      pin: "Pin",
      tag: "Tag",
      copy: "Copy",
    },
  },

  /** Success messages */
  success: {
    pinned: "⭐ Pinned\n\nInteraction pinned to top of Timeline.",
    tagged: (tags: string[]) => `🏷️ Tagged: ${tags.join(", ")}\n\nTags help filter Timeline.`,
    copied: "📋 Copied to clipboard\n\nInteraction content copied.",
    sessionDeleted: (sessionId: string) =>
      `🗑️ Session deleted\n\n${sessionId} removed from corpus.\n\nUndo not available (append-only policy).`,
  },

  /** Export flow */
  export: {
    progress: {
      title: (sessionId: string) => `Exporting ${sessionId}...`,
      steps: {
        manifest: "Generating manifest...",
        hashing: (current: number, total: number) => `Computing hashes... (${current}/${total})`,
        policies: "Applying policies...",
        writing: "Writing to disk...",
      },
      eta: (seconds: number) => `ETA: ${seconds} seconds`,
    },
    success: {
      title: "✅ Exported!",
      message: (path: string, hash: string) =>
        `Saved to: ${path}\nHash: ${hash.slice(0, 12)}...`,
      ctaPrimary: "View in Finder",
      ctaSecondary: "Verify Export",
    },
  },

  /** Verify flow */
  verify: {
    success: {
      title: "✅ Session verified!",
      badges: {
        hashVerified: "✅ Verified",
        policyCompliant: "✅ Compliant",
        auditLogged: "✅ Logged",
        redactionNA: "N/A",
      },
      message: "No tampering detected.",
      cta: "View in Timeline",
    },
    failed: {
      title: "❌ Verification failed",
      hashMismatch: (expected: string, actual: string) =>
        `Expected hash: ${expected.slice(0, 12)}...\nActual hash:   ${actual.slice(0, 12)}...\n\nThis indicates tampering or corruption.`,
      ctaPrimary: "View Details",
      ctaSecondary: "Report Issue",
    },
  },

  /** Error messages */
  errors: {
    networkTimeout: {
      title: "⚠️ Network timeout",
      message: "Request took >5 seconds.",
      causes: ["LLM API slow", "Large corpus file", "Network congestion"],
      ctaPrimary: "Retry",
      ctaSecondary: "Increase Timeout",
    },
    diskFull: {
      title: "⚠️ Export failed",
      message: (used: number, total: number) => `Disk ${used}% full (${used}GB / ${total}GB used).`,
      action: "Free up 2GB space, or change export location.",
      ctaPrimary: "Free Space",
      ctaSecondary: "Change Location",
    },
    sessionNotFound: {
      title: "❌ Session not found",
      message: (sessionId: string) => `${sessionId} doesn't exist in corpus.`,
      causes: ["Typo in session ID", "Session was deleted", "Corpus file corrupted"],
      ctaPrimary: "Go to Timeline",
      ctaSecondary: "Create New Session",
    },
    corpusLocked: {
      title: "⚠️ Corpus locked",
      message: "Another process is writing to corpus.h5.\n\nWait for operation to complete (~30s).",
      ctaPrimary: "Retry",
      ctaSecondary: "Force Unlock (Risky)",
    },
    llmRateLimit: {
      title: "⚠️ LLM request failed",
      message: (model: string) => `Model: ${model}\nError: 429 Too Many Requests\n\nRate limit exceeded. Retry in 60 seconds.`,
      ctaPrimary: "Retry Now",
      ctaSecondary: "Wait 60s",
    },
    policyViolation: {
      title: "❌ Policy violation",
      message: (rule: string, reason: string) =>
        `Action blocked by mutation_policy.yml:\n\nRule: ${rule}\n${reason}\n\nOverride requires admin approval.`,
      ctaPrimary: "Cancel",
      ctaSecondary: "Request Override",
    },
  },

  /** Delete confirmation */
  deleteConfirmation: {
    title: "⚠️ Delete Session?",
    message: (sessionId: string, interactionCount: number) =>
      `This will permanently delete:\n• ${sessionId}\n• ${interactionCount} interactions\n• All metadata\n\nThis cannot be undone.`,
    ctaCancel: "Cancel",
    ctaConfirm: "Delete Permanently",
  },

  /** Friday Review */
  fridayReview: {
    notification: {
      title: "📅 Friday Review",
      message: (sessions: number, interactions: number, exports: number) =>
        `It's Friday 4pm. Time to reflect.\n\nThis week you:\n• Created ${sessions} sessions\n• Wrote ${interactions} interactions\n• Exported ${exports} times\n\nWant to do a quick review?`,
      ctaPrimary: "Start Review",
      ctaSecondary: "Skip This Week",
      ctaTertiary: "Remind Me at 5pm",
    },
    form: {
      title: "📅 Friday Review",
      topSessions: "Most active sessions this week:",
      questions: {
        wentWell: "What went well this week?",
        couldImprove: "What could improve?",
        nextWeekGoals: "Goals for next week?",
      },
      ctaSave: "Save Reflection",
      ctaSkip: "Skip",
    },
    saved: {
      title: "✅ Reflection saved",
      message: (interactionId: string) => `Your Friday review is saved as:\n${interactionId}\n\nTagged with: friday-review`,
      ctaPrimary: "View in Timeline",
      ctaSecondary: "Done",
    },
  },

  /** Tooltips */
  tooltips: {
    sessionId: "Session ID\n\nFormat: session_YYYYMMDD_HHMMSS\n\nUnique identifier for this session.\nUsed for export, verify, and API calls.",
    contentHash: "Content Hash\n\nSHA256 hash of interaction content.\n\nUsed to verify data integrity.\nAny tampering changes the hash.\n\nFormat: hex string (64 chars)",
    corpus: "Corpus\n\nHDF5 file storing all sessions.\n\nLocation: storage/corpus.h5\nMode: Append-only (no mutations)\n\nThink of it as your knowledge database.",
    appendOnly: "Append-Only\n\nNew data can be added.\nExisting data cannot be modified or deleted.\n\nThis ensures:\n• Data integrity\n• Audit trail\n• No accidental loss\n\nDeletion requires policy approval.",
    policyAsCode: "Policy-as-Code\n\nRules defined in YAML files.\n\nExamples:\n• mutation_policy.yml (what can be modified)\n• llm_policy.yml (which models allowed)\n• export_policy.yml (redaction rules)\n\nPolicies are versioned and auditable.",
  },

  /** Settings */
  settings: {
    identityChanged: {
      title: "✅ Identity updated",
      message: (newIdentity: string) =>
        `New identity: ${newIdentity}\n\nThis affects future sessions.\nExisting sessions unchanged.`,
      cta: "OK",
    },
    exportLocationChanged: {
      title: "✅ Export location updated",
      message: (newLocation: string) => `New location: ${newLocation}\n\nFuture exports will save here.`,
      cta: "OK",
    },
    policyUpdated: {
      title: "✅ Policy updated",
      message: (rules: string[]) =>
        `mutation_policy.yml changes applied.\n\nAffected rules:\n${rules.map((r) => `• ${r}`).join("\n")}`,
      ctaPrimary: "View Policy",
      ctaSecondary: "OK",
    },
  },

  /** Keyboard shortcuts */
  shortcuts: {
    title: "Keyboard Shortcuts",
    sections: {
      navigation: {
        title: "Navigation",
        items: {
          search: "Cmd+K    Search",
          newSession: "Cmd+N    New Session",
          export: "Cmd+E    Export",
        },
      },
      timeline: {
        title: "Timeline",
        items: {
          pin: "p        Pin/Unpin",
          tag: "t        Tag",
          copy: "c        Copy",
        },
      },
      other: {
        title: "Other",
        items: {
          shortcuts: "Cmd+/    Toggle shortcuts panel",
          closeModal: "Esc      Close modal",
        },
      },
    },
    cta: "Close",
  },

  /** Search */
  search: {
    empty: (query: string) =>
      `No results for "${query}"\n\nTry:\n• Check spelling\n• Use different keywords\n• Remove filters`,
    results: (count: number, sessions: number, interactions: number) =>
      `Found ${count} results\n\nShowing results from:\n• ${sessions} sessions\n• ${interactions} interactions`,
    filters: {
      pinnedOnly: "Pinned only",
      tagged: (tag: string) => `Tagged: ${tag}`,
      lastNDays: (days: number) => `Last ${days} days`,
    },
    ctaClearFilters: "Clear Filters",
    ctaClearSearch: "Clear Search",
  },
} as const;

/**
 * Helper to get nested microcopy with type safety
 */
export function getMicrocopy(path: string): string | ((...args: any[]) => string) {
  const parts = path.split(".");
  let current: any = MICROCOPYS;

  for (const part of parts) {
    if (current[part] === undefined) {
      console.warn(`Microcopy not found: ${path}`);
      return path; // Fallback to path itself
    }
    current = current[part];
  }

  return current;
}
