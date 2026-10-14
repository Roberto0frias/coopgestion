# Compila la hoja de estilos de Tailwind CSS (v4, binario independiente, sin Node).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\entorno\tailwind.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\entorno\tailwind.ps1 -Vigilar
#
# El binario se descarga una sola vez en el perfil del usuario, fuera del repositorio.

param(
    [switch]$Vigilar
)

$ErrorActionPreference = 'Stop'

$repo = Split-Path $PSScriptRoot -Parent | Split-Path -Parent
$herramientas = Join-Path $env:USERPROFILE '.coopgestion\herramientas'
$tailwind = Join-Path $herramientas 'tailwindcss.exe'
$entrada = Join-Path $repo 'assets\css\input.css'
$salida = Join-Path $repo 'static\css\app.css'

New-Item -ItemType Directory -Force -Path $herramientas | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $salida) | Out-Null

if (-not (Test-Path $tailwind)) {
    Write-Host 'Descargando Tailwind CSS CLI (~107 MB, solo la primera vez) ...' -ForegroundColor Yellow
    & curl.exe -L --fail --retry 3 -s -A "Mozilla/5.0" -o $tailwind `
        'https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe'
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar Tailwind CSS CLI.' }
}
elseif (-not (Test-Path "$tailwind.sha256")) {
    # Se guarda una marca de la version descargada para poder auditar cambios.
    & $tailwind --help 2>&1 | Select-Object -First 1 |
        Set-Content -Path "$tailwind.sha256" -Encoding utf8
}

$argumentos = @('-i', $entrada, '-o', $salida, '--minify')
if ($Vigilar) {
    $argumentos += '--watch'
    Write-Host 'Compilando en modo vigilancia (Ctrl+C para salir) ...' -ForegroundColor Cyan
}

& $tailwind @argumentos
if ($LASTEXITCODE -ne 0) { throw "Tailwind terminó con código $LASTEXITCODE." }

if (-not $Vigilar) {
    $kb = [math]::Round((Get-Item $salida).Length / 1KB, 1)
    Write-Host "Hoja de estilos generada: $salida ($kb KB)" -ForegroundColor Green
}
