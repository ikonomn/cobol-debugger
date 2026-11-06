param(
    [string]$Python = "python",
    [Parameter(Mandatory=$true)][string]$InnoCompiler,
    [string]$Output = ""
)
$ErrorActionPreference = "Stop"
if ($env:OS -ne "Windows_NT") { throw "Build on Windows 11." }
& $Python -c "import platform, sys; sys.exit(0 if sys.getwindowsversion().build >= 22000 and platform.machine().upper() == 'AMD64' else 1)"
if ($LASTEXITCODE -ne 0) { throw "Use 64-bit x86 Python on Windows 11." }
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $Output) { $Output = Join-Path $Repo "dist/windows" }
$Output = (New-Item -ItemType Directory -Force $Output).FullName
$InnoCompiler = (Resolve-Path $InnoCompiler).Path
$Work = Join-Path ([IO.Path]::GetTempPath()) ("cobol-build-" + [guid]::NewGuid())
New-Item -ItemType Directory $Work | Out-Null
Push-Location $Repo
try {
    $Icon = Join-Path $PSScriptRoot "cobgdb.ico"
    $Resources = Join-Path $Repo "cobgdb_python/resources"
    $Extra = @("--icon", $Icon, "--add-data", "${Resources}:cobgdb_python/resources")

    & $Python -m PyInstaller --noconfirm --onefile --console --noupx --name cobgdb-python-gui `
        --paths $Repo --distpath $Output --workpath (Join-Path $Work "build") `
        --specpath $Work @Extra (Join-Path $PSScriptRoot "launcher.py")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed. Build work is in $Work" }
    $Binary = Join-Path $Output "cobgdb-python-gui.exe"
    $Examples = (New-Item -ItemType Directory -Force (Join-Path $Output "examples/gui")).FullName
    foreach ($File in @("README.md", "score.cob", "score_window.c")) {
        Copy-Item (Join-Path $Repo "examples/gui/$File") $Examples -Force
    }
    & $InnoCompiler "/DAppBinary=$Binary" "/DExampleFiles=$Examples" "/O$Output" (Join-Path $PSScriptRoot "installer.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed. Build work is in $Work" }
    $Installer = Join-Path $Output "COBGDB-0.1.0-win11-x64-setup.exe"
    $Hashes = Get-FileHash -Algorithm SHA256 $Binary,$Installer
    $Hashes | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path -Leaf $_.Path)" } |
        Set-Content -Encoding ascii (Join-Path $Output "SHA256SUMS")
    Write-Host "Build artifacts: $Output"
} finally {
    Pop-Location
}
