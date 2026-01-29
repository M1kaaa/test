# Upload to GitHub using Personal Access Token (no browser).
# 1. Create token: https://github.com/settings/tokens (repo scope)
# 2. Run this script, paste token when asked.

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "=== Upload to GitHub (token) ===" -ForegroundColor Cyan
Write-Host "Create token: https://github.com/settings/tokens (repo scope)"
Write-Host ""

$token = $env:GITHUB_TOKEN
if (-not $token) {
    $token = Read-Host "Paste your GitHub Personal Access Token"
    if ($token) { $token = $token.Trim() }
}
if (-not $token) { Write-Host "No token."; exit 1 }

$token | gh auth login --with-token
if ($LASTEXITCODE -ne 0) { Write-Host "Token login failed."; exit 1 }

Set-Location $projectRoot
$repoName = "patch-cord-calculator"

Write-Host "Creating repo '$repoName' and pushing..."
gh repo create $repoName --private --source=. --remote=origin --push

if ($LASTEXITCODE -eq 0) {
    $url = gh repo view $repoName --json url -q .url
    Write-Host "Done. Repo: $url" -ForegroundColor Green
} else {
    $user = (gh api user -q .login)
    git remote add origin "https://github.com/$user/$repoName.git" 2>$null
    git push -u origin main
    if ($LASTEXITCODE -eq 0) { Write-Host "Done. Pushed." -ForegroundColor Green }
    else { Write-Host "Push failed."; exit 1 }
}
