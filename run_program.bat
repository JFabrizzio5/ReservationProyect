@echo off
echo Este archivo se está ejecutando desde: %~dp0  REM Imprime la carpeta actual
cd /d "%~dp0"  REM Cambia al directorio donde está el archivo .bat

echo Navegando a: %cd%  REM Imprime la carpeta actual después de cambiar
REM Comprueba si el directorio del entorno virtual existe
if exist "venv\" (
    echo Encontrado el entorno virtual en 'venv'.
    echo Activando el entorno virtual...
    call "venv\Scripts\activate.bat"
) else (
    echo No se pudo encontrar el entorno virtual en 'venv'.
    pause
    exit /b
)

echo Navegando a: %cd%  REM Imprime la carpeta actual después de activar el venv

REM Comprueba si el script existe
if exist "app.py" (
    echo Ejecutando 'app.py'...
    python app.py
) else (
    echo No se pudo encontrar 'app.py'.
    pause
    exit /b
)

pause  REM Mantiene la ventana abierta
