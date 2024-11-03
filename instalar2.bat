@echo off
echo Instalando o actualizando pip...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

echo Creando entorno virtual...
python -m venv venv

echo Activando el entorno virtual...
call venv\Scripts\activate

echo Instalando dependencias desde requirements.txt...
pip install -r requirements.txt

echo Listando los paquetes instalados...
pip list

echo Todo listo. El entorno virtual ha sido configurado.
pause
