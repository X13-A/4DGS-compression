param(
    [Parameter(Mandatory = $true)]
    [string]$VideosDir,
    [Parameter(Mandatory = $true)]
    [string]$MetadataDir,
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,
    [string]$TempTexturesDir = "",
    [switch]$CleanTemp
)

$ErrorActionPreference = 'Stop'

$videosDir = [IO.Path]::GetFullPath($VideosDir)
$metadataDir = [IO.Path]::GetFullPath($MetadataDir)
$outputDir = [IO.Path]::GetFullPath($OutputDir)

if ([string]::IsNullOrWhiteSpace($TempTexturesDir)) {
    $TempTexturesDir = Join-Path $outputDir "_textures_tmp"
}
$tempTexturesDir = [IO.Path]::GetFullPath($TempTexturesDir)

if (-not (Test-Path -LiteralPath $videosDir)) {
    throw "Videos dir not found: $videosDir"
}
if (-not (Test-Path -LiteralPath $metadataDir)) {
    throw "Metadata dir not found: $metadataDir"
}
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    throw "ffmpeg not found in PATH."
}

$videos = Get-ChildItem -LiteralPath $videosDir -Filter '*.mp4'
if (-not $videos) {
    throw "No .mp4 files found in: $videosDir"
}

if (-not (Test-Path -LiteralPath $tempTexturesDir)) {
    New-Item -ItemType Directory -Path $tempTexturesDir | Out-Null
} elseif ($CleanTemp) {
    Get-ChildItem -LiteralPath $tempTexturesDir -Filter 'FRAME_*_*.png' | Remove-Item -Force
}

foreach ($video in $videos) {
    $groupName = [IO.Path]::GetFileNameWithoutExtension($video.Name)
    $outPattern = Join-Path $tempTexturesDir ("FRAME_%d_{0}.png" -f $groupName)
    & ffmpeg -y -i $video.FullName -start_number 0 -vsync 0 $outPattern | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "ffmpeg failed while extracting: $($video.Name)"
    }
}

$metas = Get-ChildItem -LiteralPath $metadataDir -Filter '*_metadata.json' |
    Sort-Object { $_.Name -replace '[^0-9]', '' -as [int] }

if (-not $metas) {
    throw "No *_metadata.json files found in: $metadataDir"
}

foreach ($meta in $metas) {
    & python ply_decode_cli.py --metadata $meta.FullName --textures-dir $tempTexturesDir --out-dir $outputDir
    if ($LASTEXITCODE -ne 0) {
        throw "PLY decode failed for: $($meta.Name)"
    }
}
