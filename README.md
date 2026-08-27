# AnhPT Official Workout Buckets

This repository hosts the catalog metadata for public AnhPT workout packages.
The app reads [`main/bucket.json`](main/bucket.json) directly; package ZIP files
are normally immutable GitHub Release assets.

## Add or update a package

The script requires PowerShell 7 and an existing `.anhpt.zip`. It calculates the
SHA-256 and byte size and updates the catalog locally. It never uploads a file,
creates a GitHub release, commits, or pushes.

```powershell
pwsh ./scripts/Add-WorkoutPackage.ps1 `
  -PackagePath ./dist/morning-flow-1.0.0.anhpt.zip `
  -Id morning-flow `
  -Version 1.0.0 `
  -Name "Morning Flow" `
  -Description "A short mobility routine" `
  -Tags mobility,quick `
  -Author "AnhPT" `
  -MinAppVersion 0.8.2 `
  -Repository owner/anhpt-official-buckets `
  -DryRun
```

`-Repository` generates a GitHub Releases URL using tag `v<version>` and the
package filename. Use `-ReleaseTag` to override the tag, `-PackageUrl` for an
explicit immutable HTTPS URL, or `-PackageUrlTemplate` with `{id}`, `{version}`,
and `{fileName}` placeholders.

Remove `-DryRun` after checking the generated JSON. Existing IDs require
`-Update` when changing version. Replacing the same ID and version requires
`-Force`. Upload the exact ZIP to the matching release separately, review the
catalog diff, then commit and push using the normal repository workflow.

```powershell
# Publish metadata for a newer release after its asset URL is decided.
pwsh ./scripts/Add-WorkoutPackage.ps1 `
  -PackagePath ./dist/morning-flow-1.1.0.anhpt.zip `
  -Id morning-flow -Version 1.1.0 -Name "Morning Flow" `
  -PackageUrl "https://github.com/owner/repo/releases/download/v1.1.0/morning-flow-1.1.0.anhpt.zip" `
  -Update
```

## Validate the script

The self-test uses a temporary catalog/package and does not change this repo:

```powershell
pwsh ./tests/Test-AddWorkoutPackage.ps1
```

The catalog schema is `schemaVersion: 1` with a `workouts` array. Every entry
contains `id`, `name`, `version`, `packageUrl`, `sha256`, `size`, and optional
display/compatibility metadata accepted by the AnhPT Marketplace MVP.
