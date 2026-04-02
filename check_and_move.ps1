# Build labelme executable using PyInstaller

# Check for both onefile and onedir modes
$exePathOnefile = "dist\Labelme.exe"
$exePathOnedir = "dist\Labelme\Labelme.exe"
$exePath = $null

if (Test-Path $exePathOnedir) {
    $exePath = $exePathOnedir
    Write-Host "Found exe in onedir mode: $exePath"
} elseif (Test-Path $exePathOnefile) {
    $exePath = $exePathOnefile
    Write-Host "Found exe in onefile mode: $exePath"
}
$specFile = "labelme.spec"
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
    Write-Host "Warning: Could not find conda environment '$condaEnvName'"
    Write-Host "Checking if conda command is available..."
    
    # Check if conda command exists
    $condaCmd = Get-Command conda -ErrorAction SilentlyContinue
    if ($condaCmd) {
        Write-Host "Found conda command, will use 'conda run'"
        $useCondaRun = $true
    } else {
        Write-Host "Error: Neither conda environment nor conda command found!"
        Write-Host "Please ensure:"
        Write-Host "  1. Conda is installed and in PATH, or"
        Write-Host "  2. The '$condaEnvName' environment exists in a standard location"
        exit 1
    }
} else {
    Write-Host "Found Python in conda environment: $pythonExe"
    $useCondaRun = $false
}

# Function to wait for build completion
function Wait-ForBuild {
    param(
        [string]$ExePath,
        [int]$MaxWaitMinutes = 60,
        [int]$CheckIntervalSeconds = 30
    )
    
    $maxWait = $MaxWaitMinutes * 60
    $waited = 0
    
    Write-Host "Waiting for build to complete..."
    Write-Host "This may take 10-30 minutes for large applications"
    
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds $CheckIntervalSeconds
        $waited += $CheckIntervalSeconds
        
        if (Test-Path $ExePath) {
            Write-Host "Build completed! Exe file found."
            return $true
        }
        
        $minutes = [math]::Floor($waited / 60)
        $seconds = $waited % 60
        Write-Host "Waiting... ($minutes min $seconds sec elapsed)"
    }
    
    Write-Host "Build timeout after $MaxWaitMinutes minutes"
    return $false
}

# Check if exe file exists
if ($exePath -and (Test-Path $exePath)) {
    Write-Host "Found exe file: $exePath"
} else {
    Write-Host "Exe file not found. Looking for:"
    Write-Host "  - $exePathOnedir"
    Write-Host "  - $exePathOnefile"
    Write-Host "Starting build process..."
    
    # Check if spec file exists
    if (-not (Test-Path $specFile)) {
        Write-Host "Error: $specFile not found!"
        Write-Host "Please make sure labelme.spec exists in the current directory"
        exit 1
    }
    
    # Start build process
    Write-Host "Running PyInstaller with conda environment '$condaEnvName'..."
    
    $buildProcess = $null
    
    if ($useCondaRun) {
        # Use conda run to execute in the environment
        try {
            $buildProcess = Start-Process -FilePath "conda" -ArgumentList "run", "-n", $condaEnvName, "python", "-m", "PyInstaller", $specFile, "--clean", "--noconfirm" -NoNewWindow -PassThru -ErrorAction Stop
        } catch {
            Write-Host "Error: Failed to start conda run command"
            Write-Host "Error message: $($_.Exception.Message)"
            Write-Host ""
            Write-Host "Trying alternative: Activating conda environment first..."
            
            # Try to find conda activate script
            $condaActivate = $null
            $possibleCondaPaths = @(
                "$env:USERPROFILE\anaconda3\Scripts\activate.bat",
                "$env:USERPROFILE\miniconda3\Scripts\activate.bat",
                "$env:ProgramData\anaconda3\Scripts\activate.bat",
                "$env:ProgramData\miniconda3\Scripts\activate.bat"
            )
            
            foreach ($path in $possibleCondaPaths) {
                if (Test-Path $path) {
                    $condaActivate = $path
                    break
                }
            }
            
            if ($condaActivate) {
                $condaRoot = Split-Path (Split-Path $condaActivate)
                $pythonExe = Join-Path $condaRoot "envs\$condaEnvName\python.exe"
                if (Test-Path $pythonExe) {
                    Write-Host "Found Python at: $pythonExe"
                    $buildProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m", "PyInstaller", $specFile, "--clean", "--noconfirm" -NoNewWindow -PassThru -ErrorAction Stop
                }
            }
            
            if (-not $buildProcess) {
                Write-Host "Error: Could not start build process"
                exit 1
            }
        }
    } else {
        # Use the Python executable directly
        try {
            $buildProcess = Start-Process -FilePath $pythonExe -ArgumentList "-m", "PyInstaller", $specFile, "--clean", "--noconfirm" -NoNewWindow -PassThru -ErrorAction Stop
        } catch {
            Write-Host "Error: Failed to start Python process"
            Write-Host "Error message: $($_.Exception.Message)"
            Write-Host "Python path: $pythonExe"
            exit 1
        }
    }
    
    if (-not $buildProcess) {
        Write-Host "Error: Build process failed to start"
        exit 1
    }
    
    Write-Host "Build process started (PID: $($buildProcess.Id))"
    Write-Host "Waiting for build to complete..."
    
    # Wait for build process to complete
    $buildProcess.WaitForExit()
    
    if ($buildProcess.ExitCode -ne 0) {
        Write-Host "Build failed with exit code: $($buildProcess.ExitCode)"
        exit 1
    }
    
    # Wait for exe file to be generated (sometimes it takes a moment after process exits)
    # Check both onefile and onedir modes
    $buildSuccess = $false
    $waited = 0
    $maxWait = 5 * 60  # 5 minutes
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 10
        $waited += 10
        
        if (Test-Path $exePathOnedir) {
            $exePath = $exePathOnedir
            $buildSuccess = $true
            Write-Host "Build completed! Exe file found in onedir mode."
            break
        } elseif (Test-Path $exePathOnefile) {
            $exePath = $exePathOnefile
            $buildSuccess = $true
            Write-Host "Build completed! Exe file found in onefile mode."
            break
        }
        
        Write-Host "Waiting for exe file... ($waited seconds)"
    }
    
    if (-not $buildSuccess) {
        Write-Host "Build process completed but exe file not found"
        Write-Host "Please check the build output for errors"
        exit 1
    }
}

# Build completed successfully
if ($exePath) {
    Write-Host ""
    Write-Host "Build completed successfully!"
    if ($exePath -like "*\Labelme\Labelme.exe") {
        Write-Host "Executable location: $exePath"
        Write-Host "Build mode: onedir (directory mode)"
    } else {
        Write-Host "Executable location: $exePath"
        Write-Host "Build mode: onefile (single file mode)"
    }
} else {
    Write-Host "Build completed, but exe file location is unknown"
}
Write-Host "Done!"
