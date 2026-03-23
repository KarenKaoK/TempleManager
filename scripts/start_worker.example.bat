@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
set "STDOUT_LOG=%PROJECT_ROOT%\worker_stdout.log"
cd /d "%PROJECT_ROOT%"

echo [%date% %time%] start>> "%STDOUT_LOG%"
echo LOCALAPPDATA=%LOCALAPPDATA%>> "%STDOUT_LOG%"
echo [%date% %time%] cwd=%cd%>> "%STDOUT_LOG%"

if not exist "%PROJECT_ROOT%\temple_venv\Scripts\python.exe" (
  echo [%date% %time%] python not found>> "%STDOUT_LOG%"
  exit /b 1
)

"%PROJECT_ROOT%\temple_venv\Scripts\python.exe" -m app.scheduler.worker >> "%STDOUT_LOG%" 2>&1

echo [%date% %time%] exitcode=%errorlevel%>> "%STDOUT_LOG%"
exit /b %errorlevel%
