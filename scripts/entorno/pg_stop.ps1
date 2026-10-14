# Detiene el PostgreSQL 16 portable de COOPGESTION.
#
# Uso: powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_stop.ps1

. (Join-Path $PSScriptRoot 'comun.ps1')

if (-not (Test-Path (Join-Path $CoopPgBin 'pg_ctl.exe'))) {
    Write-Host 'El clúster no está instalado; nada que detener.'
    exit 0
}

$codigo = Stop-CoopPostgres
exit $codigo
