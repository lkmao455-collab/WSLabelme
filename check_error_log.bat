@echo off
REM Check labelme error log file

set LOG_FILE=%LOCALAPPDATA%\labelme\labelme.log

if exist "%LOG_FILE%" (
    echo Found log file: %LOG_FILE%
    echo.
    echo Last 50 lines of log:
    echo ========================================
    powershell -Command "Get-Content '%LOG_FILE%' -Tail 50"
) else (
    echo Log file not found: %LOG_FILE%
    echo.
    echo The log file will be created when labelme runs.
)

pause
