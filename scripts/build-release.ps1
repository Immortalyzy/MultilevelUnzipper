param(
    [string]$Version = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [switch]$Zip,
    [switch]$SkipClean
)

$ErrorActionPreference = "Stop"

function Assert-Command {
    param(
        [Parameter(Mandatory = $true)][string]$CommandName,
        [Parameter(Mandatory = $true)][string]$InstallHint
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Missing required command '$CommandName'. $InstallHint"
    }
}

function Assert-PyInstallerModule {
    python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Missing required Python module 'PyInstaller'. Install it with: python -m pip install pyinstaller"
    }
}

function Run-BuildCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host "[build] $Description"
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Build step failed: $Description"
    }
}

function Assert-Path {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet("Leaf", "Container")] [string]$PathType
    )

    if (-not (Test-Path -Path $Path -PathType $PathType)) {
        throw "Expected $PathType was not found: $Path"
    }
}

$scriptRoot = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..")
Set-Location $repoRoot

Assert-Command -CommandName "python" -InstallHint "Install Python 3 and ensure it is available on PATH."
Assert-PyInstallerModule

$buildDir = Join-Path $repoRoot "build"
$distDir = Join-Path $repoRoot "dist"
$releaseRootDir = Join-Path $distDir "release"
$releaseDir = Join-Path $releaseRootDir $Version

$mainSpec = Join-Path $repoRoot "MultilevelUnzipper.spec"
$installerSpec = Join-Path $repoRoot "install.spec"

$mainOutputDir = Join-Path $distDir "MultilevelUnzipper"
$installerOutputExe = Join-Path $distDir "install.exe"

if (-not $SkipClean) {
    Write-Host "[build] Cleaning previous outputs"
    if (Test-Path $buildDir) { Remove-Item -Path $buildDir -Recurse -Force }
    if (Test-Path $mainOutputDir) { Remove-Item -Path $mainOutputDir -Recurse -Force }
    if (Test-Path $installerOutputExe) { Remove-Item -Path $installerOutputExe -Force }
    if (Test-Path $releaseDir) { Remove-Item -Path $releaseDir -Recurse -Force }
}

Run-BuildCommand -Description "Build main payload with MultilevelUnzipper.spec" -Arguments @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "$mainSpec"
)

Run-BuildCommand -Description "Build installer with install.spec" -Arguments @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "$installerSpec"
)

Write-Host "[build] Staging release artifacts to dist/release/$Version"
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
Copy-Item -Path $installerOutputExe -Destination (Join-Path $releaseDir "install.exe") -Force
Copy-Item -Path $mainOutputDir -Destination (Join-Path $releaseDir "MultilevelUnzipper") -Recurse -Force

$stagedInstallerExe = Join-Path $releaseDir "install.exe"
$stagedPayloadDir = Join-Path $releaseDir "MultilevelUnzipper"
$stagedMainExe = Join-Path $stagedPayloadDir "MultilevelUnzipper.exe"

Write-Host "[build] Validating staged release layout"
Assert-Path -Path $stagedInstallerExe -PathType Leaf
Assert-Path -Path $stagedPayloadDir -PathType Container
Assert-Path -Path $stagedMainExe -PathType Leaf

if ($Zip) {
    $zipPath = Join-Path $releaseRootDir ("MultilevelUnzipper_{0}.zip" -f $Version)
    if (Test-Path $zipPath) {
        Remove-Item -Path $zipPath -Force
    }

    Write-Host "[build] Creating zip archive: $zipPath"
    Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -Force
    Assert-Path -Path $zipPath -PathType Leaf
}

Write-Host ""
Write-Host "Release build complete."
Write-Host "Version: $Version"
Write-Host "Output:  $releaseDir"
