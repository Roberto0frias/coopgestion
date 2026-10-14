# Estado del entorno de desarrollo de COOPGESTION.
#
# Uso: powershell -ExecutionPolicy Bypass -File scripts\entorno\estado.ps1

. (Join-Path $PSScriptRoot 'comun.ps1')

Write-Host '=== COOPGESTION · estado del entorno de desarrollo ===' -ForegroundColor Cyan

# PostgreSQL
if (Test-Path (Join-Path $CoopPgBin 'pg_ctl.exe')) {
    $listo = Test-CoopPostgresListo
    if ($listo) {
        $version = Invoke-CoopPsql -Sql 'SHOW server_version;' -SinEncabezado
        $basedatos = Invoke-CoopPsql -Sql 'SELECT current_database();' -SinEncabezado
        Write-Host "PostgreSQL : EN EJECUCIÓN  versión $("$version".Trim())  base $("$basedatos".Trim())" -ForegroundColor Green
        Write-Host "             $CoopPgHost`:$CoopPgPort  usuario $CoopPgUser"
    } else {
        Write-Host "PostgreSQL : DETENIDO (arranque con scripts\entorno\pg_start.ps1)" -ForegroundColor Yellow
    }
} else {
    Write-Host 'PostgreSQL : NO INSTALADO (ejecute scripts\entorno\pg_init.ps1)' -ForegroundColor Red
}

# Python y dependencias
$venv = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) '.venv'
if (Test-Path $venv) {
    $python = Join-Path $venv 'Scripts\python.exe'
    $versionPy = & $python --version 2>&1
    Write-Host "Python     : $versionPy  ($venv)" -ForegroundColor Green
} else {
    Write-Host 'Python     : SIN ENTORNO VIRTUAL (ejecute uv sync --dev)' -ForegroundColor Yellow
}

# Repositorio
$repo = Split-Path $PSScriptRoot -Parent | Split-Path -Parent
if (Test-Path (Join-Path $repo '.git')) {
    Write-Host "Repositorio: $repo"
} else {
    Write-Host 'Repositorio: sin inicializar'
}
