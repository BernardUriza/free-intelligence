//! Embedded configuration templates for first-run bootstrap.
//!
//! These templates are compiled into the binary and extracted to the user's
//! data directory on first launch. This enables zero-config startup.

/// Main policy configuration (offline-first for desktop)
pub const POLICY: &str = include_str!("../templates/fi.policy.yaml");

// ===== Persona Templates =====

/// General Assistant - Primary medical AI persona
pub const PERSONA_GENERAL_ASSISTANT: &str =
    include_str!("../templates/personas/general_assistant.yaml");

/// Clinical Advisor - Evidence-based medical guidance
pub const PERSONA_CLINICAL_ADVISOR: &str =
    include_str!("../templates/personas/clinical_advisor.yaml");

/// SOAP Editor - Medical note generation
pub const PERSONA_SOAP_EDITOR: &str = include_str!("../templates/personas/soap_editor.yaml");

/// Honest Limiter - Transparency and limitations focus
pub const PERSONA_HONEST_LIMITER: &str =
    include_str!("../templates/personas/honest_limiter.yaml");

/// Onboarding Guide - First-run walkthrough
pub const PERSONA_ONBOARDING_GUIDE: &str =
    include_str!("../templates/personas/onboarding_guide.yaml");

/// Growth Mirror - Meta-cognitive reflection
pub const PERSONA_GROWTH_MIRROR: &str =
    include_str!("../templates/personas/growth_mirror.yaml");

/// Pattern Weaver - Conversation history analysis
pub const PERSONA_PATTERN_WEAVER: &str =
    include_str!("../templates/personas/pattern_weaver.yaml");

/// Sovereignty Guide - Data sovereignty education
pub const PERSONA_SOVEREIGNTY_GUIDE: &str =
    include_str!("../templates/personas/sovereignty_guide.yaml");

/// List of all persona templates with their filenames
pub const PERSONAS: &[(&str, &str)] = &[
    ("general_assistant.yaml", PERSONA_GENERAL_ASSISTANT),
    ("clinical_advisor.yaml", PERSONA_CLINICAL_ADVISOR),
    ("soap_editor.yaml", PERSONA_SOAP_EDITOR),
    ("honest_limiter.yaml", PERSONA_HONEST_LIMITER),
    ("onboarding_guide.yaml", PERSONA_ONBOARDING_GUIDE),
    ("growth_mirror.yaml", PERSONA_GROWTH_MIRROR),
    ("pattern_weaver.yaml", PERSONA_PATTERN_WEAVER),
    ("sovereignty_guide.yaml", PERSONA_SOVEREIGNTY_GUIDE),
];
