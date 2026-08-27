<#
.SYNOPSIS
Adds or updates an AnhPT workout package entry in a bucket catalog.

.DESCRIPTION
Validates package metadata, calculates SHA-256 and byte size, and atomically
updates bucket.json. This script never uploads assets, creates releases, commits,
or pushes. Upload the package separately and provide its immutable HTTPS URL.

.EXAMPLE
./scripts/Add-WorkoutPackage.ps1 -PackagePath ./dist/morning-flow-1.0.0.anhpt.zip `
  -Id morning-flow -Version 1.0.0 -Name 'Morning Flow' `
  -Repository anhpt/anhpt-official-buckets -Tags mobility,quick -DryRun

.EXAMPLE
./scripts/Add-WorkoutPackage.ps1 -PackagePath ./dist/morning-flow-1.1.0.anhpt.zip `
  -Id morning-flow -Version 1.1.0 -Name 'Morning Flow' `
  -PackageUrl https://github.com/anhpt/anhpt-official-buckets/releases/download/v1.1.0/morning-flow-1.1.0.anhpt.zip -Update
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)] [string] $PackagePath,
    [Parameter(Mandatory)] [string] $Id,
    [Parameter(Mandatory)] [string] $Version,
    [Parameter(Mandatory)] [string] $Name,
    [string] $Description,
    [string[]] $Tags = @(),
    [string] $Author,
    [string] $MinAppVersion,
    [string] $PackageUrl,
    [string] $Repository,
    [string] $ReleaseTag,
    [string] $PackageUrlTemplate,
    [string] $CatalogPath = (Join-Path $PSScriptRoot '..\main\bucket.json'),
    [switch] $Update,
    [switch] $Force,
    [switch] $DryRun,
    [switch] $PassThru
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'Add-WorkoutPackage.ps1 requires PowerShell 7 or newer.'
}

function Assert-SemVer([string] $Value, [string] $Field) {
    if ($Value -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$') {
        throw "$Field must be a semantic version such as 1.2.0 or 1.2.0-beta.1."
    }
}

function Assert-PublicHttpsUrl([string] $Value) {
    $uri = $null
    if (-not [Uri]::TryCreate($Value, [UriKind]::Absolute, [ref] $uri) -or
        $uri.Scheme -ne 'https' -or -not $uri.Host -or $uri.UserInfo -or $uri.Fragment) {
        throw 'PackageUrl must be an absolute HTTPS URL without credentials or a fragment.'
    }
    if ($uri.Host -in @('localhost', '127.0.0.1', '::1') -or $uri.Host.EndsWith('.localhost')) {
        throw 'PackageUrl must not point to localhost.'
    }
}

if ($Id -notmatch '^[a-z0-9][a-z0-9._-]{0,63}$') {
    throw 'Id must be 1-64 lowercase letters, digits, dots, underscores, or hyphens.'
}
Assert-SemVer $Version 'Version'
if ($MinAppVersion) { Assert-SemVer $MinAppVersion 'MinAppVersion' }
if ([string]::IsNullOrWhiteSpace($Name)) { throw 'Name must not be empty.' }

$package = Get-Item -LiteralPath $PackagePath
if ($package.PSIsContainer -or -not $package.Name.EndsWith('.anhpt.zip', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'PackagePath must point to an existing .anhpt.zip file.'
}

if (-not $PackageUrl) {
    if ($PackageUrlTemplate) {
        $PackageUrl = $PackageUrlTemplate.Replace('{id}', $Id).Replace('{version}', $Version).Replace('{fileName}', $package.Name)
    } elseif ($Repository) {
        if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
            throw 'Repository must use the GitHub owner/repository form.'
        }
        if (-not $ReleaseTag) { $ReleaseTag = "v$Version" }
        $PackageUrl = "https://github.com/$Repository/releases/download/$ReleaseTag/$($package.Name)"
    } else {
        throw 'Provide PackageUrl, PackageUrlTemplate, or Repository.'
    }
}
Assert-PublicHttpsUrl $PackageUrl

$CatalogPath = [IO.Path]::GetFullPath($CatalogPath)
if (-not (Test-Path -LiteralPath $CatalogPath -PathType Leaf)) {
    throw "Catalog not found: $CatalogPath"
}
$catalog = Get-Content -LiteralPath $CatalogPath -Raw | ConvertFrom-Json
if ($catalog.schemaVersion -ne 1 -or [string]::IsNullOrWhiteSpace($catalog.name) -or $null -eq $catalog.workouts) {
    throw 'Catalog must contain schemaVersion 1, name, and a workouts array.'
}

$hash = (Get-FileHash -LiteralPath $package.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -notmatch '^[0-9a-f]{64}$') { throw 'Calculated SHA-256 is invalid.' }
$entry = [ordered]@{
    id = $Id
    name = $Name.Trim()
    description = if ($Description) { $Description.Trim() } else { '' }
    version = $Version
    packageUrl = $PackageUrl
    sha256 = $hash
    size = [int64] $package.Length
    tags = @($Tags | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object -Unique)
}
if ($Author) { $entry.author = $Author.Trim() }
if ($MinAppVersion) { $entry.minAppVersion = $MinAppVersion }

$existing = @($catalog.workouts | Where-Object { $_.id -eq $Id })
if ($existing.Count -gt 1) { throw "Catalog already contains multiple entries with id '$Id'." }
if ($existing.Count -eq 1) {
    if ($existing[0].version -eq $Version -and -not $Force) {
        throw "Entry '$Id' version '$Version' already exists. Use -Force to replace that exact version."
    }
    if ($existing[0].version -ne $Version -and -not $Update) {
        throw "Entry '$Id' already exists at version '$($existing[0].version)'. Use -Update to publish a new version."
    }
    $catalog.workouts = @($catalog.workouts | Where-Object { $_.id -ne $Id })
}
$catalog.workouts = @($catalog.workouts) + [pscustomobject] $entry
$catalog.workouts = @($catalog.workouts | Sort-Object id)
$json = $catalog | ConvertTo-Json -Depth 20

if ($DryRun) {
    Write-Host "Dry run: $CatalogPath would contain $($catalog.workouts.Count) workout(s)."
    $json
} elseif ($PSCmdlet.ShouldProcess($CatalogPath, "Add/update workout '$Id' version '$Version'")) {
    $directory = Split-Path -Parent $CatalogPath
    $temporary = Join-Path $directory ".bucket.$([Guid]::NewGuid().ToString('N')).tmp"
    $backup = Join-Path $directory ".bucket.$([Guid]::NewGuid().ToString('N')).bak"
    try {
        [IO.File]::WriteAllText($temporary, "$json`n", [Text.UTF8Encoding]::new($false))
        $null = Get-Content -LiteralPath $temporary -Raw | ConvertFrom-Json
        [IO.File]::Replace($temporary, $CatalogPath, $backup)
        Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
        Write-Host "Updated $CatalogPath with '$Id' version '$Version'."
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

if ($PassThru) { [pscustomobject] $entry }
