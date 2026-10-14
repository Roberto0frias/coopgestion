# Variables y funciones comunes para la gestión del PostgreSQL 16 portable de COOPGESTION.
# Este clúster vive en el perfil del usuario y NO requiere permisos de administrador.
#
# Hay DOS roles, por principio de menor privilegio:
#   - postgres     : superusuario, solo para administración (crear roles y bases de datos).
#   - coopgestion  : rol de la aplicación. NOSUPERUSER, NOCREATEROLE, CREATEDB
#                    (CREATEDB solo para poder crear la base de datos de pruebas).
#
# NOTA IMPORTANTE DE CODIFICACIÓN: este archivo debe guardarse en UTF-8 **con BOM**.
# Windows PowerShell 5.1 lee los .ps1 sin BOM como ANSI; una «Ó» se convertiría en una
# comilla tipográfica y rompería el analizador sintáctico.
#
# NOTA TÉCNICA DEL ARRANQUE: el servidor se lanza con WMI (Win32_Process.Create), que crea
# un proceso totalmente desacoplado. Si se lanzara con Start-Process, postgres.exe heredaría
# la tubería de salida del shell y cualquier trabajo en segundo plano quedaría abierto
# indefinidamente (y cancelarlo mataría al servidor).

$ErrorActionPreference = 'Stop'

$script:CoopBase       = Join-Path $env:USERPROFILE '.coopgestion'
$script:CoopDescargas  = Join-Path $CoopBase 'descargas'
$script:CoopPgRoot     = Join-Path $CoopBase 'pgsql'
$script:CoopPgBin      = Join-Path $CoopPgRoot 'bin'
$script:CoopPgData     = Join-Path $CoopBase 'pgdata'
$script:CoopPgLogDir   = Join-Path $CoopPgData 'log'
$script:CoopPgLog      = Join-Path $CoopBase 'postgresql.log'
$script:CoopPgCtlOut   = Join-Path $CoopBase 'pg_ctl.out.log'
$script:CoopPgCtlErr   = Join-Path $CoopBase 'pg_ctl.err.log'
$script:CoopZip        = Join-Path $CoopDescargas 'postgresql-16.15-1-windows-x64-binaries.zip'

$script:CoopPgHost          = '127.0.0.1'
$script:CoopPgPort          = 5433
$script:CoopPgAdminUser     = 'postgres'
$script:CoopPgAdminPassword = 'coopgestion_admin'
$script:CoopPgUser          = 'coopgestion'
$script:CoopPgPassword      = 'coopgestion_dev'
$script:CoopPgDatabase      = 'coopgestion'

function Test-CoopPostgresListo {
    <# Devuelve $true si el servidor acepta conexiones. #>
    & (Join-Path $CoopPgBin 'pg_isready.exe') -h $CoopPgHost -p $CoopPgPort -q
    return ($LASTEXITCODE -eq 0)
}

function Get-CoopPostgresLogTail {
    <# Devuelve las últimas líneas del registro más reciente del servidor. #>
    param([int]$Lineas = 25)
    $archivo = Get-ChildItem $CoopPgLogDir -Filter '*.log' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($archivo) { return (Get-Content $archivo.FullName -Tail $Lineas -ErrorAction SilentlyContinue) }
    if (Test-Path $CoopPgLog) { return (Get-Content $CoopPgLog -Tail $Lineas -ErrorAction SilentlyContinue) }
    return @('(sin registro disponible)')
}

function Start-CoopPostgres {
    <#
        Arranca el servidor de forma totalmente desacoplada mediante WMI y espera a que
        acepte conexiones. No hereda ninguna tubería del shell que lo invoca.
    #>
    if (Test-CoopPostgresListo) {
        Write-Host "PostgreSQL ya está en ejecución en $CoopPgHost`:$CoopPgPort" -ForegroundColor Green
        return 0
    }
    $comando = '"{0}" -D "{1}"' -f (Join-Path $CoopPgBin 'postgres.exe'), $CoopPgData
    $resultado = Invoke-CimMethod -ClassName Win32_Process -MethodName Create `
        -Arguments @{ CommandLine = $comando }
    if ($resultado.ReturnValue -ne 0) {
        throw "No se pudo crear el proceso del servidor (WMI devolvió $($resultado.ReturnValue))."
    }

    for ($intento = 0; $intento -lt 60; $intento++) {
        Start-Sleep -Milliseconds 500
        if (Test-CoopPostgresListo) {
            Write-Host "PostgreSQL arrancado en $CoopPgHost`:$CoopPgPort (proceso $($resultado.ProcessId))" -ForegroundColor Green
            return 0
        }
    }
    Write-Host 'Últimas líneas del registro:' -ForegroundColor Red
    Get-CoopPostgresLogTail -Lineas 25 | Write-Host
    throw 'El servidor PostgreSQL no respondió en 30 segundos.'
}

function Stop-CoopPostgres {
    <# Detiene el servidor con parada rápida y espera a que deje de aceptar conexiones. #>
    if (-not (Test-CoopPostgresListo)) {
        Write-Host 'PostgreSQL no está en ejecución.' -ForegroundColor Yellow
        return 0
    }
    $proc = Start-Process -FilePath (Join-Path $CoopPgBin 'pg_ctl.exe') `
        -ArgumentList @('-D', $CoopPgData, '-m', 'fast', '-w', 'stop') `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $CoopPgCtlOut -RedirectStandardError $CoopPgCtlErr
    for ($intento = 0; $intento -lt 60; $intento++) {
        Start-Sleep -Milliseconds 500
        if (-not (Test-CoopPostgresListo)) {
            Write-Host 'PostgreSQL detenido.' -ForegroundColor Green
            return 0
        }
    }
    Write-Host 'Salida de pg_ctl stop:' -ForegroundColor Red
    Get-Content $CoopPgCtlOut, $CoopPgCtlErr -ErrorAction SilentlyContinue
    throw 'El servidor no se detuvo en 30 segundos.'
}

function Invoke-CoopPsql {
    <#
        Ejecuta SQL contra el clúster.
        Uso: Invoke-CoopPsql -Sql 'SELECT 1' [-Database coopgestion] [-Admin] [-SinEncabezado]
        Con -Admin usa el superusuario 'postgres'; sin él, el rol de la aplicación.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Sql,
        [string]$Database = $CoopPgDatabase,
        [switch]$Admin,
        [switch]$SinEncabezado
    )
    if ($Admin) {
        $env:PGPASSWORD = $CoopPgAdminPassword
        $usuario = $CoopPgAdminUser
    } else {
        $env:PGPASSWORD = $CoopPgPassword
        $usuario = $CoopPgUser
    }
    $argumentos = @('-h', $CoopPgHost, '-p', $CoopPgPort, '-U', $usuario, '-d', $Database)
    if ($SinEncabezado) { $argumentos += '-tA' }
    $argumentos += @('-c', $Sql)
    return (& (Join-Path $CoopPgBin 'psql.exe') @argumentos 2>&1)
}
