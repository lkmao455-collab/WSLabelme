@echo off
REM Setup VS Code Python interpreter path
REM This script finds the conda Python and updates VS Code settings
REM Uses PowerShell script for more reliable detection

echo Finding conda Python environment...
echo.

REM Try using PowerShell script first (more reliable)
powershell -ExecutionPolicy Bypass -File "%~dp0find_conda_python.ps1" > "%TEMP%\conda_python_path.txt" 2>&1
if %ERRORLEVEL% == 0 (
    set /p PYTHON_PATH=<"%TEMP%\conda_python_path.txt"
    if defined PYTHON_PATH (
        echo Found Python: %PYTHON_PATH%
        echo.
        echo Please manually set VS Code Python interpreter:
        echo 1. Press Ctrl+Shift+P
        echo 2. Type "Python: Select Interpreter"
        echo 3. Choose: %PYTHON_PATH%
        echo.
        echo Or edit .vscode/settings.json and set:
        echo   "python.defaultInterpreterPath": "%PYTHON_PATH%"
        echo.
        del "%TEMP%\conda_python_path.txt" >nul 2>&1
        pause
        exit /b 0
    )
)

REM Fallback to batch script detection
set CONDA_ENV_NAME=labelme
set PYTHON_PATH=

REM Try common conda installation paths
if exist "%USERPROFILE%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=%USERPROFILE%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%USERPROFILE%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=%USERPROFILE%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%ProgramData%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=%ProgramData%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%ProgramData%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=%ProgramData%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%LOCALAPPDATA%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=%LOCALAPPDATA%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=%LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "C:\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=C:\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "C:\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_PATH=C:\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)

REM Try using conda command
where conda >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "tokens=*" %%i in ('conda info --base 2^>nul') do set CONDA_BASE=%%i
    if defined CONDA_BASE (
        if exist "%CONDA_BASE%\envs\%CONDA_ENV_NAME%\python.exe" (
            set PYTHON_PATH=%CONDA_BASE%\envs\%CONDA_ENV_NAME%\python.exe
            goto :found
        )
    )
)

echo Error: Could not find conda environment '%CONDA_ENV_NAME%'
echo.
echo Please ensure:
echo   1. Conda is installed and in PATH, or
echo   2. The '%CONDA_ENV_NAME%' environment exists in a standard location
echo.
echo You can also manually set the Python interpreter in VS Code:
echo   1. Press Ctrl+Shift+P
echo   2. Type "Python: Select Interpreter"
echo   3. Browse to your conda environment Python
echo.
del "%TEMP%\conda_python_path.txt" >nul 2>&1
pause
exit /b 1

:found
echo Found Python: %PYTHON_PATH%
echo.
echo Please manually set VS Code Python interpreter:
echo 1. Press Ctrl+Shift+P
echo 2. Type "Python: Select Interpreter"
echo 3. Choose: %PYTHON_PATH%
echo.
echo Or edit .vscode/settings.json and set:
echo   "python.defaultInterpreterPath": "%PYTHON_PATH%"
echo.
del "%TEMP%\conda_python_path.txt" >nul 2>&1
pause
