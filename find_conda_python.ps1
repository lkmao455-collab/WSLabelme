# Find conda Python executable path
# This script uses the same logic as check_and_move.ps1

param(
    [string]$EnvName = "labelme"
)

# Function to find conda Python executable
function Get-CondaPython {
    param([string]$EnvName)
    
    # Try common conda installation paths
    $condaPaths = @(
        "$env:USERPROFILE\anaconda3",
        "$env:USERPROFILE\miniconda3",
        "$env:ProgramData\anaconda3",
        "$env:ProgramData\miniconda3",
        "$env:LOCALAPPDATA\anaconda3",
        "$env:LOCALAPPDATA\miniconda3",
        "C:\anaconda3",
        "C:\miniconda3"
    )
    
    foreach ($condaPath in $condaPaths) {
        if (Test-Path $condaPath) {
            $pythonPath = Join-Path $condaPath "envs\$EnvName\python.exe"
            if (Test-Path $pythonPath) {
                Write-Host "Found conda environment at: $pythonPath"
                return $pythonPath
            }
        }
    }
    
    # Try using conda command to get environment path
    try {
        $condaCmd = Get-Command conda -ErrorAction SilentlyContinue
        if ($condaCmd) {
            # Get conda base path
            $condaBase = conda info --base 2>$null
            if ($condaBase) {
                $condaBase = $condaBase.Trim()
                $pythonPath = Join-Path $condaBase "envs\$EnvName\python.exe"
                if (Test-Path $pythonPath) {
                    Write-Host "Found conda environment via conda command: $pythonPath"
                    return $pythonPath
                }
            }
        }
    } catch {
        # Ignore errors
    }
    
    return $null
}

# Get Python executable
$pythonExe = Get-CondaPython -EnvName $EnvName

if ($pythonExe) {
    Write-Output $pythonExe
    exit 0
} else {
    Write-Host "Error: Could not find conda environment '$EnvName'" -ForegroundColor Red
    Write-Host "Trying to use conda run as fallback..." -ForegroundColor Yellow
    
    # Check if conda command exists
    $condaCmd = Get-Command conda -ErrorAction SilentlyContinue
    if ($condaCmd) {
        Write-Host "Conda command found. You can use: conda run -n $EnvName python -m labelme" -ForegroundColor Green
        exit 1
    } else {
        Write-Host "Error: Conda command not found in PATH" -ForegroundColor Red
        exit 1
    }
}
