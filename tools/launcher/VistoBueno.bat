@echo off
setlocal

rem Inicia VistoBueno desde WSL. Requisitos:
rem - WSL2 con la distro por defecto y Nix instalado.
rem - El repositorio en ~/vistobueno.
rem Si el repositorio queda en otra ruta, cambia el cd de la linea de abajo.

wsl.exe -- bash -lc "cd ~/vistobueno && nix develop --command python3 scripts/lanzar_app.py --abrir-windows"

if errorlevel 1 (
  echo.
  echo VistoBueno no pudo iniciarse. Revisa el mensaje de arriba.
  pause
)
