// Prevents additional console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_log::Builder::default().build())
        .setup(|app| {
            let _store = app.store_builder("offline-queue.bin").build();
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_app_version,
            check_for_updates,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
async fn check_for_updates(app: tauri::AppHandle) -> Result<String, String> {
    match app.updater() {
        Ok(updater) => match updater.check().await {
            Ok(Some(update)) => Ok(format!(
                "Update available: {} -> {}",
                update.current_version,
                update.version
            )),
            Ok(None) => Ok("No updates available".to_string()),
            Err(e) => Err(format!("Update check failed: {}", e)),
        },
        Err(e) => Err(format!("Updater not available: {}", e)),
    }
}
