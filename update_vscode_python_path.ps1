# Update VS Code Python path file
# This script finds conda Python and saves it to .vscode/conda_python_path.txt

$condaEnvName = "labelme"
$outputFile = Join-Path $PSScriptRoot ".vscode\conda_python_path.txt"

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
                Write-Host "Found conda environment at: $pythonPath" -ForegroundColor Green
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
                    Write-Host "Found conda environment via conda command: $pythonPath" -ForegroundColor Green
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
$pythonExe = Get-CondaPython -EnvName $condaEnvName

if ($pythonExe) {
    # Ensure .vscode directory exists
    $vscodeDir = Join-Path $PSScriptRoot ".vscode"
    if (-not (Test-Path $vscodeDir)) {
        New-Item -ItemType Directory -Path $vscodeDir | Out-Null
    }
    
    # Write Python path to file
    $pythonExe | Out-File -FilePath $outputFile -Encoding utf8 -NoNewline
    Write-Host "`nPython path saved to: $outputFile" -ForegroundColor Green
    Write-Host "You can now use F5 to debug Labelme" -ForegroundColor Green
} else {
    Write-Host "`nError: Could not find conda environment '$condaEnvName'" -ForegroundColor Red
    Write-Host "Please ensure:" -ForegroundColor Yellow
    Write-Host "  1. Conda is installed and in PATH" -ForegroundColor Yellow
    Write-Host "  2. The '$condaEnvName' environment exists" -ForegroundColor Yellow
    Write-Host "`nYou can manually set the Python interpreter in VS Code:" -ForegroundColor Yellow
    Write-Host "  1. Press Ctrl+Shift+P" -ForegroundColor Yellow
    Write-Host "  2. Type 'Python: Select Interpreter'" -ForegroundColor Yellow
    Write-Host "  3. Browse to your conda environment Python" -ForegroundColor Yellow
    
    # Write empty file to avoid errors
    "" | Out-File -FilePath $outputFile -Encoding utf8 -NoNewline
    exit 1
}
