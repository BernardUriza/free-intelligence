// Path & URL Helpers — executable names, installer filenames, download URLs,
// and install-path discovery.

use std::path::PathBuf;

use super::{
    FI_MONITOR_PRODUCT_NAME, FI_MONITOR_VERSION, GITHUB_REPO_NAME, GITHUB_REPO_OWNER,
};

/// Executable filename derived from productName (Tauri NSIS renames binary to this).
pub(crate) fn exe_name() -> String {
    format!("{}.exe", FI_MONITOR_PRODUCT_NAME)
}

/// NSIS installer filename: `{productName}_{version}_x64-setup.exe`.
pub(crate) fn installer_filename() -> String {
    format!(
        "{}_{}_x64-setup.exe",
        FI_MONITOR_PRODUCT_NAME, FI_MONITOR_VERSION
    )
}

/// GitHub Releases download URL for the current FI Monitor version.
pub(crate) fn release_download_url() -> String {
    format!(
        "https://github.com/{}/{}/releases/download/v{}/{}",
        GITHUB_REPO_OWNER, GITHUB_REPO_NAME, FI_MONITOR_VERSION, installer_filename()
    )
}

/// GitHub Releases page URL (for manual download fallback links).
pub(crate) fn releases_page_url() -> String {
    format!(
        "https://github.com/{}/{}/releases",
        GITHUB_REPO_OWNER, GITHUB_REPO_NAME
    )
}

/// All candidate install paths (primary NSIS path first, then fallbacks).
///
/// Search order:
///   1. `%LOCALAPPDATA%\{productName}\{productName}.exe` (NSIS currentUser)
///   2. `%ProgramFiles%\{productName}\{productName}.exe`
///   3. `%ProgramFiles(x86)%\{productName}\{productName}.exe`
pub(crate) fn candidate_install_paths() -> Vec<PathBuf> {
    let mut paths = Vec::new();

    // Primary: NSIS currentUser → %LOCALAPPDATA%
    if let Some(local) = dirs::data_local_dir() {
        paths.push(local.join(FI_MONITOR_PRODUCT_NAME).join(exe_name()));
    }

    // Fallback: Program Files
    if let Ok(pf) = std::env::var("ProgramFiles") {
        paths.push(
            PathBuf::from(&pf)
                .join(FI_MONITOR_PRODUCT_NAME)
                .join(exe_name()),
        );
    }

    // Fallback: Program Files (x86)
    if let Ok(pf86) = std::env::var("ProgramFiles(x86)") {
        paths.push(
            PathBuf::from(&pf86)
                .join(FI_MONITOR_PRODUCT_NAME)
                .join(exe_name()),
        );
    }

    paths
}

/// Find the first existing install path, or `None`.
pub(crate) fn find_installed_path() -> Option<PathBuf> {
    candidate_install_paths().into_iter().find(|p| p.exists())
}
