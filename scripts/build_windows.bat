@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

cd /d "%PROJECT_ROOT%"

set "VENV_DIR=%PROJECT_ROOT%\temple_venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "ICON_SOURCE=%PROJECT_ROOT%\assets\icon_source.png"
set "ICON_TARGET=%PROJECT_ROOT%\assets\TempleManager.ico"

echo [1/6] Create virtual environment...
if not exist "%PYTHON_EXE%" (
    py -3.12 -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
) else (
    echo     Existing venv found. Skip.
)

echo [2/6] Upgrade pip...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/6] Install dependencies...
"%PYTHON_EXE%" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto :fail

echo [4/6] Run tests...
"%PYTHON_EXE%" -m pytest -q
if errorlevel 1 goto :fail

echo [5/6] Prepare icon...
where magick >nul 2>nul
if errorlevel 1 (
    echo     ImageMagick not found. Skip icon generation.
) else (
    if exist "%ICON_SOURCE%" (
        magick "%ICON_SOURCE%" -define icon:auto-resize=256,128,64,48,32,24,16 "%ICON_TARGET%"
        if errorlevel 1 goto :fail
    ) else (
        echo     icon_source.png not found. Skip icon generation.
    )
)

echo [6/6] Run PyInstaller...
"%PYTHON_EXE%" -m PyInstaller app/main.py ^
 --noconfirm ^
 --clean ^
 --windowed ^
 --onefile ^
 --name TempleManager ^
 --icon "%ICON_TARGET%" ^
 --paths . ^
 --add-data "app/scheduler/scheduler_config.yaml;app/scheduler" ^
 --add-data "app/resources;app/resources"
if errorlevel 1 goto :fail

echo.
echo Build complete: %PROJECT_ROOT%\dist\TempleManager.exe
exit /b 0

:fail
echo.
echo Build failed. Check the log above.
exit /b 1
