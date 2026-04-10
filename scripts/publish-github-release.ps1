# Create or update a GitHub Release using the distribute zip (requires: gh auth login).
# Reads version from build.json. Uploads release/<archive_stem>-<version>.zip (two .wotmod files only).
# Usage: .\scripts\publish-github-release.ps1 [-Tag v1.2.3] [-Notes "markdown..."]

param(
    [string]$Tag = "",
    [string]$Notes = ""
)

$GhDir = "C:\Program Files\GitHub CLI"
if (Test-Path (Join-Path $GhDir "gh.exe")) {
    $env:Path = "$GhDir;$env:Path"
}

$RepoRoot = Split-Path $PSScriptRoot
Set-Location $RepoRoot

$Repo = "Walaxy/WOT-Realtime-Dispersion-Aim-Time-Remaining"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) not found. Install from https://cli.github.com/"
}

& gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in. Run: gh auth login"
    exit 1
}

$cfg = Get-Content (Join-Path $RepoRoot "build.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$ver = $cfg.info.version
$archiveName = $cfg.info.archive_name
if (-not $archiveName.ToLower().EndsWith(".zip")) {
    $archiveName = $archiveName + ".zip"
}
$archStem = $archiveName.Substring(0, $archiveName.Length - ".zip".Length)

if (-not $Tag) {
    $Tag = "v$ver"
}

$ReleaseZip = Join-Path $RepoRoot (Join-Path "release" ("{0}-{1}.zip" -f $archStem, $ver))
if (-not (Test-Path $ReleaseZip)) {
    Write-Error "Missing $ReleaseZip — run: python build.py --distribute"
}

if (-not $Notes) {
    $Notes = "Release **$ver**. Install: copy both `.wotmod` files from the zip into `WorldOfTanks/mods/<game_version>/`."
}

$Title = "$ver – Realtime Dispersion & Aim Time Remaining (with ModSettingsAPI zip)"

$view = & gh release view $Tag --repo $Repo 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Release $Tag exists; uploading release zip (--clobber)..."
    & gh release upload $Tag --repo $Repo --clobber $ReleaseZip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done: https://github.com/$Repo/releases/tag/$Tag"
    exit 0
}

Write-Host "Creating release $Tag..."
& gh release create $Tag --repo $Repo --title $Title --notes $Notes $ReleaseZip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done: https://github.com/$Repo/releases/tag/$Tag"
