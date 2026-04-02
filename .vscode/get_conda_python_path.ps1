# Get conda Python path for VS Code
# This script is called by VS Code to get the Python interpreter path

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
} else {
    # Fallback: try to get from VS Code's Python extension
    Write-Output ""
}
