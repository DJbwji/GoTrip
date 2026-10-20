$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Create the virtual environment and install requirements first. See README.md.'
}
& $pythonExe manage.py migrate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonExe manage.py runserver 127.0.0.1:8000
