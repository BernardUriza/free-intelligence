// Persistence — load/save benchmark history to disk.

use std::path::PathBuf;

use super::{BenchmarkHistory, BenchmarkSuite};

/// Maximum number of benchmark results to keep.
const MAX_HISTORY: usize = 50;

/// Path to the benchmarks JSON file (~/.config/fi-monitor/benchmarks.json).
fn get_benchmarks_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("fi-monitor")
        .join("benchmarks.json")
}

/// Load benchmark history from disk. Returns empty history on any error.
pub(super) fn load_benchmark_history() -> BenchmarkHistory {
    let path = get_benchmarks_path();
    if !path.exists() {
        return BenchmarkHistory { results: vec![] };
    }
    let content = std::fs::read_to_string(&path).unwrap_or_else(|_| "{}".to_string());
    serde_json::from_str(&content).unwrap_or(BenchmarkHistory { results: vec![] })
}

/// Append a benchmark result to the history file (most recent first, capped).
pub(super) fn save_benchmark_result(result: BenchmarkSuite) -> Result<(), String> {
    let mut history = load_benchmark_history();
    history.results.insert(0, result);
    history.results.truncate(MAX_HISTORY);

    let path = get_benchmarks_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&history).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    println!("[FI Monitor] Benchmark saved to {:?}", path);
    Ok(())
}
