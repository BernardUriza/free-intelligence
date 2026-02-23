fn main() {
    // Inject FI Monitor version and productName from its tauri.conf.json at compile time.
    // This keeps the download URL in fi_monitor.rs always in sync with what Tauri builds.
    let fi_monitor_conf =
        std::path::Path::new("../../fi-monitor/src-tauri/tauri.conf.json");

    if fi_monitor_conf.exists() {
        let content = std::fs::read_to_string(fi_monitor_conf)
            .expect("Failed to read fi-monitor tauri.conf.json");
        let json: serde_json::Value =
            serde_json::from_str(&content).expect("Failed to parse fi-monitor tauri.conf.json");

        let version = json["version"]
            .as_str()
            .expect("fi-monitor tauri.conf.json missing 'version' field");
        let product_name = json["productName"]
            .as_str()
            .expect("fi-monitor tauri.conf.json missing 'productName' field");

        println!("cargo:rustc-env=FI_MONITOR_VERSION={}", version);
        println!("cargo:rustc-env=FI_MONITOR_PRODUCT_NAME={}", product_name);
        println!(
            "cargo:rerun-if-changed={}",
            fi_monitor_conf.display()
        );
    } else {
        // Fallback for CI or environments where fi-monitor source isn't available.
        // Keep this in sync with apps/fi-monitor/src-tauri/tauri.conf.json version field.
        println!("cargo:rustc-env=FI_MONITOR_VERSION=1.0.14");
        println!("cargo:rustc-env=FI_MONITOR_PRODUCT_NAME=FIMonitor");
        println!("cargo:warning=fi-monitor tauri.conf.json not found, using fallback version 1.0.14");
    }

    tauri_build::build()
}
