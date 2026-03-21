@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

if not exist "%LOCALAPPDATA%\TempleManager" mkdir "%LOCALAPPDATA%\TempleManager"

"%PROJECT_ROOT%\temple_venv\Scripts\python.exe" -m app.scheduler.worker >> "%LOCALAPPDATA%\TempleManager\worker_stdout.log" 2>&1
