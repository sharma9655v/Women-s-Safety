$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "== Starting infra (postgis, redis, osrm) ==" -ForegroundColor Cyan
cmd /c "docker compose up -d --build postgis redis osrm 2>nul"
if ($LASTEXITCODE -ne 0) { Write-Error "docker compose up failed (exit $LASTEXITCODE)." }

Write-Host "== Waiting for PostGIS ==" -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
  docker compose exec -T postgis pg_isready -U postgres -d mapforwomen *> $null
  if ($LASTEXITCODE -eq 0) { $ready = $true; break }
  Start-Sleep -Seconds 2
}
if (-not $ready) { Write-Error "PostGIS did not become ready in time." }

Write-Host "== Seeding demo evidence ==" -ForegroundColor Cyan
Push-Location "..\apps\api"
try {
  uv run python -m app.seed_demo
  if ($LASTEXITCODE -ne 0) { throw "Seeding failed (exit $LASTEXITCODE)." }
} finally {
  Pop-Location
}

Write-Host "== Starting api + web ==" -ForegroundColor Cyan
cmd /c "docker compose up -d --build api web 2>nul"
if ($LASTEXITCODE -ne 0) { Write-Error "docker compose up failed (exit $LASTEXITCODE)." }

Start-Sleep -Seconds 6
Write-Host ""
Write-Host "Demo running at:" -ForegroundColor Green
Write-Host "  http://localhost:3000 (web)"
Write-Host "  http://localhost:8000/docs (API)"
