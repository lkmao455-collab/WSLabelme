# Run Labelme using conda environment
# This script uses the same conda environment detection as check_and_move.ps1

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$condaEnvName = "labelme"

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

# Get Python executable from conda environment
$pythonExe = Get-CondaPython -EnvName $condaEnvName

if (-not $pythonExe) {
    Write-Host "Warning: Could not find conda environment '$condaEnvName'" -ForegroundColor Yellow
    Write-Host "Checking if conda command is available..." -ForegroundColor Yellow
    
    # Check if conda command exists
    $condaCmd = Get-Command conda -ErrorAction SilentlyContinue
    if ($condaCmd) {
        Write-Host "Using 'conda run' to execute in $condaEnvName environment..." -ForegroundColor Green
        $allArgs = @("-n", $condaEnvName, "python", "-m", "labelme") + $Arguments
        & conda run $allArgs
        exit $LASTEXITCODE
    } else {
        Write-Host "Error: Neither conda environment nor conda command found!" -ForegroundColor Red
        Write-Host "Please ensure:" -ForegroundColor Red
        Write-Host "  1. Conda is installed and in PATH, or" -ForegroundColor Red
        Write-Host "  2. The '$condaEnvName' environment exists in a standard location" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Using Python: $pythonExe" -ForegroundColor Green
    $allArgs = @("-m", "labelme") + $Arguments
    & $pythonExe $allArgs
    exit $LASTEXITCODE
}
