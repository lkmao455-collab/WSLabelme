@echo off
REM Run Labelme using conda environment
REM This script uses the same conda environment detection as check_and_move.ps1

set CONDA_ENV_NAME=labelme

REM Try to find conda Python executable
set PYTHON_EXE=

REM Try common conda installation paths
if exist "%USERPROFILE%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=%USERPROFILE%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%USERPROFILE%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=%USERPROFILE%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%ProgramData%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=%ProgramData%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%ProgramData%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=%ProgramData%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%LOCALAPPDATA%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "%LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "C:\anaconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=C:\anaconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)
if exist "C:\miniconda3\envs\%CONDA_ENV_NAME%\python.exe" (
    set PYTHON_EXE=C:\miniconda3\envs\%CONDA_ENV_NAME%\python.exe
    goto :found
)

REM Try using conda command
where conda >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "tokens=*" %%i in ('conda info --base 2^>nul') do set CONDA_BASE=%%i
    if defined CONDA_BASE (
        if exist "%CONDA_BASE%\envs\%CONDA_ENV_NAME%\python.exe" (
            set PYTHON_EXE=%CONDA_BASE%\envs\%CONDA_ENV_NAME%\python.exe
            goto :found
        )
    )
)

REM If not found, try using conda run
where conda >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Using conda run to execute in %CONDA_ENV_NAME% environment...
    conda run -n %CONDA_ENV_NAME% python -m labelme %*
    goto :end
)

REM If still not found, use system python (fallback)
echo Warning: Could not find conda environment '%CONDA_ENV_NAME%'
echo Using system Python as fallback...
python -m labelme %*
goto :end

:found
echo Found conda environment: %PYTHON_EXE%
"%PYTHON_EXE%" -m labelme %*

:end
