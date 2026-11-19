$ErrorActionPreference = "Stop"

$postgresBin = "C:\Program Files\PostgreSQL\18\bin"
$activateScript = Join-Path $PSScriptRoot "..\.venv\Scripts\Activate.ps1"

if (-not (Test-Path (Join-Path $postgresBin "libpq.dll"))) {
    throw "PostgreSQL libpq.dll was not found."
}

if (-not (Test-Path $activateScript)) {
    throw "Virtual environment activation script was not found."
}

$env:PSYCOPG_IMPL = "python"
$env:PATH = "$postgresBin;$env:PATH"

. $activateScript