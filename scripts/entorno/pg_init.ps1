# Inicializa el clúster PostgreSQL 16 portable de COOPGESTION.
#
# Crea el clúster con el superusuario 'postgres' (solo administración) y el rol de
# aplicación 'coopgestion' (NOSUPERUSER, NOCREATEROLE, CREATEDB), dueño de la base de
# datos del proyecto. No requiere permisos de administrador.
#
# Uso: powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_init.ps1

. (Join-Path $PSScriptRoot 'comun.ps1')

Write-Host '=== COOPGESTION · inicialización del PostgreSQL 16 portable ===' -ForegroundColor Cyan

# 1. Binarios
if (Test-Path (Join-Path $CoopPgBin 'initdb.exe')) {
    Write-Host "[1/6] Binarios ya presentes en $CoopPgRoot"
} else {
    if (-not (Test-Path $CoopZip)) {
        throw "No se encontraron los binarios en $CoopZip. Descargue primero el archivo oficial."
    }
    Write-Host "[1/6] Extrayendo binarios en $CoopBase (puede tardar un par de minutos) ..."
    New-Item -ItemType Directory -Force -Path $CoopBase | Out-Null
    & tar.exe -xf $CoopZip -C $CoopBase
    if ($LASTEXITCODE -ne 0) { throw 'Falló la extracción de los binarios.' }
    if (-not (Test-Path (Join-Path $CoopPgBin 'initdb.exe'))) {
        throw "La extracción no produjo $CoopPgBin\initdb.exe"
    }
}
& (Join-Path $CoopPgBin 'postgres.exe') --version

# 2. Directorio de datos
if (Test-Path (Join-Path $CoopPgData 'PG_VERSION')) {
    Write-Host "[2/6] El clúster ya está inicializado en $CoopPgData"
} else {
    Write-Host "[2/6] Ejecutando initdb en $CoopPgData (superusuario: $CoopPgAdminUser) ..."
    New-Item -ItemType Directory -Force -Path $CoopPgData | Out-Null
    $pwFile = Join-Path $env:TEMP 'coopgestion_admin_pw.txt'
    Set-Content -Path $pwFile -Value $CoopPgAdminPassword -NoNewline -Encoding ascii
    try {
        & (Join-Path $CoopPgBin 'initdb.exe') `
            -D $CoopPgData `
            -U $CoopPgAdminUser `
            "--pwfile=$pwFile" `
            --encoding=UTF8 `
            --locale=C `
            --auth-host=scram-sha-256 `
            --auth-local=scram-sha-256
        if ($LASTEXITCODE -ne 0) { throw 'initdb falló.' }
    } finally {
        Remove-Item $pwFile -Force -ErrorAction SilentlyContinue
    }
}

# 3. Parámetros del servidor
Write-Host '[3/6] Configurando puerto, escucha local, zona horaria y registro ...'
$conf = Join-Path $CoopPgData 'postgresql.conf'
$ajustes = @(
    '# --- COOPGESTION ---',
    "port = $CoopPgPort",
    "listen_addresses = '$CoopPgHost'",
    "timezone = 'America/Santo_Domingo'",
    "log_timezone = 'America/Santo_Domingo'",
    # El servidor se lanza desacoplado (sin consola): recolecta su propio registro.
    'logging_collector = on',
    "log_directory = 'log'",
    "log_filename = 'postgresql-%Y-%m-%d.log'",
    'log_rotation_age = 1d',
    'log_rotation_size = 0',
    "log_line_prefix = '%m [%p] %u@%d '",
    'log_min_duration_statement = 1000',
    'shared_buffers = 256MB',
    'work_mem = 16MB',
    'maintenance_work_mem = 128MB',
    'random_page_cost = 1.1',
    'effective_cache_size = 1GB'
)
if ((Get-Content $conf -Raw) -notmatch '# --- COOPGESTION ---') {
    Add-Content -Path $conf -Value "`n$($ajustes -join "`n")"
} else {
    # Un clúster creado por una versión anterior del script puede tener el recolector de
    # registro desactivado. Se agrega un bloque correctivo que se aplica al final del archivo.
    if ((Get-Content $conf -Raw) -notmatch '# --- COOPGESTION REGISTRO ---') {
        Write-Host '      Aplicando bloque correctivo de registro ...'
        $correccion = @(
            '# --- COOPGESTION REGISTRO ---',
            'logging_collector = on',
            "log_directory = 'log'",
            "log_filename = 'postgresql-%Y-%m-%d.log'",
            "log_line_prefix = '%m [%p] %u@%d '"
        )
        Add-Content -Path $conf -Value "`n$($correccion -join "`n")"
    }
}

# 4. Arranque desacoplado
Write-Host '[4/6] Arrancando el servidor ...'
Start-CoopPostgres | Out-Null

# 5. Rol de la aplicación (menor privilegio)
Write-Host "[5/6] Asegurando el rol de aplicación '$CoopPgUser' ..."
$sqlRol = @"
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$CoopPgUser') THEN
        CREATE ROLE $CoopPgUser LOGIN PASSWORD '$CoopPgPassword'
            NOSUPERUSER NOCREATEROLE CREATEDB;
    END IF;
END
`$`$;
"@
Invoke-CoopPsql -Sql $sqlRol -Database postgres -Admin | Out-Null

$privilegios = Invoke-CoopPsql -Database postgres -Admin -SinEncabezado `
    -Sql "SELECT rolsuper || '|' || rolcreatedb || '|' || rolcreaterole FROM pg_roles WHERE rolname = '$CoopPgUser';"
Write-Host "      Privilegios (super|createdb|createrole): $("$privilegios".Trim())"

# 6. Base de datos del proyecto
$existe = Invoke-CoopPsql -Database postgres -Admin -SinEncabezado `
    -Sql "SELECT 1 FROM pg_database WHERE datname = '$CoopPgDatabase';"
if ("$existe".Trim() -ne '1') {
    Write-Host "[6/6] Creando base de datos '$CoopPgDatabase' propiedad de '$CoopPgUser' ..."
    $env:PGPASSWORD = $CoopPgAdminPassword
    & (Join-Path $CoopPgBin 'createdb.exe') -h $CoopPgHost -p $CoopPgPort -U $CoopPgAdminUser `
        -O $CoopPgUser -E UTF8 -T template0 $CoopPgDatabase
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la base de datos.' }
} else {
    Write-Host "[6/6] La base de datos '$CoopPgDatabase' ya existe"
}

Invoke-CoopPsql -Sql 'SELECT version();'

Write-Host ''
Write-Host 'Entorno listo.' -ForegroundColor Green
Write-Host "  Host: $CoopPgHost  Puerto: $CoopPgPort  Base: $CoopPgDatabase"
Write-Host "  Administrador: $CoopPgAdminUser   Aplicación: $CoopPgUser (NOSUPERUSER)"
