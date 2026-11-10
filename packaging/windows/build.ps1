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
Start-Transcript -Path (Join-Path $Work "build.log") | Out-Null
Push-Location $Repo
try {
    $Icon = Join-Path $PSScriptRoot "cobgdb.ico"
    $Resources = Join-Path $Repo "cobgdb_python/resources"
    $Examples = Join-Path $Work "examples"
    & $Python (Join-Path $Repo "scripts/stage_examples.py") $Examples
    if ($LASTEXITCODE -ne 0) { throw "Example staging failed. Build work is in $Work" }
    $Extra = @("--icon", $Icon, "--add-data", "${Resources}:cobgdb_python/resources",
               "--add-data", "${Examples}:cobgdb_python/example_templates")

    & $Python -m PyInstaller --noconfirm --onefile --console --noupx --name cobol-debugger `
        --paths $Repo --distpath $Output --workpath (Join-Path $Work "build") `
        --specpath $Work @Extra (Join-Path $PSScriptRoot "launcher.py")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed. Build work is in $Work" }
    $Binary = Join-Path $Output "cobol-debugger.exe"
    Copy-Item -Path $Examples -Destination $Output -Recurse -Force
    & $InnoCompiler "/DAppBinary=$Binary" "/DExampleFiles=$Examples" "/O$Output" (Join-Path $PSScriptRoot "installer.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed. Build work is in $Work" }
    $Installer = Join-Path $Output "COBOL-Debugger-0.1.0-win11-x64-setup.exe"
    $Hashes = Get-FileHash -Algorithm SHA256 $Binary,$Installer
    $Hashes | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path -Leaf $_.Path)" } |
        Set-Content -Encoding ascii (Join-Path $Output "SHA256SUMS")
    Stop-Transcript | Out-Null
    & $Python (Join-Path $Repo "scripts/release_bundle.py") --system windows11-x64 --app cobol-debugger `
        --output $Output --source $Repo --files $Binary $Installer (Join-Path $Output "SHA256SUMS") (Join-Path $Work "build.log")
    if ($LASTEXITCODE -ne 0) { throw "Release collection failed. Build files remain in $Output" }
    Write-Host "Build artifacts: $Output"
} finally {
    Pop-Location
}
