# Create or update a GitHub Release using the bundled GitHub-Release zip (requires: gh auth login).
# Reads version and package stem from build.json. Uploads only *-GitHub-Release.zip.
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
$pkg = $cfg.info.package_name
if (-not $pkg.EndsWith(".wotmod")) { $pkg = $pkg + ".wotmod" }
$stem = $pkg.Substring(0, $pkg.Length - ".wotmod".Length)

if (-not $Tag) {
    $Tag = "v$ver"
}

$ReleaseZip = Join-Path $RepoRoot (Join-Path "release" ("{0}-{1}-GitHub-Release.zip" -f $stem, $ver))
if (-not (Test-Path $ReleaseZip)) {
    Write-Error "Missing $ReleaseZip — run: python build.py --distribute"
}

if (-not $Notes) {
    $Notes = "Release **$ver**. Install: copy both `.wotmod` files from the zip into `WorldOfTanks/mods/<game_version>/`."
}

$Title = "$ver – Realtime Dispersion & Aim Time Remaining (with ModSettingsAPI zip)"

$view = & gh release view $Tag --repo $Repo 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Release $Tag exists; uploading GitHub-Release zip (--clobber)..."
    & gh release upload $Tag --repo $Repo --clobber $ReleaseZip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done: https://github.com/$Repo/releases/tag/$Tag"
    exit 0
}

Write-Host "Creating release $Tag..."
& gh release create $Tag --repo $Repo --title $Title --notes $Notes $ReleaseZip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done: https://github.com/$Repo/releases/tag/$Tag"
