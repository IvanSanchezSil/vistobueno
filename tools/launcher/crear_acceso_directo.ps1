$ErrorActionPreference = 'Stop'

$origen = $PSScriptRoot
$escritorio = [Environment]::GetFolderPath('Desktop')
$destino = Join-Path $escritorio 'VistoBueno.lnk'

$shell = New-Object -ComObject WScript.Shell
$acceso = $shell.CreateShortcut($destino)
$acceso.TargetPath = Join-Path $origen 'VistoBueno.bat'
$acceso.WorkingDirectory = $origen
$acceso.IconLocation = Join-Path $origen 'vistobueno.ico'
$acceso.Description = 'Abrir VistoBueno'
$acceso.Save()

Write-Host "Acceso directo creado en $destino"
