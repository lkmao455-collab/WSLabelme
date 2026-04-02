# Move built exe file to myapp folder

$exePathOnefile = "dist\Labelme.exe"
$exePathOnedir = "dist\Labelme\Labelme.exe"
$myappDir = "myapp"

# Check for both onefile and onedir modes
$exePath = $null
if (Test-Path $exePathOnedir) {
    $exePath = $exePathOnedir
    Write-Host "Found exe in onedir mode: $exePath"
} elseif (Test-Path $exePathOnefile) {
    $exePath = $exePathOnefile
    Write-Host "Found exe in onefile mode: $exePath"
} else {
    Write-Host "Error: Exe file not found!"
    Write-Host "Looking for:"
    Write-Host "  - $exePathOnedir"
    Write-Host "  - $exePathOnefile"
    Write-Host ""
    Write-Host "Please run build.ps1 first to build the executable."
    exit 1
}

# Create myapp folder
if (-not (Test-Path $myappDir)) {
    New-Item -ItemType Directory -Path $myappDir | Out-Null
    Write-Host "Created myapp folder"
}

# Move exe file (and entire directory if onedir mode)
if ($exePath -like "*\Labelme\Labelme.exe") {
    # Onedir mode: move the entire directory
    $sourceDir = Split-Path $exePath
    $destDir = Join-Path $myappDir "Labelme"
    if (Test-Path $destDir) {
        Remove-Item $destDir -Recurse -Force
        Write-Host "Removed old Labelme directory"
    }
    Move-Item $sourceDir $destDir -Force
    Write-Host "Successfully moved Labelme directory to $destDir"
    Write-Host "Executable is at: $(Join-Path $destDir 'Labelme.exe')"
} else {
    # Onefile mode: move just the exe
    $destPath = Join-Path $myappDir "Labelme.exe"
    if (Test-Path $destPath) {
        Remove-Item $destPath -Force
        Write-Host "Removed old exe file"
    }
    Move-Item $exePath $destPath -Force
    Write-Host "Successfully moved Labelme.exe to $destPath"
}
Write-Host "Done!"
