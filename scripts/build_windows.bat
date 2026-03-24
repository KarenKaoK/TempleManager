@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

cd /d "%PROJECT_ROOT%"

set "VENV_DIR=%PROJECT_ROOT%\temple_venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "ICON_SOURCE=%PROJECT_ROOT%\assets\icon_source.png"
set "ICON_TARGET=%PROJECT_ROOT%\assets\TempleManager.ico"

echo [1/6] 建立虛擬環境...
if not exist "%PYTHON_EXE%" (
    py -3.12 -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
) else (
    echo     已存在，略過建立 venv
)

echo [2/6] 升級 pip...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/6] 安裝相依套件...
"%PYTHON_EXE%" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto :fail

echo [4/6] 執行測試...
"%PYTHON_EXE%" -m pytest -q
if errorlevel 1 goto :fail

echo [5/6] 準備 icon...
where magick >nul 2>nul
if errorlevel 1 (
    echo     找不到 ImageMagick，略過重新產生 .ico
) else (
    if exist "%ICON_SOURCE%" (
        magick "%ICON_SOURCE%" -define icon:auto-resize=256,128,64,48,32,24,16 "%ICON_TARGET%"
        if errorlevel 1 goto :fail
    ) else (
        echo     找不到 icon_source.png，略過重新產生 .ico
    )
)

echo [6/6] 執行 PyInstaller...
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
echo 打包完成：%PROJECT_ROOT%\dist\TempleManager.exe
exit /b 0

:fail
echo.
echo 打包失敗，請檢查上方輸出。
exit /b 1
