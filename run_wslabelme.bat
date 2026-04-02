@echo off
REM Run WSLabelme with training curve docks
REM 使用本地源码运行 WSLabelme

echo Starting WSLabelme with training curves...

REM 使用当前目录的 Python 运行 main.py
python main.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo Error: Failed to run main.py
    echo Please make sure you are in the correct directory and have the required dependencies installed.
    pause
)
