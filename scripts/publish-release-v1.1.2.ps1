# Deprecated: use .\scripts\publish-github-release.ps1 (reads version from build.json).
Set-Location (Split-Path $PSScriptRoot)
& ".\scripts\publish-github-release.ps1" @args
