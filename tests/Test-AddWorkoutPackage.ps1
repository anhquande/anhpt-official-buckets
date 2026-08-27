#requires -Version 7.0
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root 'scripts\Add-WorkoutPackage.ps1'
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) "anhpt-bucket-test-$([Guid]::NewGuid().ToString('N'))"

try {
    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    $catalog = Join-Path $temporaryRoot 'bucket.json'
    [IO.File]::WriteAllText($catalog, '{"schemaVersion":1,"name":"Test","workouts":[]}', [Text.UTF8Encoding]::new($false))
    $package = Join-Path $temporaryRoot 'sample-1.0.0.anhpt.zip'
    [IO.File]::WriteAllBytes($package, [byte[]](1, 2, 3, 4, 5))

    & $script -PackagePath $package -Id sample -Version 1.0.0 -Name Sample `
        -PackageUrl 'https://github.com/example/repo/releases/download/v1.0.0/sample-1.0.0.anhpt.zip' `
        -CatalogPath $catalog
    $result = Get-Content -LiteralPath $catalog -Raw | ConvertFrom-Json
    if ($result.workouts.Count -ne 1) { throw 'Expected one catalog entry.' }
    if ($result.workouts[0].sha256 -ne (Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'SHA-256 mismatch.' }
    if ($result.workouts[0].size -ne 5) { throw 'Size mismatch.' }

    $duplicateRejected = $false
    try {
        & $script -PackagePath $package -Id sample -Version 1.0.0 -Name Sample `
            -PackageUrl 'https://example.com/sample.anhpt.zip' -CatalogPath $catalog
    } catch { $duplicateRejected = $true }
    if (-not $duplicateRejected) { throw 'Duplicate id/version was not rejected.' }

    & $script -PackagePath $package -Id sample -Version 1.1.0 -Name Sample `
        -Repository example/repo -CatalogPath $catalog -Update
    $updated = Get-Content -LiteralPath $catalog -Raw | ConvertFrom-Json
    if ($updated.workouts[0].version -ne '1.1.0') { throw 'Update did not replace the previous version.' }
    if ($updated.workouts[0].packageUrl -notmatch '/releases/download/v1.1.0/') { throw 'GitHub release URL was not generated.' }

    Write-Host 'All Add-WorkoutPackage.ps1 self-tests passed.' -ForegroundColor Green
} finally {
    Remove-Item -LiteralPath $temporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
}
