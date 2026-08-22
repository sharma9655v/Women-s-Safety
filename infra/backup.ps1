# Phase 8 ops: backup the Map for Women database.
# Runs pg_dump inside the postgis container and rotates backups,
# keeping $KeepCount newest dumps in infra/backups/.
#
# Usage (from the repo root):
#   powershell -File infra\backup.ps1
# Optional: powershell -File infra\backup.ps1 -KeepCount 7

param(
    [int]$KeepCount = 5,
    [string]$Container = "map-for-women-postgis-1",
    [string]$DbUser = "postgres",
    [string]$DbName = "mapforwomen"
)

$ErrorActionPreference = "Stop"
$BackupDir = Join-Path $PSScriptRoot "backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$stamp = Get-Date -Format "yyyyMMddTHHmmss"
$out = Join-Path $BackupDir "mapforwomen-$stamp.dump"

# --format=custom is self-verifying and restores with pg_restore.
docker exec $Container pg_dump -U $DbUser -Fc -d $DbName -f /tmp/backup.dump
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed (exit $LASTEXITCODE)" }
docker cp "${Container}:/tmp/backup.dump" $out
if ($LASTEXITCODE -ne 0) { throw "docker cp failed (exit $LASTEXITCODE)" }
docker exec $Container rm /tmp/backup.dump

Write-Host "wrote $out"

# Rotate: keep only the newest $KeepCount dumps.
Get-ChildItem $BackupDir -Filter "mapforwomen-*.dump" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $KeepCount |
    ForEach-Object { Remove-Item $_.FullName; Write-Host "removed $($_.FullName)" }
