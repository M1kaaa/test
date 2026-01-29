$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "=== Upload to GitHub ===" -ForegroundColor Cyan

cmd /c "gh auth status 2>nul"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in. Try web login (browser will open)..."
    $p = Start-Process -FilePath "gh" -ArgumentList "auth","login","-h","github.com","-p","https","-w" -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) {
        Write-Host ""
        Write-Host "Web login failed. Use token: https://github.com/settings/tokens"
        Write-Host "Create token (repo scope), paste below (input hidden)."
        $t = Read-Host -AsSecureString "Token"
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($t)
        $token = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        $token | gh auth login --with-token
        if ($LASTEXITCODE -ne 0) { Write-Host "Token login failed."; exit 1 }
    }
}

Set-Location $projectRoot
$repoName = "patch-cord-calculator"

Write-Host "Creating repo '$repoName' and pushing..."
gh repo create $repoName --private --source=. --remote=origin --push

if ($LASTEXITCODE -eq 0) {
    $url = gh repo view $repoName --json url -q .url
    Write-Host "Done. Repo: $url" -ForegroundColor Green
} else {
    $remote = git remote get-url origin 2>$null
    if (-not $remote) {
        $user = (gh api user -q .login)
        git remote add origin "https://github.com/$user/$repoName.git"
    }
    git push -u origin main
    if ($LASTEXITCODE -eq 0) { Write-Host "Done. Pushed to origin/main." -ForegroundColor Green }
    else { Write-Host "Push failed. Check: git remote -v"; exit 1 }
}
