@echo off
REM Verifica si Python está instalado
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python no está instalado. Por favor, instala Python primero.
    exit /b 1
)

REM Actualiza pip a la última versión
echo Actualizando pip...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

REM Crea un entorno virtual si no existe
IF NOT EXIST "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activa el entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate

REM Verifica si existe el archivo requirements.txt
IF NOT EXIST "requirements.txt" (
    echo No se encontró requirements.txt.
    exit /b 1
)

REM Instala las dependencias
echo Instalando dependencias desde requirements.txt...
pip install -r requirements.txt

echo Listo!
