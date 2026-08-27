pub fn run() {
    let context = tauri::generate_context!("./tauri.conf.json");
    tauri::Builder::default()
        .run(context)
        .expect("error while running AeroGuard desktop application");
}
