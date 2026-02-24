// Path Utilities — Windows ↔ WSL path conversion and backend source discovery.

/// Find the backend source directory on the Windows filesystem.
/// Tries paths relative to the executable first, then common dev locations.
#[cfg(target_os = "windows")]
pub(crate) fn get_windows_backend_path() -> Option<String> {
    let exe = std::env::current_exe().ok()?;
    let mut path = exe.parent()?;

    // Walk up to 5 levels looking for a `backend/` sibling directory
    for _ in 0..5 {
        let backend = path.join("backend");
        if backend.exists() {
            return Some(backend.to_string_lossy().to_string());
        }
        path = path.parent()?;
    }

    // Fallback: common development paths
    let home = dirs::home_dir()?;
    let candidates = [
        home.join("free-intelligence/backend"),
        home.join("projects/free-intelligence/backend"),
    ];

    candidates
        .iter()
        .find(|c| c.exists())
        .map(|c| c.to_string_lossy().to_string())
}

/// Convert a Windows path (`C:\Users\...`) to a WSL mount path (`/mnt/c/Users/...`).
#[cfg(target_os = "windows")]
pub(crate) fn windows_to_wsl_path(win_path: &str) -> String {
    let path = win_path.replace('\\', "/");
    match path.as_bytes() {
        [drive_letter, b':', b'/', rest @ ..] if drive_letter.is_ascii_alphabetic() => {
            let drive = (*drive_letter as char).to_ascii_lowercase();
            format!(
                "/mnt/{}/{}",
                drive,
                std::str::from_utf8(rest).unwrap_or("")
            )
        }
        [drive_letter, b':', rest @ ..] if drive_letter.is_ascii_alphabetic() => {
            let drive = (*drive_letter as char).to_ascii_lowercase();
            let remainder = std::str::from_utf8(rest).unwrap_or("");
            format!("/mnt/{}/{}", drive, remainder.trim_start_matches('/'))
        }
        _ => path,
    }
}

#[cfg(test)]
mod tests {
    #[allow(unused_imports)]
    use super::*;

    #[test]
    #[cfg(target_os = "windows")]
    fn test_windows_to_wsl_path_basic() {
        assert_eq!(
            windows_to_wsl_path(r"C:\Users\bob\code"),
            "/mnt/c/Users/bob/code"
        );
    }

    #[test]
    #[cfg(target_os = "windows")]
    fn test_windows_to_wsl_path_no_trailing_slash() {
        assert_eq!(
            windows_to_wsl_path("D:\\projects"),
            "/mnt/d/projects"
        );
    }

    #[test]
    #[cfg(target_os = "windows")]
    fn test_windows_to_wsl_path_forward_slashes() {
        assert_eq!(
            windows_to_wsl_path("C:/Users/test"),
            "/mnt/c/Users/test"
        );
    }
}
