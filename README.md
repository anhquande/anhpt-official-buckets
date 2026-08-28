# AnhPT Official Workout Buckets

This repository stores **editable workout source files**. The app reads
[`main/bucket.json`](main/bucket.json) directly, while `.anhpt.zip` packages are
build artifacts attached to GitHub Releases and are not committed to the repo.

## Repository layout

Each workout lives in its own directory under `main/`:

```text
main/
  daily-plank/
    workout.yaml
    bucket-entry.json
    audio/
      ...
  meditation-before-sleep/
    workout.yaml
    bucket-entry.json
    ...
  bucket.json
```

`bucket-entry.json` contains the catalog metadata that cannot be derived safely
from `workout.yaml`, for example:

```json
{
  "id": "daily-plank",
  "name": "Daily Plank",
  "description": "Bài tập plank hằng ngày",
  "version": "1.0.0",
  "tags": ["core", "quick"],
  "minAppVersion": "0.8.2"
}
```

The file `bucket-entry.json` is repository metadata only and is **not included**
in the generated `.anhpt.zip` package.

## Automatic release flow

Every push/merge to `main` runs `.github/workflows/release-bucket.yml`:

1. Legacy `main/*.anhpt.zip` files are migrated once into editable source
   directories and removed from Git.
2. Every source directory is packaged as `<id>-<version>.anhpt.zip`.
3. SHA-256 and byte size are calculated from the exact generated ZIP.
4. `main/bucket.json` is regenerated with immutable GitHub Release URLs.
5. Generated catalog/migration changes are committed back to `main`.
6. A release named `bucket-<github run number>` is created.
7. All generated `.anhpt.zip` files are uploaded as release assets.

Commits made by the workflow use `GITHUB_TOKEN`, so they do not recursively start
a new workflow run.

## Add a new workout

Create a new directory under `main/`, add `workout.yaml`, referenced media, and a
`bucket-entry.json`. Do not create or commit a ZIP manually.

Example:

```text
main/morning-flow/
  workout.yaml
  bucket-entry.json
  audio/intro.mp3
```

After the change is merged into `main`, GitHub Actions builds and publishes the
package automatically.

## Build locally

PowerShell 7+ can build the same release artifacts locally:

```powershell
pwsh ./scripts/Build-Bucket.ps1 `
  -ReleaseTag local-test `
  -Repository anhquande/anhpt-official-buckets
```

The generated ZIP files are written to `dist/` and `main/bucket.json` is updated
with URLs for the supplied release tag.

## Legacy helper

`scripts/Add-WorkoutPackage.ps1` is kept for compatibility with the previous
manual ZIP-first workflow, but new workouts should use the source-folder flow
described above.
