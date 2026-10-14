# Arranca el PostgreSQL 16 portable de COOPGESTION (lo inicializa si hace falta).
#
# Uso: powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_start.ps1

. (Join-Path $PSScriptRoot 'comun.ps1')

if (-not (Test-Path (Join-Path $CoopPgBin 'pg_ctl.exe'))) {
    Write-Host 'El clúster no está inicializado. Ejecutando pg_init.ps1 ...' -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'pg_init.ps1')
    exit $LASTEXITCODE
}

Start-CoopPostgres | Out-Null
& (Join-Path $CoopPgBin 'pg_isready.exe') -h $CoopPgHost -p $CoopPgPort -d $CoopPgDatabase -U $CoopPgUser
exit $LASTEXITCODE
