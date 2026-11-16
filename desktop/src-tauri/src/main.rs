#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader, Read, Seek},
    os::windows::process::CommandExt,
    path::PathBuf,
    process::{Command, Stdio},
    sync::{Mutex, TryLockError},
};
use tauri::{ipc::Channel, Manager};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_updater::UpdaterExt;

#[derive(Default)]
struct Operation(Mutex<()>);

fn lock_operation(app: &tauri::AppHandle) -> Result<tauri::State<'_, Operation>, String> {
    app.try_state::<Operation>()
        .ok_or_else(|| "App state unavailable.".into())
}

fn operation_error(error: TryLockError<std::sync::MutexGuard<'_, ()>>) -> String {
    match error {
        TryLockError::WouldBlock => "Another operation is running.".into(),
        TryLockError::Poisoned(_) => "Restart the app and try again.".into(),
    }
}

#[tauri::command]
async fn choose_video(app: tauri::AppHandle, extensions: Vec<String>) -> Option<PathBuf> {
    let extensions: Vec<&str> = extensions.iter().map(String::as_str).collect();
    app.dialog()
        .file()
        .add_filter("Video", &extensions)
        .blocking_pick_file()?
        .into_path()
        .ok()
}

#[tauri::command]
async fn choose_output(app: tauri::AppHandle, input: PathBuf) -> Option<PathBuf> {
    let stem = input.file_stem()?.to_string_lossy();
    app.dialog()
        .file()
        .add_filter("MP4", &["mp4"])
        .set_directory(input.parent()?)
        .set_file_name(format!("{stem}_anonymized.mp4"))
        .blocking_save_file()?
        .into_path()
        .ok()
}

#[tauri::command]
async fn anonymize(
    app: tauri::AppHandle,
    input: PathBuf,
    output: PathBuf,
    mask: String,
    keep_audio: bool,
    progress: Channel<u64>,
) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || -> Result<(), String> {
        let operation = lock_operation(&app)?;
        let _guard = operation.0.try_lock().map_err(operation_error)?;
        if !input.is_absolute() || !input.is_file() || !output.is_absolute() {
            return Err("Choose an existing source video and an absolute output path.".into());
        }
        if output
            .extension()
            .and_then(|ext| ext.to_str())
            .map(str::to_ascii_lowercase)
            .as_deref()
            != Some("mp4")
        {
            return Err("Save the output as an MP4 file.".into());
        }
        if output.exists() {
            return Err("The output file already exists. Choose a new file name.".into());
        }
        if !matches!(mask.as_str(), "blur" | "mosaic" | "solid") {
            return Err("Choose a valid face mask.".into());
        }
        let parent = output.parent().ok_or("Invalid output folder.")?;
        let temp = tempfile::Builder::new()
            .prefix(".deface-")
            .suffix(".mp4")
            .tempfile_in(parent)
            .map_err(|error| format!("Could not create the output file: {error}"))?
            .into_temp_path();
        let mut errors = tempfile::tempfile().map_err(|error| error.to_string())?;
        let executable = std::env::current_exe()
            .map_err(|error| error.to_string())?
            .with_file_name("deface-engine.exe");
        let ffmpeg = executable.with_file_name("deface-ffmpeg.exe");
        let mut engine = Command::new(executable);
        engine
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .arg(&input)
            .arg(temp.as_os_str())
            .arg(mask)
            .arg("--ffmpeg")
            .arg(ffmpeg)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(errors.try_clone().map_err(|error| error.to_string())?);
        if keep_audio {
            engine.arg("--keep-audio");
        }
        let mut child = engine
            .spawn()
            .map_err(|error| format!("Could not start Deface: {error}"))?;
        let stdout = child.stdout.take().expect("stdout is piped");
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Ok(frames) = line.parse() {
                let _ = progress.send(frames);
            }
        }
        let status = child.wait().map_err(|error| error.to_string())?;
        if !status.success() {
            let length = errors.metadata().map_err(|error| error.to_string())?.len();
            errors
                .seek(std::io::SeekFrom::Start(length.saturating_sub(4096)))
                .map_err(|error| error.to_string())?;
            let mut details = Vec::new();
            errors
                .read_to_end(&mut details)
                .map_err(|error| error.to_string())?;
            return Err(format!(
                "Deface could not process the video ({status}). {}",
                String::from_utf8_lossy(&details).trim()
            ));
        }
        temp.persist_noclobber(&output)
            .map_err(|error| format!("Could not save the result: {error}"))?;
        app.asset_protocol_scope()
            .allow_file(&output)
            .map_err(|error| error.to_string())?;
        Ok(())
    })
    .await
    .map_err(|error| error.to_string())?
}

#[tauri::command]
async fn check_update(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let update = app
        .updater()
        .map_err(|error| error.to_string())?
        .check()
        .await
        .map_err(|error| error.to_string())?;
    Ok(update.map(|release| release.version))
}

#[tauri::command]
async fn install_update(app: tauri::AppHandle, version: String) -> Result<(), String> {
    let update = app
        .updater()
        .map_err(|error| error.to_string())?
        .check()
        .await
        .map_err(|error| error.to_string())?
        .filter(|release| release.version == version)
        .ok_or("The available version changed. Check for updates again.")?;
    tauri::async_runtime::spawn_blocking(move || -> Result<(), String> {
        let operation = lock_operation(&app)?;
        let _guard = operation.0.try_lock().map_err(operation_error)?;
        tauri::async_runtime::block_on(update.download_and_install(|_, _| {}, || {}))
            .map_err(|error| error.to_string())
    })
    .await
    .map_err(|error| error.to_string())?
}

fn main() {
    tauri::Builder::default()
        .manage(Operation::default())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            choose_video,
            choose_output,
            anonymize,
            check_update,
            install_update
        ])
        .run(tauri::generate_context!())
        .expect("could not start Deface Desktop");
}
