param(
    [string]$SourceDir = "main",
    [string]$OutputDir = "dist",
    [string]$Repository = "anhquande/anhpt-official-buckets",
    [string]$ReleaseTag
)

$ErrorActionPreference = "Stop"

if (-not $ReleaseTag) {
    throw "ReleaseTag is required."
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$sourcePath = Join-Path $repoRoot $SourceDir
$outputPath = Join-Path $repoRoot $OutputDir
$bucketPath = Join-Path $sourcePath "bucket.json"

if (-not (Test-Path $sourcePath)) {
    throw "Source directory not found: $sourcePath"
}

if (Test-Path $outputPath) {
    Remove-Item $outputPath -Recurse -Force
}

New-Item -ItemType Directory -Path $outputPath | Out-Null

$workouts = @()

$workoutDirs = Get-ChildItem -Path $sourcePath -Directory | Sort-Object Name

foreach ($dir in $workoutDirs) {
    $metadataPath = Join-Path $dir.FullName "bucket-entry.json"

    if (-not (Test-Path $metadataPath)) {
        Write-Warning "Skipping '$($dir.Name)': bucket-entry.json not found."
        continue
    }

    $metadata = Get-Content $metadataPath -Raw | ConvertFrom-Json

    foreach ($required in @("id", "name", "version", "minAppVersion")) {
        if (-not $metadata.$required) {
            throw "$metadataPath is missing required property '$required'."
        }
    }

    $packageFileName = "$($metadata.id)-$($metadata.version).anhpt.zip"
    $packagePath = Join-Path $outputPath $packageFileName

    Write-Host "Building $packageFileName"

    $tempDir = Join-Path $outputPath "_tmp_$($metadata.id)"

    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }

    New-Item -ItemType Directory -Path $tempDir | Out-Null

    Get-ChildItem -Path $dir.FullName -Force |
        Where-Object { $_.Name -ne "bucket-entry.json" } |
        ForEach-Object {
            Copy-Item $_.FullName -Destination $tempDir -Recurse -Force
        }

    Compress-Archive `
        -Path (Join-Path $tempDir "*") `
        -DestinationPath $packagePath `
        -CompressionLevel Optimal

    Remove-Item $tempDir -Recurse -Force

    $hash = (Get-FileHash $packagePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $size = (Get-Item $packagePath).Length

    $packageUrl =
        "https://github.com/$Repository/releases/download/$ReleaseTag/$packageFileName"

    $entry = [ordered]@{
        id            = $metadata.id
        name          = $metadata.name
        description   = $metadata.description
        version       = $metadata.version
        packageUrl    = $packageUrl
        sha256        = $hash
        size          = $size
        tags          = @($metadata.tags)
        minAppVersion = $metadata.minAppVersion
    }

    if ($metadata.author) {
        $entry.author = $metadata.author
    }

    $workouts += [pscustomobject]$entry
}

if ($workouts.Count -eq 0) {
    throw "No workouts found."
}

$bucket = [ordered]@{
    schemaVersion = 1
    name          = "AnhPT Official Workouts"
    workouts      = $workouts
}

$bucket |
    ConvertTo-Json -Depth 10 |
    Set-Content -Path $bucketPath -Encoding utf8

Write-Host ""
Write-Host "Generated bucket:"
Write-Host "  $bucketPath"
Write-Host ""
Write-Host "Generated packages:"

Get-ChildItem $outputPath -Filter "*.anhpt.zip" |
    ForEach-Object {
        Write-Host "  $($_.Name)"
    }