@echo off
REM Setup VS Code debug environment for Labelme
REM This script finds conda Python and updates VS Code settings

echo Setting up VS Code debug environment...
echo.

REM Use PowerShell script to find and update Python path
powershell -ExecutionPolicy Bypass -File "%~dp0update_vscode_python_path.ps1"

if %ERRORLEVEL% == 0 (
    echo.
    echo Setup completed successfully!
    echo.
    echo You can now:
    echo   1. Press F5 to start debugging
    echo   2. Or select "Python: Labelme" from the debug panel
    echo.
) else (
    echo.
    echo Setup failed. Please check the error messages above.
    echo.
    echo Manual setup:
    echo   1. Press Ctrl+Shift+P in VS Code
    echo   2. Type "Python: Select Interpreter"
    echo   3. Choose the conda environment 'labelme' Python
    echo.
)

pause
