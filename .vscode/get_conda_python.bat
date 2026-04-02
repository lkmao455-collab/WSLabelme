@echo off
REM Get conda Python executable path for VS Code debugger
REM This uses the same logic as check_and_move.ps1

set CONDA_ENV_NAME=labelme

REM Try common conda installation paths
if exist "%USERPROFILE%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo %USERPROFILE%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)
if exist "%USERPROFILE%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo %USERPROFILE%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)
if exist "%ProgramData%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo %ProgramData%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)
if exist "%ProgramData%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo %ProgramData%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)
if exist "%LOCALAPPDATA%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo %LOCALAPPDATA%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)
if exist "%LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo %LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)
if exist "C:\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo C:\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)
if exist "C:\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    echo C:\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    exit /b 0
)

REM Try using conda command
where conda >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "tokens=*" %%i in ('conda info --base 2^>nul') do set CONDA_BASE=%%i
    if defined CONDA_BASE (
        if exist "%CONDA_BASE%\envs\%CONDA_ENV_NAME%\python.exe" (
            echo %CONDA_BASE%\envs\%CONDA_ENV_NAME%\python.exe
            exit /b 0
        )
    )
)

REM Fallback to system python
python --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    where python
    exit /b 0
)

echo Error: Could not find Python executable
exit /b 1
