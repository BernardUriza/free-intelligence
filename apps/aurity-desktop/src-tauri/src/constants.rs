// Constants — app-level configuration values (ports, timeouts, durations).

use std::time::Duration;

/// Localhost address for all local bindings
pub(crate) const LOCALHOST: &str = "127.0.0.1";

/// Default backend port (frontend expects this)
pub(crate) const DEFAULT_BACKEND_PORT: u16 = 7001;

/// Fallback port range when default is busy
pub(crate) const FALLBACK_PORT_START: u16 = 7002;
pub(crate) const FALLBACK_PORT_END: u16 = 7050;

/// Ollama API base URL
pub(crate) const OLLAMA_API_URL: &str = "http://localhost:11434";

/// Timeout for Ollama health checks
pub(crate) const OLLAMA_CHECK_TIMEOUT: Duration = Duration::from_secs(2);

/// Timeout for backend health checks
pub(crate) const BACKEND_HEALTH_TIMEOUT: Duration = Duration::from_secs(2);

/// Maximum health check attempts (500ms each = 30s total)
pub(crate) const MAX_HEALTH_CHECK_ATTEMPTS: u32 = 60;

/// Minimum splash screen duration for branding animation
pub(crate) const MIN_SPLASH_DURATION: Duration = Duration::from_secs(15);

/// Fallback timeout to force-show main window
pub(crate) const FALLBACK_WINDOW_TIMEOUT: Duration = Duration::from_secs(20);
