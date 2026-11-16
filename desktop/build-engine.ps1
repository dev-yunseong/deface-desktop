$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $bin = Join-Path $PSScriptRoot 'src-tauri/bin'
    New-Item -ItemType Directory -Force $bin | Out-Null
    python -m PyInstaller --noconfirm --distpath $bin --workpath desktop/.engine/build desktop/engine.spec
    if ($LASTEXITCODE -ne 0) { throw 'Deface engine build failed.' }
} finally {
    Pop-Location
}
