# AnhPT Official Workout Buckets

This repository contains the editable source files for the official AnhPT workout catalog.

Workout packages are **not stored as `.anhpt.zip` files in Git**. Instead, each workout is stored as an editable directory and GitHub Actions automatically builds the packages when changes are merged into `main`.

The AnhPT app reads the generated catalog from:

```text
main/bucket.json
```

## Repository layout

Each workout lives in its own directory under `main/`.

Example:

```text
main/
  daily-plank-1.0.0.anhpt/
    workout.yaml
    manifest.json
    coach_recordings/
      ...
    music/
      ...

  mediation-before-sleep.anhpt/
    workout.yaml
    manifest.json
    music/
      ...

  bai-tap-dit-cua-tho-bay-mau.anhpt/
    workout.yaml
    manifest.json

  bucket.json

scripts/
  build_bucket.py

.github/
  workflows/
    release-bucket.yml
```

## Workout metadata

Metadata is split between `workout.yaml` and `manifest.json`.

### `workout.yaml`

The workout file contains the actual workout definition and user-facing metadata.

For example:

```yaml
version: 2

name: Tập Plank mỗi ngày
description: Bài này nên tập đều đặn mỗi ngày để nâng cơ bụng

tags:
  - core
  - plank
  - daily

steps:
  ...
```

The `version` field in `workout.yaml` is the **workout schema version** used by the AnhPT app. It is not the package release version.

### `manifest.json`

Package-specific metadata lives in `manifest.json`.

Example:

```json
{
  "schemaVersion": 1,
  "workoutFile": "workout.yaml",
  "id": "daily-plank",
  "version": "1.0.0",
  "minAppVersion": "0.8.2"
}
```

Fields:

* `schemaVersion` — package manifest schema version.
* `workoutFile` — workout definition file, normally `workout.yaml`.
* `id` — stable workout identifier used in `bucket.json`.
* `version` — package version.
* `minAppVersion` — minimum AnhPT application version required to install the workout.

The package version is intentionally stored separately from the workout YAML schema version.

## Adding a new workout

Create a new directory under `main/`.

For example:

```text
main/morning-flow.anhpt/
  workout.yaml
  manifest.json
  music/
  coach_recordings/
```

Add the workout definition to `workout.yaml`.

Then create `manifest.json`:

```json
{
  "schemaVersion": 1,
  "workoutFile": "workout.yaml",
  "id": "morning-flow",
  "version": "1.0.0",
  "minAppVersion": "0.8.2"
}
```

Do **not** manually create or commit an `.anhpt.zip` file.

## Automatic release flow

Every push or merge to `main` runs:

```text
.github/workflows/release-bucket.yml
```

The workflow:

1. Checks out the repository.
2. Sets up Python.
3. Installs `PyYAML`.
4. Creates a release tag such as:

```text
bucket-42
```

5. Runs:

```bash
python scripts/build_bucket.py \
  --release-tag "$RELEASE_TAG" \
  --repository "$GITHUB_REPOSITORY"
```

6. Scans the workout directories under `main/`.
7. Reads package metadata from `manifest.json`.
8. Reads `name`, `description`, and `tags` from `workout.yaml`.
9. Builds one `.anhpt.zip` package for each workout.
10. Calculates SHA-256 and package size.
11. Regenerates `main/bucket.json`.
12. Commits the generated `bucket.json` back to `main` when it changed.
13. Creates a GitHub Release.
14. Uploads all generated `.anhpt.zip` packages as release assets.

The generated ZIP files are build artifacts and are never committed to the repository.

## Generated package

A generated package contains the complete workout directory.

Example:

```text
daily-plank-1.0.0.anhpt.zip
  workout.yaml
  manifest.json
  coach_recordings/
    ...
  music/
    ...
```

The package filename is generated from:

```text
<manifest.id>-<manifest.version>.anhpt.zip
```

For example:

```text
daily-plank-1.0.0.anhpt.zip
```

## Generated bucket catalog

`main/bucket.json` is generated automatically.

Example entry:

```json
{
  "id": "daily-plank",
  "name": "Tập Plank mỗi ngày",
  "description": "Bài này nên tập đều đặn mỗi ngày để nâng cơ bụng",
  "version": "1.0.0",
  "packageUrl": "https://github.com/anhquande/anhpt-official-buckets/releases/download/bucket-42/daily-plank-1.0.0.anhpt.zip",
  "sha256": "...",
  "size": 4535675,
  "tags": [
    "core",
    "plank",
    "daily"
  ],
  "minAppVersion": "0.8.2"
}
```

The following values are calculated automatically during the build:

* `packageUrl`
* `sha256`
* `size`

These values should not be maintained manually.

## Build locally

Python 3 is required.

Install the build dependency:

```bash
python -m pip install PyYAML
```

Build the packages locally:

```bash
python scripts/build_bucket.py --release-tag local-test
```

Or specify the repository explicitly:

```bash
python scripts/build_bucket.py \
  --release-tag local-test \
  --repository anhquande/anhpt-official-buckets
```

The generated packages will be written to:

```text
dist/
```

For example:

```text
dist/
  daily-plank-1.0.0.anhpt.zip
  meditation-before-sleep-1.0.0.anhpt.zip
  bai-tap-dit-cua-tho-bay-mau-1.0.0.anhpt.zip
```

`main/bucket.json` will also be regenerated.

## Git ignore

Generated packages and build output should not be committed.

The repository therefore ignores:

```text
*.anhpt.zip
dist/
```

## Publishing a new version

To publish a new version of an existing workout, update:

```json
"version": "1.1.0"
```

in its `manifest.json`, then commit and merge the change into `main`.

GitHub Actions will build:

```text
<id>-1.1.0.anhpt.zip
```

and publish it in the next bucket release.

There is no need to manually build, hash, upload, or edit `bucket.json`.
