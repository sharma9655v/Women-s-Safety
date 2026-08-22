# Download an OSM PBF extract and record its provenance manifest.
# Usage:
#   powershell -File data/loaders/fetch-osm.ps1 `
#     -Url "https://download.geofabrik.de/asia/india/northern-zone-latest.osm.pbf" `
#     -Out "data/india-latest.osm.pbf" `
#     -Dataset "osm-india"
param(
    [string]$Url = "https://download.geofabrik.de/asia/india/northern-zone-latest.osm.pbf",
    [string]$Out = "",
    [string]$Dataset = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $Out) { $Out = Join-Path $repoRoot "data\northern-zone-latest.osm.pbf" }
if (-not $Dataset) { $Dataset = [System.IO.Path]::GetFileNameWithoutExtension([System.IO.Path]::GetFileNameWithoutExtension($Out)) }

$dataDir = Split-Path -Parent $Out
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$versionsDir = Join-Path $repoRoot "data\versions"
New-Item -ItemType Directory -Force -Path $versionsDir | Out-Null

Write-Host "[fetch-osm] downloading $Url -> $Out"
Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing

# Sanity check: a real PBF is not HTML and is larger than a few MB.
$bytes = [System.IO.File]::ReadAllBytes($Out)
$isHtml = [System.Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(64, $bytes.Length)).TrimStart().StartsWith("<")
if ($isHtml) {
    Remove-Item -LiteralPath $Out -Force
    throw "Downloaded file is an HTML page (wrong URL), not an OSM PBF extract."
}
if ($bytes.Length -lt 1048576) {
    Remove-Item -LiteralPath $Out -Force
    throw "Downloaded file is suspiciously small ($($bytes.Length) bytes). Aborting to protect provenance."
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Out).Hash
$size = (Get-Item -LiteralPath $Out).Length
$manifest = [ordered]@{
    dataset       = $Dataset
    source        = $Url
    downloaded_at = [DateTime]::UtcNow.ToString('yyyy-MM-dd\THH\:mm\:ss\Z')
    sha256        = $hash
    bytes         = $size
    notes         = ""
}
$manifestPath = Join-Path $versionsDir "$Dataset-$(Get-Date -Format 'yyyyMMdd').json"
$manifest | ConvertTo-Json -Depth 3 | Set-Content -Path $manifestPath -Encoding utf8
Write-Host "[fetch-osm] manifest written: $manifestPath"