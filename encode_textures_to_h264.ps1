param(
    [Parameter(Mandatory = $true)]
    [string]$InputDir,
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,
    [int]$Crf = 18,
    [int]$Fps = 30
)

$ErrorActionPreference = 'Stop'

$inputDir = [IO.Path]::GetFullPath($InputDir)
$outputDir = [IO.Path]::GetFullPath($OutputDir)

if (-not (Test-Path -LiteralPath $inputDir)) {
    throw "Input dir not found: $inputDir"
}

if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$files = Get-ChildItem -LiteralPath $inputDir -Filter 'FRAME_*_*.png' |
    Where-Object { $_.Name -match '^FRAME_(\d+)_([^.]+)\.png$' }

if (-not $files) {
    throw 'No FRAME_*_*.png files found.'
}

$groups = $files |
    ForEach-Object {
        $m = [regex]::Match($_.Name, '^FRAME_(\d+)_([^.]+)\.png$')
        [pscustomobject]@{
            Index = [int]$m.Groups[1].Value
            Group = $m.Groups[2].Value
            Path = $_.FullName
        }
    } |
    Group-Object Group

foreach ($g in $groups) {
    $listPath = Join-Path $outputDir ("_list_$($g.Name).txt")
    $g.Group |
        Sort-Object Index |
        ForEach-Object { "file '$($_.Path.Replace("'", "''"))'" } |
        Set-Content -LiteralPath $listPath -Encoding ascii

    $isPosition = $g.Name -in @('xyz_0', 'xyz_1')
    # Lossless encoding for position data, lossy for others
    if ($isPosition) {
        $outPath = Join-Path $outputDir ("$($g.Name).mkv")
        & ffmpeg -y -r $Fps -f concat -safe 0 -i $listPath -c:v ffv1 -level 3 -g 1 -pix_fmt rgb24 $outPath
    } else {
        $outPath = Join-Path $outputDir ("$($g.Name).mp4")
        & ffmpeg -y -r $Fps -f concat -safe 0 -i $listPath -c:v libx264 -pix_fmt yuv444p -crf $Crf $outPath
    }
    if ($LASTEXITCODE -ne 0) {
        throw "ffmpeg failed for group: $($g.Name)"
    }

    Remove-Item -LiteralPath $listPath -ErrorAction SilentlyContinue
}
